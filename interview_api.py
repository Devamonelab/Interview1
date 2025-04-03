import sys
import traceback
import threading
import time
from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import interview_utils
import os
from audio_utils import (
    start_recording,
    stop_recording,
    transcribe_audio_bytes,
    security,
    text_to_speech_plain,
    play_audio_from_buffer
)

# Custom excepthook to print full tracebacks on unhandled exceptions.
def my_excepthook(exc_type, exc_value, exc_tb):
    try:
        print("Uncaught exception:")
        traceback.print_exception(exc_type, exc_value, exc_tb)
    except Exception as hook_error:
        print("Error in custom excepthook:", hook_error)
sys.excepthook = my_excepthook

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# In-memory storage
candidate_sessions = {}
completed_interviews = {}

# Function to speak the question in a separate thread
def speak_question_async(question):
    try:
        print(f"Speaking question: {question}")
        audio_buffer = text_to_speech_plain(question, lang_code="en")
        if audio_buffer:
            play_audio_from_buffer(audio_buffer)
    except Exception as e:
        print(f"Failed to speak question: {str(e)}")

# Serve static files
@app.route('/')
def serve_root():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

@app.route('/admin', methods=['POST'])
def admin_setup_endpoint():
    data = request.form if request.form else request.get_json()
    candidate_name = data.get("candidate_name")
    num_questions = data.get("num_questions")
    admin_instructions = data.get("admin_instructions")
    interview_time = data.get("interview_time", 30)
    
    if not candidate_name or not num_questions or not admin_instructions:
        return jsonify({"error": "Missing required parameters"}), 400

    if candidate_name in candidate_sessions:
        return jsonify({"error": f"Candidate '{candidate_name}' already exists."}), 400

    # Create the session
    session = {
        "candidate_name": candidate_name,
        "num_questions": int(num_questions),
        "admin_instructions": admin_instructions,
        "interview_time": int(interview_time),
        "current_question_index": 0,
        "current_question": None,
        "current_ideal_answer": None,
        "history": []
    }

    # Generate first question
    try:
        first_prompt = f"""
You are an interviewer. Admin instructions: {admin_instructions}

Generate an open-ended interview question about the candidate's experience, projects, education, or skills.
Provide an "ideal answer" for the question.

Format exactly:

*Question:*
<One open-ended question here>

*Ideal Answer:*
<A concise summary, 1-3 sentences>
"""
        response = interview_utils.llm.invoke(input=first_prompt)
        content = response.content.strip() if hasattr(response, "content") else ""
        qa = interview_utils.parse_open_ended_question(content)
        session["current_question"] = qa["question"]
        session["current_ideal_answer"] = qa["ideal_answer"]
    except Exception as e:
        return jsonify({"error": f"Failed to generate first question: {str(e)}"}), 500

    candidate_sessions[candidate_name] = session
    
    return jsonify({
        "message": "Interview session created",
        "current_question": session["current_question"],
        "instruction": "Please answer the question above."
    }), 200

@app.route('/candidate_voice', methods=['POST'])
def candidate_voice_interview():
    data = request.get_json()
    candidate_name = data.get("candidate_name")
    action = data.get("action")  # Expected: "start" or "stop"
    
    if not candidate_name or not action:
        return jsonify({"error": "Missing required parameters"}), 400

    if candidate_name not in candidate_sessions:
        return jsonify({"error": "Candidate session not found"}), 404

    session = candidate_sessions[candidate_name]

    if action == "start":
        session["recording_handle"] = start_recording()
        return jsonify({
            "message": "Recording started. When you finish speaking, click the 'Stop' button."
        }), 200

    elif action == "stop":
        if "recording_handle" not in session:
            return jsonify({"error": "No recording in progress"}), 400

        recorded_audio = stop_recording(session["recording_handle"])
        del session["recording_handle"]

        # Transcribe the candidate's audio answer
        encrypted_transcription = transcribe_audio_bytes(recorded_audio)
        candidate_answer = security.decrypt_text(encrypted_transcription)

        session["history"].append({
            "question": session["current_question"],
            "ideal_answer": session["current_ideal_answer"],
            "candidate_answer": candidate_answer
        })
        session["current_question_index"] += 1

        # Check if interview is complete
        if session["current_question_index"] >= session["num_questions"]:
            final_history = session["history"]
            overall_fb = interview_utils.generate_overall_feedback(final_history)
            
            completed_interviews[candidate_name] = {
                "message": "Interview completed",
                "history": final_history,
                "final_feedback": overall_fb["final_feedback"],
                "overall_score": overall_fb["overall_score"]
            }
            
            del candidate_sessions[candidate_name]
            
            return jsonify({
                "message": "Interview completed. Thank you for your participation.",
                "instruction": "Your interview has been processed and results are available to the administrator."
            }), 200

        try:
            qa = interview_utils.follow_up_interview(
                resume_text="",
                question=session["current_question"],
                ideal_answer=session["current_ideal_answer"],
                user_answer=candidate_answer
            )
            
            session["history"][-1]["feedback"] = qa.get("feedback", "")
            session["history"][-1]["score"] = qa.get("score", "")
            
            session["current_question"] = qa["question"]
            session["current_ideal_answer"] = qa["ideal_answer"]
            
            # Prepare response
            response_data = {
                "current_question": session["current_question"],
                "total_questions": session["num_questions"],
                "instruction": "Please answer the question above.",
                "feedback": qa.get("feedback", ""),
                "score": qa.get("score", "")
            }
            
            # Speak the new question
            threading.Thread(target=speak_question_async, args=(session["current_question"],)).start()
            
            return jsonify(response_data), 200
                
        except Exception as e:
            return jsonify({"error": f"Failed to generate next question: {str(e)}"}), 500

    else:
        return jsonify({"error": "Invalid action"}), 400

@app.route('/speak_question', methods=['GET'])
def speak_question():
    candidate_name = request.args.get("candidate_name")
    if not candidate_name:
        return jsonify({"error": "Missing candidate_name parameter"}), 400
    if candidate_name not in candidate_sessions:
        return jsonify({"error": "Candidate session not found"}), 404

    # Get the current question from the session
    question = candidate_sessions[candidate_name]["current_question"]
    
    # Return the question immediately in the response
    response_data = {
        "question": question,
        "message": "Speaking question now"
    }
    
    # Speak the question after sending the response
    threading.Thread(target=speak_question_async, args=(question,)).start()
    
    return jsonify(response_data), 200

@app.route('/admin_results', methods=['GET'])
def admin_results_endpoint():
    candidate_name = request.args.get("candidate_name")
    result_flag = request.args.get("result")
    
    if not candidate_name:
        return jsonify({"error": "Missing candidate_name parameter"}), 400
    
    if result_flag != "true":
        return jsonify({"error": "Parameter 'result' must be set to 'true'"}), 400
    
    if candidate_name in completed_interviews:
        return jsonify(completed_interviews[candidate_name]), 200
    else:
        if candidate_name in candidate_sessions:
            return jsonify({"message": "Interview for this candidate is still in progress"}), 400
        else:
            return jsonify({"error": "No results found for this candidate"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)