import io
import os
import logging
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import threading
from groq import Groq
from gtts import gTTS
from langdetect import detect, LangDetectException
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env
load_dotenv()

class BasicSecurity:
    def __init__(self):
        # Use the ENCRYPTION_KEY from the environment or generate a new one
        self.encryption_key = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)

    def encrypt_text(self, text):
        return self.cipher_suite.encrypt(text.encode()).decode()

    def decrypt_text(self, encrypted_text):
        try:
            return self.cipher_suite.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            return None

# Initialize Groq client (ensure 'api_key' is defined in your .env)
client = Groq(api_key=os.getenv("api_key"))
security = BasicSecurity()

def text_to_speech_in_memory(encrypted_text, lang_code="en"):
    """
    Convert encrypted text to speech in memory using gTTS.
    """
    try:
        decrypted_text = security.decrypt_text(encrypted_text)
        if not decrypted_text:
            return None
        tts = gTTS(text=decrypted_text, lang=lang_code)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        logging.error(f"TTS error: {str(e)}")
        return None

def text_to_speech_plain(text, lang_code="en"):
    """
    Convert plain text to speech in memory using gTTS.
    """
    try:
        tts = gTTS(text=text, lang=lang_code)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        logging.error(f"TTS error: {str(e)}")
        return None

def play_audio_from_buffer(audio_buffer):
    """
    Play MP3 audio from an in-memory buffer without saving a temporary file.
    This implementation uses pydub to decode the MP3 and sounddevice to play the raw audio.
    """
    try:
        # Decode the MP3 audio from the in-memory buffer
        audio_segment = AudioSegment.from_file(audio_buffer, format="mp3")
        # Get raw audio samples as a NumPy array
        samples = np.array(audio_segment.get_array_of_samples())
        # If the audio is stereo, reshape the data
        if audio_segment.channels == 2:
            samples = samples.reshape((-1, 2))
        # Play the audio using sounddevice
        sd.play(samples, audio_segment.frame_rate)
        sd.wait()  # Wait until playback is finished
    except Exception as e:
        logging.error(f"Error playing audio: {e}")

def transcribe_audio_bytes(audio_bytes, expected_lang_code="en"):
    """
    Transcribe audio from in-memory bytes using Groq's Whisper API.
    Returns the encrypted transcription.
    """
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio_input.wav", audio_bytes),
            model="whisper-large-v3",
            response_format="verbose_json",
            language=expected_lang_code
        )
        transcribed_text = transcription.text.strip()
        try:
            detected_lang = detect(transcribed_text)
            logging.info(f"Detected language: {detected_lang}")
        except LangDetectException:
            logging.warning("Language detection failed; proceeding.")
        return security.encrypt_text(transcribed_text)
    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        return None

def record_until_silence(
    sample_rate=44100, 
    channels=1, 
    chunk_duration=0.5, 
    silence_threshold=100, 
    silence_period=5.0
):
    """
    Records audio in-memory until silence (for silence_period seconds) is detected.
    This is provided for backward compatibility.
    """
    logging.info("Starting recording with silence detection...")
    recorded_frames = []
    silent_time = 0.0
    start_time = time.time()
    stream = sd.InputStream(samplerate=sample_rate, channels=channels, dtype='int16')
    stream.start()
    try:
        while True:
            chunk_frames, _ = stream.read(int(sample_rate * chunk_duration))
            recorded_frames.append(chunk_frames)
            rms = np.sqrt(np.mean(chunk_frames**2))
            logging.debug(f"RMS amplitude: {rms}")
            if rms < silence_threshold:
                silent_time += chunk_duration
            else:
                silent_time = 0.0
            if silent_time >= silence_period:
                logging.info("Detected 5 seconds of silence; stopping recording.")
                break
    except Exception as e:
        logging.error(f"Error while recording: {e}")
    finally:
        stream.stop()
        stream.close()
    recorded_data = np.concatenate(recorded_frames, axis=0)
    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, recorded_data, sample_rate, format='WAV')
    wav_buffer.seek(0)
    total_duration = time.time() - start_time
    logging.info(f"Recording finished. Total duration: {total_duration:.2f} seconds.")
    return wav_buffer.read()

# --- New functions for manual recording via Start/Stop buttons ---

def start_recording(sample_rate=44100, channels=1, chunk_duration=0.5):
    """
    Starts recording in a separate thread.
    Returns a handle with a stop event, a list to hold frames, and the thread.
    """
    recording_handle = {
        "stop_event": threading.Event(),
        "recorded_frames": [],
        "thread": None,
        "sample_rate": sample_rate,
        "channels": channels,
        "chunk_duration": chunk_duration
    }
    
    def recording_loop(handle):
        try:
            stream = sd.InputStream(
                samplerate=handle["sample_rate"],
                channels=handle["channels"],
                dtype='int16'
            )
            stream.start()
            while not handle["stop_event"].is_set():
                frames, _ = stream.read(int(handle["sample_rate"] * handle["chunk_duration"]))
                handle["recorded_frames"].append(frames)
            stream.stop()
            stream.close()
        except Exception as e:
            logging.error(f"Recording error: {e}")
    
    t = threading.Thread(target=recording_loop, args=(recording_handle,))
    recording_handle["thread"] = t
    t.start()
    logging.info("Recording started (manual mode).")
    return recording_handle

def stop_recording(recording_handle):
    """
    Signals the recording thread to stop and waits for it to finish.
    Returns the recorded audio bytes.
    """
    recording_handle["stop_event"].set()
    recording_handle["thread"].join()
    recorded_frames = recording_handle["recorded_frames"]
    if not recorded_frames:
        logging.error("No audio recorded.")
        return None
    recorded_data = np.concatenate(recorded_frames, axis=0)
    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, recorded_data, recording_handle["sample_rate"], format='WAV')
    wav_buffer.seek(0)
    logging.info("Recording stopped and audio data compiled.")
    return wav_buffer.read()

def ask_question_via_voice(question_text, lang_code="en"):
    """
    Uses TTS to speak the question and then starts the recording.
    This function is provided for backward compatibility.
    For manual control, use start_recording and stop_recording via API calls.
    """
    audio_buffer = text_to_speech_plain(question_text, lang_code=lang_code)
    if audio_buffer is None:
        logging.error("Failed to convert text to speech.")
        return None
    play_audio_from_buffer(audio_buffer)
    logging.info("Candidate, please click the 'Start' button to record your answer.")
    recorded_audio = record_until_silence()
    if recorded_audio is None:
        logging.error("Recording failed.")
        return None
    encrypted_transcription = transcribe_audio_bytes(recorded_audio, expected_lang_code=lang_code)
    if not encrypted_transcription:
        return None
    plain_transcription = security.decrypt_text(encrypted_transcription)
    return plain_transcription