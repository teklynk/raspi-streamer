import time
import json
import subprocess
import os
import signal
import logging
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from threading import Thread, Event

# Truncate the stream_control.log file
with open('stream_control.log', 'w'):
    pass

# Load environment variables from .env file
load_dotenv()

# RTMP stream settings
STREAM_KEY = os.getenv('STREAM_KEY')
RTMP_SERVER = os.getenv('RTMP_SERVER')

# ALSA audio source
ALSA_AUDIO_SOURCE = os.getenv('ALSA_AUDIO_SOURCE')

# Stream Settings
VIDEO_SIZE = os.getenv('VIDEO_SIZE')
FRAME_RATE = int(os.getenv('FRAME_RATE'))
BITRATE = int(os.getenv('BITRATE'))
KEYFRAME_INTERVAL = int(os.getenv('KEYFRAME_INTERVAL'))
AUDIO_OFFSET = os.getenv('AUDIO_OFFSET')
STREAM_M3U8_URL = os.getenv('STREAM_M3U8_URL')
STREAM_FILE = os.getenv('STREAM_FILE')  # Add STREAM_FILE variable

# Calculate buffer size and keyframe interval
BUFFER_SIZE = BITRATE * 2  # in kbps

# Determine the current working directory
current_directory = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(current_directory, 'stream_control.log')
sys_info_file_path = os.path.join(current_directory, 'system_info.txt')

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Disable werkzeug logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Initialize variables
streaming = False
recording = False
file_streaming = False
stream_recording = False

# Initialize global variables
stream_record_process = None
stream_recording = False
stream_process = None
streaming = False
file_stream_process = None
file_streaming = False

state_file = 'state.json'

default_state = {"streaming": False, "recording": False, "file_streaming": False, "streaming_and_recording": False}

# Sets the default state on startup
def load_default_state():    
    with open("state.json", "w") as file:
        json.dump(default_state, file, indent=4)

# Sets default state
load_default_state()

# Save current state to json file
def load_state():
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return default_state

def save_state(state):
    with open(state_file, 'w') as f:
        json.dump(state, f)

state = load_state()

def ensure_recordings_directory():
    if not os.path.exists("recordings"):
        os.makedirs("recordings")

def start_stream():
    global stream_process, streaming

    state = load_state()

    if state["streaming"]:
        return

    logging.debug("Starting stream...")

    stream_command = [
        "ffmpeg",
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-thread_queue_size", "64",
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE),  # Input from ALSA
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-probesize", "32", "-analyzeduration", "0",  # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME_INTERVAL),  # Keyframe interval
        "-profile:v", "main",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",  # Audio encoding settings
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-f", "flv", f"{RTMP_SERVER}{STREAM_KEY}"  # Output to RTMP server
    ]

    stream_process = subprocess.Popen(stream_command)
    logging.debug("Stream started!")
    streaming = True
    state["streaming_and_recording"] = False
    state["recording"] = False
    state["streaming"] = True
    save_state(state)

def stop_stream():
    global stream_process, streaming

    state = load_state()

    if not state["streaming"] and not state["streaming_and_recording"]:
        logging.debug("No active stream to stop.")
        return

    if stream_process:
        logging.debug("Stopping stream...")
        stream_process.terminate()
        stream_process.wait()
        stream_process = None
    logging.debug("Stream stopped!")
    streaming = False
    state["streaming"] = False
    save_state(state)

def start_recording():
    global record_process, recording

    state = load_state()

    if state["recording"]:
        return

    ensure_recordings_directory()
    logging.debug("Starting recording...")

    record_command = [
        "ffmpeg",
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-thread_queue_size", "64",
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE),  # Input from ALSA
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME_INTERVAL),  # Keyframe interval
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",  # Audio encoding settings
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-f", "mp4", f"recordings/recording_{int(time.time())}.mp4"  # Output to MP4 file
    ]

    record_process = subprocess.Popen(record_command)
    logging.debug("Recording started!")
    recording = True
    state["streaming"] = False
    state["streaming_and_recording"] = False
    state["recording"] = True
    save_state(state)

def stop_recording():
    global record_process, recording

    state = load_state()

    if not state["recording"]:
        return

    if record_process:
        logging.debug("Stopping recording...")
        record_process.terminate()
        record_process.wait()
        record_process = None
    logging.debug("Recording stopped!")
    recording = False
    state["recording"] = False
    save_state(state)

# Assuming load_state, save_state, ensure_recordings_directory, STREAM_M3U8_URL, 
# stream_record_process, and stream_recording are defined elsewhere

stop_event = Event()

def delayed_start_recording():
    for _ in range(30):
        if stop_event.is_set():
            logging.debug("Delayed start recording process was stopped before it started.")
            return
        time.sleep(1)

    if not stop_event.is_set():
        stream_record_command = [
            "ffmpeg",
            "-re", "-i", str(STREAM_M3U8_URL),
            "-c", "copy", f"recordings/stream_{int(time.time())}.mp4"
        ]

        global stream_record_process
        stream_record_process = subprocess.Popen(stream_record_command)
        logging.debug("Recording stream started!")

def start_stream_recording():
    global stream_record_process, stream_recording, stop_event

    state = load_state()

    if not STREAM_M3U8_URL:
        logging.error("STREAM_M3U8_URL is not set or is empty. Cannot start recording.")
        return

    ensure_recordings_directory()
    logging.debug("Starting stream recording...")

    stream_recording = True
    state["recording"] = False
    state["streaming"] = False
    state["streaming_and_recording"] = True
    save_state(state)

    stop_event.clear()  # Clear the stop event before starting the thread
    Thread(target=delayed_start_recording).start()

def stop_stream_recording():
    global stream_record_process, stream_recording, stream_process, stop_event

    state = load_state()

    if not state["streaming_and_recording"]:
        return

    if not STREAM_M3U8_URL:
        logging.error("STREAM_M3U8_URL is not set or is empty. Cannot stop recording.")
        return

    stop_event.set()  # Signal the delayed start thread to stop

    if stream_record_process:
        logging.debug("Stopping recording...")
        stream_record_process.terminate()
        stream_record_process.wait()
        stream_record_process = None

    logging.debug("Stream and Recording stopped!")
    stream_recording = False
    state["streaming_and_recording"] = False
    save_state(state)

def start_file_stream():
    global file_stream_process, file_streaming

    state = load_state()

    if state["file_streaming"]:
        return

    if not STREAM_FILE:
        logging.error("STREAM_FILE is not set or is empty. Cannot start file streaming.")
        return

    if os.path.isfile(STREAM_FILE) and not STREAM_FILE.endswith('.txt'):
        logging.debug(f"Streaming single file: {STREAM_FILE}")
        file_stream_command = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-stream_loop", "-1",  # Loop the input file indefinitely
            "-i", str(STREAM_FILE),  # Input file
            "-c:v", "copy",  # Copy the video codec
            "-c:a", "aac",  # Audio codec
            "-strict", "-2",  # Allow experimental codecs
            "-ac", "2",  # Set number of audio channels
            "-b:a", "128k",  # Audio bitrate
            "-ar", "44100",  # Audio sampling rate
            "-bufsize", "2M",  # Set buffer size for the stream
            "-f", "flv",  # Output format
            f"{RTMP_SERVER}{STREAM_KEY}"  # RTMP server URL and stream key
        ]
    elif STREAM_FILE.endswith('.txt') and os.path.isfile(STREAM_FILE):
        logging.debug(f"Streaming playlist file: {STREAM_FILE}")
        file_stream_command = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-f", "concat",  # Use concat demuxer
            "-safe", "0",  # Allow unsafe file paths
            "-stream_loop", "-1",  # Loop the playlist indefinitely
            "-i", str(STREAM_FILE),  # Input playlist file
            "-c:v", "copy",  # Copy the video codec
            "-c:a", "aac",  # Audio codec
            "-strict", "-2",  # Allow experimental codecs
            "-ac", "2",  # Set number of audio channels
            "-b:a", "128k",  # Audio bitrate
            "-ar", "44100",  # Audio sampling rate
            "-bufsize", "2M",  # Set buffer size for the stream
            "-f", "flv",  # Output format
            f"{RTMP_SERVER}{STREAM_KEY}"  # RTMP server URL and stream key
        ]
    else:
        logging.error(f"{STREAM_FILE} not found or invalid format. Cannot start file streaming.")
        return

    file_stream_process = subprocess.Popen(file_stream_command)
    logging.debug("File stream started!")
    file_streaming = True
    state["recording"] = False
    state["streaming"] = False
    state["file_streaming"] = True
    save_state(state)

def stop_file_stream():
    global file_stream_process, file_streaming

    state = load_state()

    if not state["file_streaming"]:
        return

    if file_stream_process:
        file_stream_process.terminate()
        file_stream_process.wait()
        file_stream_process = None
        time.sleep(3)  # Wait for 3 seconds
    logging.debug("File stream stopped!")
    file_streaming = False
    state["file_streaming"] = False
    save_state(state)

def shutdown_pi():
    logging.debug("Rebooting...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    if file_streaming:
        stop_file_stream()
    if stream_recording:
        stop_stream_recording()
    time.sleep(3)
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])

def restart_service():
    logging.debug("Restarting stream_control service...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    if file_streaming:
        stop_file_stream()
    if stream_recording:
        stop_stream_recording()
    time.sleep(3)
    subprocess.call(['sudo', 'systemctl', 'restart', 'stream_control.service'])

def poweroff_pi():
    logging.debug("Shutting down...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    if file_streaming:
        stop_file_stream()
    if stream_recording:
        stop_stream_recording()
    time.sleep(3)
    subprocess.call(['sudo', 'shutdown', '-h', 'now'])

# Flask application
app = Flask(__name__)

# Function to update the .env file
def update_env_file(data):
    # Open the .env file in write mode
    with open('.env', 'w') as env_file:
        # Write each key-value pair to the file
        for key, value in data.items():
            env_file.write(f"{key}={value}\n")
            
    # Reload the .env file to update the environment variables
    load_dotenv()
    
    # Update global variables with new values
    global STREAM_KEY, RTMP_SERVER, ALSA_AUDIO_SOURCE, VIDEO_SIZE, FRAME_RATE, BITRATE, KEYFRAME_INTERVAL, AUDIO_OFFSET, BUFFER_SIZE, STREAM_M3U8_URL, STREAM_FILE
    STREAM_KEY = os.getenv('STREAM_KEY')
    RTMP_SERVER = os.getenv('RTMP_SERVER')
    ALSA_AUDIO_SOURCE = os.getenv('ALSA_AUDIO_SOURCE')
    VIDEO_SIZE = os.getenv('VIDEO_SIZE')
    FRAME_RATE = int(os.getenv('FRAME_RATE'))
    BITRATE = int(os.getenv('BITRATE'))
    KEYFRAME_INTERVAL = int(os.getenv('KEYFRAME_INTERVAL'))
    AUDIO_OFFSET = os.getenv('AUDIO_OFFSET')
    STREAM_M3U8_URL = os.getenv('STREAM_M3U8_URL')
    STREAM_FILE = os.getenv('STREAM_FILE')
    BUFFER_SIZE = BITRATE * 2

@app.route('/')
def index():
    config = {
        'STREAM_KEY': os.getenv('STREAM_KEY'),
        'RTMP_SERVER': os.getenv('RTMP_SERVER'),
        'ALSA_AUDIO_SOURCE': os.getenv('ALSA_AUDIO_SOURCE'),
        'VIDEO_SIZE': os.getenv('VIDEO_SIZE'),
        'FRAME_RATE': os.getenv('FRAME_RATE'),
        'BITRATE': os.getenv('BITRATE'),
        'KEYFRAME_INTERVAL': os.getenv('KEYFRAME_INTERVAL'),
        'AUDIO_OFFSET': os.getenv('AUDIO_OFFSET'),
        'STREAM_M3U8_URL': os.getenv('STREAM_M3U8_URL'),
        'STREAM_FILE': os.getenv('STREAM_FILE')  # Add STREAM_FILE to config
    }
    state = load_state()
    return render_template('index.html', config=config, state=state)

@app.route('/load_state', methods=['GET'])
def load_state_endpoint():
    state = load_state()
    return jsonify(state)

@app.route('/toggle_<action>', methods=['POST'])
def toggle_action(action):
    try:
        state = load_state()
        logging.debug(f"Current state before toggle: {state}")
        
        if action not in state:
            raise ValueError(f"Invalid action: {action}")

        # Determine the current and new state for the action
        current_state = state[action]
        new_state = not current_state

        # Call the appropriate start/stop functions based on the action and new state
        if action == 'streaming':
            if new_state:
                start_stream()
            else:
                stop_stream()
        elif action == 'recording':
            if new_state:
                start_recording()
            else:
                stop_recording()
        elif action == 'file_streaming':
            if new_state:
                start_file_stream()
            else:
                stop_file_stream()
        elif action == 'streaming_and_recording':
            if new_state:
                start_stream()
                start_stream_recording()
            else:
                stop_stream()
                stop_stream_recording()

        # Update the state
        state[action] = new_state
        logging.debug(f"Toggled '{action}' to {state[action]}")

        # Ensure mutual exclusivity
        if action == 'streaming_and_recording' and new_state:
            state['streaming'] = False
            state['recording'] = False
            state['file_streaming'] = False
        elif action == 'streaming' and new_state:
            state['streaming_and_recording'] = False
            state['recording'] = False
            state['file_streaming'] = False
        elif action == 'recording' and new_state:
            state['streaming_and_recording'] = False
            state['streaming'] = False
            state['file_streaming'] = False
        elif action == 'file_streaming' and new_state:
            state['streaming_and_recording'] = False
            state['streaming'] = False
            state['recording'] = False

        logging.debug(f"New state after toggle: {state}")
        save_state(state)
        return jsonify(state), 200
    except Exception as e:
        logging.error(f"Error toggling action '{action}': {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/update_config', methods=['POST'])
def update_config():
    data = request.form.to_dict()
    update_env_file(data)
    shutdown_pi()
    return jsonify({"message": "Config updated successfully. Rebooting..."}), 200

@app.route('/start_stream', methods=['POST'])
def start_stream_route():
    start_stream()
    return jsonify({"message": "Stream started."}), 200

@app.route('/stop_stream', methods=['POST'])
def stop_stream_route():
    stop_stream()
    return jsonify({"message": "Stream stopped."}), 200

@app.route('/start_stream_record', methods=['POST'])
def start_stream_record_route():
    start_stream()
    start_stream_recording()
    return jsonify({"message": "Stream and recording started."}), 200


@app.route('/stop_stream_record', methods=['POST'])
def stop_stream_record_route():
    try:
        print("Calling stop_stream()")
        stop_stream()
        print("stop_stream() executed successfully")
    except Exception as e:
        print(f"Error in stop_stream(): {e}")

    try:
        print("Calling stop_stream_recording()")
        stop_stream_recording()
        print("stop_stream_recording() executed successfully")
    except Exception as e:
        print(f"Error in stop_stream_recording(): {e}")

    return jsonify({"message": "Stream and recording stopped."}), 200

@app.route('/start_record', methods=['POST'])
def start_record_route():
    start_recording()
    return jsonify({"message": "Recording started."}), 200

@app.route('/stop_record', methods=['POST'])
def stop_record_route():
    stop_recording()
    return jsonify({"message": "Recording stopped."}), 200

@app.route('/start_file_stream', methods=['POST'])
def start_file_stream_route():
    start_file_stream()
    return jsonify({"message": "File stream started."}), 200

@app.route('/stop_file_stream', methods=['POST'])
def stop_file_stream_route():
    stop_file_stream()
    return jsonify({"message": "File stream stopped."}), 200

@app.route('/reboot', methods=['POST'])
def shutdown_route():
    shutdown_pi()
    return jsonify({"message": "Rebooting"}), 200

@app.route('/poweroff', methods=['POST'])
def poweroff_route():
    poweroff_pi()
    return jsonify({"message": "Shutting down..."}), 200

@app.route('/restart', methods=['POST'])
def restart_route():
    restart_service()
    return jsonify({"message": "Restarting service..."}), 200

@app.route('/get_log')
def get_log():
    try:
        with open(log_file_path, 'r') as file:
            log_content = file.read()
        return jsonify({'log': log_content})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_sys_info')
def get_sys_info():
    try:
        with open(sys_info_file_path, 'r') as file:
            sys_info_content = file.read()
        return jsonify({'info': sys_info_content})
    except Exception as e:
        return jsonify({'error': str(e)})

# Function to run the Flask app in a separate thread
def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

# Start the Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.start()