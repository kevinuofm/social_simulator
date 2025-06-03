from flask import Flask, render_template, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile
import uuid
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

# Enable CORS
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize OpenAI client with error handling
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set!")
    sys.exit(1)

try:
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    sys.exit(1)

# Create a temporary directory for audio files
TEMP_DIR = tempfile.mkdtemp()

# Define social scenarios
SCENARIOS = [
    {
        "id": "job_interview",
        "title": "Job Interview",
        "description": "You're interviewing for your dream job at a tech company.",
        "context": "The interviewer will ask you questions about your experience and skills.",
        "ai_role": "A professional hiring manager conducting a job interview"
    },
    {
        "id": "networking",
        "title": "Networking Event",
        "description": "You're at a professional networking event in your industry.",
        "context": "You need to introduce yourself and make meaningful connections.",
        "ai_role": "A potential business contact at a networking event"
    },
    {
        "id": "difficult_conversation",
        "title": "Difficult Conversation",
        "description": "You need to discuss a sensitive issue with a colleague.",
        "context": "Your colleague has been consistently late to team meetings.",
        "ai_role": "A colleague who needs feedback about their punctuality"
    },
    {
        "id": "presentation",
        "title": "Public Speaking",
        "description": "You're giving a presentation to a group of stakeholders.",
        "context": "You need to present your project ideas and handle questions.",
        "ai_role": "A stakeholder in the audience asking questions about your presentation"
    }
]

@app.route('/')
def index():
    logger.info("Homepage accessed")
    try:
        return render_template('index.html', scenarios=SCENARIOS)
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")
    emit('connected', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")

def text_to_speech(text, voice="alloy"):
    """Convert text to speech using OpenAI's TTS API and return the filename"""
    try:
        filename = f"speech_{uuid.uuid4()}.mp3"
        filepath = os.path.join(TEMP_DIR, filename)
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        response.stream_to_file(filepath)
        return filename
    except Exception as e:
        print(f"Error generating speech: {str(e)}")
        return None

@app.route('/audio/<filename>')
def serve_audio(filename):
    try:
        return send_file(
            os.path.join(TEMP_DIR, filename),
            mimetype='audio/mpeg'
        )
    except Exception as e:
        print(f"Error serving audio: {str(e)}")
        return str(e), 404

@socketio.on('start_scenario')
def handle_start_scenario(data):
    """Handle scenario initialization"""
    try:
        scenario_id = data.get('scenario_id')
        scenario = next((s for s in SCENARIOS if s['id'] == scenario_id), None)
        
        if not scenario:
            raise ValueError("Invalid scenario selected")
            
        # Generate initial prompt from AI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are {scenario['ai_role']}. Start the conversation naturally as per the scenario context: {scenario['context']}"
                }
            ],
            max_tokens=100
        )
        
        initial_message = response.choices[0].message.content.strip()
        audio_filename = text_to_speech(initial_message, data.get('voice', 'alloy'))
        
        emit('scenario_started', {
            'message': initial_message,
            'audio_url': f'/audio/{audio_filename}' if audio_filename else None,
            'scenario': scenario
        })
        
    except Exception as e:
        print(f"Error starting scenario: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('transcribe')
def handle_transcription(data):
    logger.info(f"Received transcription request: {data.get('text')[:50]}...")
    try:
        text = data.get('text', '')
        voice = data.get('voice', 'alloy')
        scenario_id = data.get('scenario_id')
        scenario = next((s for s in SCENARIOS if s['id'] == scenario_id), None)
        
        if not scenario:
            raise ValueError("Invalid scenario")
            
        print(f"Received text: {text}")
        
        # Get AI response and feedback
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are {scenario['ai_role']}. 
                    Provide two responses:
                    1. An in-character response continuing the conversation
                    2. A brief feedback on the user's social skills, communication style, and suggestions for improvement
                    Format your response as JSON with 'response' and 'feedback' keys."""
                },
                {"role": "user", "content": text}
            ],
            max_tokens=200,
            response_format={ "type": "json_object" }
        )
        
        # Parse the JSON response
        response_data = json.loads(response.choices[0].message.content)
        ai_response = response_data['response']
        feedback = response_data['feedback']
        
        print(f"AI response: {ai_response}")
        print(f"Feedback: {feedback}")
        
        # Generate speech for AI response
        audio_filename = text_to_speech(ai_response, voice)
        
        # Emit both response and feedback
        emit('ai_response', {
            'response': ai_response,
            'feedback': feedback,
            'audio_url': f'/audio/{audio_filename}' if audio_filename else None
        })
        
    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    socketio.run(app, host='0.0.0.0', port=port) 