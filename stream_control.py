import RPi.GPIO as GPIO
import time
import subprocess
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from threading import Thread

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

# Calculate buffer size and keyframe interval
BUFFER_SIZE = BITRATE * 2  # in kbps

# Configure logging
logging.basicConfig(filename='/home/teklynk/raspi-streamer/stream_control.log', level=logging.DEBUG)

# Set up GPIO pins for buttons and LEDs
GPIO.setmode(GPIO.BCM)
STREAM_BUTTON_PIN = 23
RECORD_BUTTON_PIN = 24
SHUTDOWN_BUTTON_PIN = 16
STREAM_LED_PIN = 17
RECORD_LED_PIN = 26

GPIO.setup(STREAM_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RECORD_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(STREAM_LED_PIN, GPIO.OUT)
GPIO.setup(RECORD_LED_PIN, GPIO.OUT)

# Initialize variables
streaming = False
recording = False
last_stream_button_state = GPIO.input(STREAM_BUTTON_PIN)
last_record_button_state = GPIO.input(RECORD_BUTTON_PIN)
last_shutdown_button_state = GPIO.input(SHUTDOWN_BUTTON_PIN)
stream_process = None
record_process = None

# Timestamp variables for debouncing
last_stream_action_time = 0
last_record_action_time = 0
last_shutdown_action_time = 0

# Minimum delay between actions in seconds
ACTION_DELAY = 3

def ensure_recordings_directory():
    if not os.path.exists('recordings'):
        os.makedirs('recordings')

def start_stream():
    global stream_process, streaming
    if streaming:
        return
    logging.debug("Starting stream...")
    stream_command = [
        "ffmpeg",
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-thread_queue_size", "64",
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE),  # Input from ALSA
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental",  # Flags for low latency
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-probesize", "32", "-analyzeduration", "0",  # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME_INTERVAL),  # Keyframe interval
        "-profile:v", "main",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",  # Audio encoding settings
        "-max_delay", "0",  # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-async", "1",  # Sync audio with video
        "-f", "flv", f"{RTMP_SERVER}{STREAM_KEY}"  # Output to RTMP server
    ]
    stream_process = subprocess.Popen(stream_command)
    GPIO.output(STREAM_LED_PIN, GPIO.HIGH)
    logging.debug("Stream started!")
    logging.debug(stream_command)
    streaming = True

def stop_stream():
    global stream_process, streaming
    if not streaming:
        return
    if stream_process:
        logging.debug("Stopping stream...")
        stream_process.terminate()
        stream_process.wait()
        stream_process = None
        GPIO.output(STREAM_LED_PIN, GPIO.LOW)
        logging.debug("Stream stopped!")
        time.sleep(3)  # Wait for 3 seconds to ensure the device is released
    streaming = False

def start_recording():
    global record_process, recording
    if recording:
        return
    ensure_recordings_directory()
    logging.debug("Starting recording...")
    record_command = [
        "ffmpeg",
        "-retries", "3",  # specify the number of retries
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-thread_queue_size", "64",
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE),  # Input from ALSA
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental",  # Flags for low latency
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-probesize", "32", "-analyzeduration", "0",  # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME_INTERVAL),  # Keyframe interval
        "-profile:v", "main",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",  # Audio encoding settings
        "-max_delay", "0",  # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-async", "1",  # Sync audio with video
        "-f", "mp4", f"recordings/recording_{int(time.time())}.mp4"
    ]
    record_process = subprocess.Popen(record_command)
    GPIO.output(RECORD_LED_PIN, GPIO.HIGH)
    logging.debug("Recording started!")
    logging.debug(record_command)
    recording = True

def stop_recording():
    global record_process, recording
    if not recording:
        return
    if record_process:
        logging.debug("Stopping recording...")
        record_process.terminate()
        record_process.wait()
        record_process = None
        GPIO.output(RECORD_LED_PIN, GPIO.LOW)
        logging.debug("Recording stopped!")
        time.sleep(3)  # Wait for 3 seconds to ensure the device is released
        recording = False

def start_stream_recording():
    global stream_record_process, recording
    if recording:
        return
    ensure_recordings_directory()
    logging.debug("Starting stream recording...")
    stream_record_command = [
        "ffmpeg",
        "-retries", "3",  # specify the number of retries
        "-i", str(STREAM_M3U8_URL),
        "-c", "copy", f"recordings/stream_{int(time.time())}.mp4"
    ]
    stream_record_process = subprocess.Popen(stream_record_command)
    logging.debug("Recording stream started!")
    logging.debug(stream_record_command)
    recording = True

def shutdown_pi():
    logging.debug("Rebooting...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    GPIO.cleanup()
    time.sleep(3)
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])

def restart_service():
    logging.debug("Restarting stream_control service...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    GPIO.cleanup()
    time.sleep(3)
    subprocess.call(['sudo', 'systemctl', 'restart', 'stream_control.service'])

def poweroff_pi():
    logging.debug("Shutting down...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    GPIO.cleanup()
    time.sleep(3)
    subprocess.call(['sudo', 'shutdown', '-h', 'now'])

# Flask application
app = Flask(__name__)

# Function to update the .env file
def update_env_file(data):
    with open('.env', 'w') as env_file:
        for key, value in data.items():
            env_file.write(f"{key}={value}\n")
        load_dotenv()  # Reload the .env file to update the environment variables
        # Update global variables with new values
        global STREAM_KEY, RTMP_SERVER, ALSA_AUDIO_SOURCE, VIDEO_SIZE, FRAME_RATE, BITRATE, KEYFRAME_INTERVAL, AUDIO_OFFSET, BUFFER_SIZE
        STREAM_KEY = os.getenv('STREAM_KEY')
        RTMP_SERVER = os.getenv('RTMP_SERVER')
        ALSA_AUDIO_SOURCE = os.getenv('ALSA_AUDIO_SOURCE')
        VIDEO_SIZE = os.getenv('VIDEO_SIZE')
        FRAME_RATE = int(os.getenv('FRAME_RATE'))
        BITRATE = int(os.getenv('BITRATE'))
        KEYFRAME_INTERVAL = int(os.getenv('KEYFRAME_INTERVAL'))
        AUDIO_OFFSET = os.getenv('AUDIO_OFFSET')
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
        'AUDIO_OFFSET': os.getenv('AUDIO_OFFSET')
    }
    return render_template('index.html', config=config)

@app.route('/update_config', methods=['POST'])
def update_config():
    data = request.form.to_dict()
    update_env_file(data)
    time.sleep(1)
    shutdown_pi()
    return jsonify({"message": "Config updated successfully. Rebooting"}), 200

@app.route('/start_stream', methods=['POST'])
def start_stream_route():
    start_stream()
    start_stream_recording()
    return jsonify({"message": "Stream started"}), 200

@app.route('/stop_stream', methods=['POST'])
def stop_stream_route():
    stop_stream()
    return jsonify({"message": "Stream stopped"}), 200

@app.route('/start_record', methods=['POST'])
def start_record_route():
    start_recording()
    return jsonify({"message": "Recording started"}), 200

@app.route('/stop_record', methods=['POST'])
def stop_record_route():
    stop_recording()
    return jsonify({"message": "Recording stopped"}), 200

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
    return jsonify({"message": "Restarting service"}), 200

# Function to run the Flask app in a separate thread
def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

# Start the Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.start()

# Main loop to handle button presses
try:
    while True:
        stream_button_state = GPIO.input(STREAM_BUTTON_PIN)
        record_button_state = GPIO.input(RECORD_BUTTON_PIN)
        shutdown_button_state = GPIO.input(SHUTDOWN_BUTTON_PIN)
        
        current_time = time.time()

        if stream_button_state == GPIO.LOW and last_stream_button_state == GPIO.HIGH and (current_time - last_stream_action_time) > ACTION_DELAY:
            if streaming:
                stop_stream()
            else:
                start_stream()
            last_stream_action_time = current_time

        if record_button_state == GPIO.LOW and last_record_button_state == GPIO.HIGH and (current_time - last_record_action_time) > ACTION_DELAY:
            if recording:
                stop_recording()
            else:
                start_recording()
            last_record_action_time = current_time

        if shutdown_button_state == GPIO.LOW and last_shutdown_button_state == GPIO.HIGH and (current_time - last_shutdown_action_time) > ACTION_DELAY:
            shutdown_pi()
            last_shutdown_action_time = current_time

        last_stream_button_state = stream_button_state
        last_record_button_state = record_button_state
        last_shutdown_button_state = shutdown_button_state

        time.sleep(0.1)

except KeyboardInterrupt:
    GPIO.cleanup()
