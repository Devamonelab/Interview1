import PyPDF2
import traceback
import time

# For the LLM integration
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

# -------------------------------------------------------------------------
# LLM INITIALIZATION
# -------------------------------------------------------------------------
# Provide your Google API key in .env or code. The below is just an example.
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    verbose=False,
    temperature=0.5,
    google_api_key="AIzaSyAdGpuFO3_LHENFu2JOMYDRBPF0CptBNzM"
)

# -------------------------------------------------------------------------
# PROMPT TEMPLATES
# -------------------------------------------------------------------------
resume_question_prompt_template = PromptTemplate(
    input_variables=["resume_text"],
    template="""
You are an interviewer reviewing the following resume:

{resume_text}

Generate a single open-ended interview question about the candidate's experience, projects, education, or skills.
Provide an "ideal answer" for the question.

Format exactly:

*Question:*
<One open-ended question here>

*Ideal Answer:*
<A concise summary of the best or correct response, 1-3 sentences>
"""
)

follow_up_prompt_template = PromptTemplate(
    input_variables=["resume_text", "question", "ideal_answer", "user_answer"],
    template="""
You are an interviewer. You asked the candidate this question:

{question}

Ideal answer:
{ideal_answer}

Candidate's answer:
{user_answer}

1. Provide detailed feedback on the correctness/completeness of the candidate's answer.
2. Score the answer out of 10. Be moderately strict in your evaluation, where:
   - 9-10: Exceptional answer that exceeds expectations
   - 7-8: Good answer with minor omissions
   - 5-6: Adequate answer with noticeable gaps
   - 3-4: Weak answer with significant issues
   - 1-2: Very poor answer that misses the point entirely
3. Generate ONE new question to continue the interview.
4. Provide an ideal answer for that question.

Format exactly:

*Feedback:*
<Your detailed feedback, 2-3 sentences>

*Score:*
<Score as a number between 1 and 10>

*Next Question:*
<One new question>

*Ideal Answer:*
<1-3 sentences>
"""
)

multi_question_prompt_template = PromptTemplate(
    input_variables=[
        "resume_text",
        "candidate_name",
        "num_questions",
        "interview_time",
        "admin_instructions"
    ],
    template="""
You are an interviewer with instructions from the admin:

- Candidate name: {candidate_name}
- Number of questions: {num_questions}
- Time duration (minutes): {interview_time}
- Kind of interview / Admin instructions: {admin_instructions}

Given the candidate's resume:
{resume_text}

Generate exactly {num_questions} open-ended questions that follow the admin's instructions about difficulty, distribution, or topics. Also provide an "ideal answer" for each question.

Format exactly:

*Questions and Ideal Answers:*
1) Question: <question>
   Ideal Answer: <1-3 sentences>
2) Question: ...
   Ideal Answer: ...
...
"""
)

# NEW: Overall feedback prompt template
overall_feedback_prompt_template = PromptTemplate(
    input_variables=["history_text"],
    template="""
You are an interviewer reviewing an entire interview session consisting of multiple questions.
The interview history is provided below:

{history_text}

Provide a final summary feedback for the entire interview highlighting strengths and areas for improvement.
Also, provide an overall score out of 10 (not as a percentage). Be moderately strict in your evaluation.

Format exactly:
*Final Feedback:*
<Your final summary feedback>

*Overall Score:*
<Score as a number between 1 and 10>
"""
)

# NEW: Overall feedback with monitoring prompt template
overall_feedback_with_monitoring_prompt_template = PromptTemplate(
    input_variables=["history_text", "monitoring_data"],
    template="""
You are an interviewer reviewing an entire interview session consisting of multiple questions.
The interview history is provided below:

{history_text}

The candidate was also monitored for suspicious behavior during the interview. Here is the monitoring data:

{monitoring_data}

Please review both the interview responses AND the monitoring data carefully.
- Consider any evidence of looking away from the screen, mobile phone usage, or other suspicious actions.
- Take into account eye movement patterns, head position changes, and any detected mobile devices.
- Be more strict in your evaluation if there are significant suspicious behaviors detected.

Provide a final summary feedback for the entire interview addressing:
1. The quality of the candidate's answers
2. Any concerning behaviors from the monitoring data
3. Overall impression and trustworthiness of the assessment

Also, provide an overall score out of 10 (not as a percentage), taking into account both answer quality and behavior integrity.

Format exactly:
*Final Feedback:*
<Your final summary feedback, addressing both answer quality and monitoring data>

*Overall Score:*
<Score as a number between 1 and 10>
"""
)

# -------------------------------------------------------------------------
# PARSING / HELPER FUNCTIONS
# -------------------------------------------------------------------------
def parse_pdf_to_text(pdf_file_bytes) -> str:
    """
    Reads a PDF (file-like object) and returns extracted text.
    """
    reader = PyPDF2.PdfReader(pdf_file_bytes)
    pages_text = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        pages_text.append(txt)
    return "\n".join(pages_text).strip()

def parse_open_ended_question(content: str):
    """
    Parse the LLM response for the FIRST question. Expecting markers:
    *Question:*
    ...
    *Ideal Answer:*
    ...
    """
    lines = content.strip().split("\n")
    question_marker = "*Question:*"
    ideal_marker = "*Ideal Answer:*"

    try:
        q_index = lines.index(question_marker)
        a_index = lines.index(ideal_marker)
        question_text = "\n".join(lines[q_index + 1 : a_index]).strip()
        ideal_text = "\n".join(lines[a_index + 1 :]).strip()

        return {"question": question_text, "ideal_answer": ideal_text}
    except Exception as e:
        raise ValueError(f"Failed to parse question from LLM: {e}")

def parse_follow_up_response(content: str):
    """
    Parse the LLM response for follow-up. Expecting:
    *Feedback:*
    ...
    *Score:*
    ...
    *Next Question:*
    ...
    *Ideal Answer:*
    ...
    """
    lines = content.strip().split("\n")
    feedback_marker = "*Feedback:*"
    score_marker = "*Score:*"
    next_q_marker = "*Next Question:*"
    ideal_marker = "*Ideal Answer:*"

    try:
        f_index = lines.index(feedback_marker)
        score_index = lines.index(score_marker)
        nq_index = lines.index(next_q_marker)
        ia_index = lines.index(ideal_marker)

        feedback = "\n".join(lines[f_index + 1 : score_index]).strip()
        score = "\n".join(lines[score_index + 1 : nq_index]).strip()
        next_question = "\n".join(lines[nq_index + 1 : ia_index]).strip()
        next_ideal = "\n".join(lines[ia_index + 1 :]).strip()

        return {
            "feedback": feedback,
            "score": score,
            "question": next_question,
            "ideal_answer": next_ideal
        }
    except Exception as e:
        raise ValueError(f"Failed to parse follow-up response from LLM: {e}")

# NEW: Parsing overall feedback response
def parse_overall_feedback(content: str):
    """
    Parse the LLM response for final overall feedback. Expecting markers:
    *Final Feedback:*
    ...
    *Overall Score:*
    ...
    """
    lines = content.strip().split("\n")
    final_fb_marker = "*Final Feedback:*"
    score_marker = "*Overall Score:*"
    
    try:
        fb_index = lines.index(final_fb_marker)
        score_index = lines.index(score_marker)
        final_feedback = "\n".join(lines[fb_index + 1:score_index]).strip()
        
        # Fix: Extract the score and clean it properly
        overall_score = "\n".join(lines[score_index + 1:]).strip()
        
        # Clean up the score - extract just the number value
        import re
        
        # First, try to match a pattern like "8/10" and get just the first number
        match = re.search(r'(\d+(\.\d+)?)/10', overall_score)
        if match:
            overall_score = match.group(1)
        else:
            # If not in X/10 format, extract any numeric value
            match = re.search(r'(\d+(\.\d+)?)', overall_score)
            if match:
                overall_score = match.group(1)
            else:
                overall_score = "0"  # Fallback
        
        # Make sure it's a valid float and format to one decimal place
        try:
            overall_score = str(float(overall_score))
        except ValueError:
            overall_score = "0"  # Fallback
        
        return {"final_feedback": final_feedback, "overall_score": overall_score}
    except Exception as e:
        raise ValueError(f"Failed to parse overall feedback from LLM: {e}")

# Existing single-question generation:
def generate_question_from_resume(resume_text: str):
    prompt = resume_question_prompt_template.format(resume_text=resume_text)
    response = llm.invoke(input=prompt)
    content = response.content.strip() if hasattr(response, "content") else ""
    return parse_open_ended_question(content)

# Existing follow-up:
def follow_up_interview(resume_text: str, question: str, ideal_answer: str, user_answer: str):
    prompt = follow_up_prompt_template.format(
        resume_text=resume_text,
        question=question,
        ideal_answer=ideal_answer,
        user_answer=user_answer
    )
    response = llm.invoke(input=prompt)
    content = response.content.strip() if hasattr(response, "content") else ""
    return parse_follow_up_response(content)

# -------------------------------------------------------------------------
# NEW: MULTI-QUESTION GENERATION BASED ON ADMIN INSTRUCTIONS
# -------------------------------------------------------------------------
def generate_multi_questions(resume_text: str, candidate_name: str, num_questions: int,
                             interview_time: int, admin_instructions: str):
    """
    Uses an LLM prompt to generate `num_questions` questions (and ideal answers)
    based on the admin instructions about difficulty, topic distribution, etc.
    """
    prompt = multi_question_prompt_template.format(
        resume_text=resume_text,
        candidate_name=candidate_name,
        num_questions=num_questions,
        interview_time=interview_time,
        admin_instructions=admin_instructions
    )
    response = llm.invoke(input=prompt)
    return response.content.strip() if hasattr(response, "content") else ""

# -------------------------------------------------------------------------
# NEW: OVERALL FEEDBACK GENERATION
# -------------------------------------------------------------------------
def generate_overall_feedback(history):
    """
    Generates a final overall feedback and performance percentage based on the interview history.
    """
    history_text = ""
    for i, entry in enumerate(history, start=1):
        history_text += f"{i}) Question: {entry['question']}\n   Ideal Answer: {entry['ideal_answer']}\n   Candidate Answer: {entry['candidate_answer']}\n\n"
    prompt = overall_feedback_prompt_template.format(history_text=history_text)
    response = llm.invoke(input=prompt)
    content = response.content.strip() if hasattr(response, "content") else ""
    return parse_overall_feedback(content)

# -------------------------------------------------------------------------
# NEW: OVERALL FEEDBACK WITH MONITORING DATA
# -------------------------------------------------------------------------
def generate_overall_feedback_with_monitoring(history, monitoring_metrics):
    """
    Generates a final overall feedback and score based on both interview history and monitoring data.
    Takes into account suspicious behaviors detected during the interview.
    """
    # Format the interview history
    history_text = ""
    for i, entry in enumerate(history, start=1):
        history_text += f"{i}) Question: {entry['question']}\n   Ideal Answer: {entry['ideal_answer']}\n   Candidate Answer: {entry['candidate_answer']}\n"
        if "feedback" in entry and "score" in entry:
            history_text += f"   Feedback: {entry['feedback']}\n   Score: {entry['score']}\n\n"
        else:
            history_text += "\n"
    
    # Format the monitoring data for the LLM
    monitoring_data = f"""
Mobile Phone Detections: {monitoring_metrics['mobile_detection_count']}

Head Position Events:
- Looking Left: {monitoring_metrics['head_pose_events']['Looking Left']}
- Looking Right: {monitoring_metrics['head_pose_events']['Looking Right']}
- Looking Up: {monitoring_metrics['head_pose_events']['Looking Up']}
- Looking Down: {monitoring_metrics['head_pose_events']['Looking Down']}
- Tilted: {monitoring_metrics['head_pose_events']['Tilted']}

Eye Movement Events:
- Looking Left: {monitoring_metrics['eye_movement_events']['Looking Left']}
- Looking Right: {monitoring_metrics['eye_movement_events']['Looking Right']}
- Looking Up: {monitoring_metrics['eye_movement_events']['Looking Up']}
- Looking Down: {monitoring_metrics['eye_movement_events']['Looking Down']}

Suspicious Activity Log:
"""
    
    # Add suspicious activity log entries
    for i, activity in enumerate(monitoring_metrics['suspicious_activity_log'][:10], start=1):  # Limit to 10 entries
        if activity['type'] == 'mobile_detected':
            monitoring_data += f"{i}. Mobile device detected at {time.strftime('%H:%M:%S', time.localtime(activity['timestamp']))}\n"
        elif activity['type'] == 'head_pose':
            monitoring_data += f"{i}. Head {activity['direction']} at {time.strftime('%H:%M:%S', time.localtime(activity['timestamp']))}\n"
        elif activity['type'] == 'eye_movement':
            monitoring_data += f"{i}. Eyes {activity['direction']} at {time.strftime('%H:%M:%S', time.localtime(activity['timestamp']))}\n"
    
    # If there are more than 10 entries, indicate there are more
    if len(monitoring_metrics['suspicious_activity_log']) > 10:
        monitoring_data += f"... and {len(monitoring_metrics['suspicious_activity_log']) - 10} more events\n"
    
    # Generate the feedback with monitoring data
    prompt = overall_feedback_with_monitoring_prompt_template.format(
        history_text=history_text,
        monitoring_data=monitoring_data
    )
    response = llm.invoke(input=prompt)
    content = response.content.strip() if hasattr(response, "content") else ""
    return parse_overall_feedback(content)

# -------------------------------------------------------------------------
# SIMPLE ADMIN "PANEL" LOGIC FOR UNIQUE CANDIDATES
# -------------------------------------------------------------------------
existing_candidates = set()

def admin_setup(candidate_name: str, num_questions: int, interview_time: int, admin_instructions: str):
    """
    Mimics an 'admin panel' that ensures the candidate name is unique,
    and returns a dictionary of interview parameters.
    """
    # Check uniqueness
    if candidate_name in existing_candidates:
        raise ValueError(f"Candidate '{candidate_name}' already exists. Provide a unique name.")
    existing_candidates.add(candidate_name)

    # Return the 'config' (in real-world usage, you'd store this in a DB)
    interview_config = {
        "candidate_name": candidate_name,
        "num_questions": num_questions,
        "interview_time": interview_time,
        "admin_instructions": admin_instructions
    }
    return interview_config

# -------------------------------------------------------------------------
# Example usage from the command line
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    """
    Example usage:
        python interview_utils.py Admin "John_Doe" 5 30 "Ask 30% coding, 20% project, 50% technical questions"

    OR just to illustrate how you might read arguments in a real scenario:
        python interview_utils.py John_Doe 5 30 "Ask some advanced coding questions"
    """

    if len(sys.argv) < 5:
        print("Usage: python interview_utils.py <candidate_name> <num_questions> <time_duration> <admin_instructions>")
        sys.exit(1)

    # Parse arguments
    candidate_name = sys.argv[1]
    num_questions = int(sys.argv[2])
    interview_time = int(sys.argv[3])
    admin_instructions = sys.argv[4]

    # Setup from "admin panel"
    try:
        config = admin_setup(candidate_name, num_questions, interview_time, admin_instructions)
        print(f"Admin setup complete for candidate: {candidate_name}")
        print("Interview config:", config)
    except ValueError as ve:
        print(f"Error in admin setup: {ve}")
        sys.exit(1)

    # Example: Generate multiple questions from a dummy resume text
    dummy_resume_text = "John Doe is a software engineer with 5 years of experience in Python and web development."
    result = generate_multi_questions(
        resume_text=dummy_resume_text,
        candidate_name=config["candidate_name"],
        num_questions=config["num_questions"],
        interview_time=config["interview_time"],
        admin_instructions=config["admin_instructions"]
    )

    print("\n===== LLM-Generated Questions and Ideal Answers =====\n")
    print(result)