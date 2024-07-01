import RPi.GPIO as GPIO
import time
import subprocess
import os
import logging
from dotenv import load_dotenv

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
KEYFRAME_INTERVAL_SEC = int(os.getenv('KEYFRAME_INTERVAL_SEC'))
AUDIO_OFFSET = os.getenv('AUDIO_OFFSET')

# Calculate buffer size and keyframe interval
BUFFER_SIZE = BITRATE * 2  # in kbps
KEYFRAME = FRAME_RATE * KEYFRAME_INTERVAL_SEC  # Keyframe interval in frames

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
    global stream_process
    logging.debug("Starting stream...")
    stream_command = [
        "ffmpeg",
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE), # Input from ALSA
        "-thread_queue_size", "64",
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental", # Flags for low latency
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0", # Video input settings
        "-probesize", "32", "-analyzeduration", "0", # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k", # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME),  # Keyframe interval
        "-profile:v", "main",
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100", # Audio encoding settings
        "-max_delay", "0", # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1", # Use wallclock timestamps
        "-flush_packets", "1", # Flush packets
        "-async", "1", # Sync audio with video
        "-f", "flv", f"{RTMP_SERVER}{STREAM_KEY}"  # Output to RTMP server
    ]
    stream_process = subprocess.Popen(stream_command)
    GPIO.output(STREAM_LED_PIN, GPIO.HIGH)
    logging.debug("Stream started!")

def stop_stream():
    global stream_process
    if stream_process:
        logging.debug("Stopping stream...")
        stream_process.terminate()
        stream_process.wait()
        stream_process = None
        GPIO.output(STREAM_LED_PIN, GPIO.LOW)
        logging.debug("Stream stopped!")
        time.sleep(3)  # Wait for 3 seconds to ensure the device is released

def start_recording():
    global record_process
    ensure_recordings_directory()
    logging.debug("Starting recording...")
    record_command = [
        "ffmpeg",
        "-itsoffset", str(AUDIO_OFFSET),  # Adjust the offset value for audio sync
        "-f", "alsa", "-ac", "2", "-i", str(ALSA_AUDIO_SOURCE), # Input from ALSA
        "-thread_queue_size", "64",
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental", # Flags for low latency
        "-f", "v4l2", "-framerate", str(FRAME_RATE), "-video_size", str(VIDEO_SIZE), "-input_format", "yuyv422", "-i", "/dev/video0", # Video input settings
        "-probesize", "32", "-analyzeduration", "0", # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", f"{BITRATE}k", "-maxrate", f"{BITRATE}k", "-bufsize", f"{BUFFER_SIZE}k", # Video encoding settings
        "-vf", "format=yuv420p", "-g", str(KEYFRAME),  # Keyframe interval
        "-profile:v", "main",
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100", # Audio encoding settings
        "-max_delay", "0", # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1", # Use wallclock timestamps
        "-flush_packets", "1", # Flush packets
        "-async", "1", # Sync audio with video
        "-f", "mp4", f"recordings/recording_{int(time.time())}.mp4"
    ]
    record_process = subprocess.Popen(record_command)
    GPIO.output(RECORD_LED_PIN, GPIO.HIGH)
    logging.debug("Recording started!")

def stop_recording():
    global record_process
    if record_process:
        logging.debug("Stopping recording...")
        record_process.terminate()
        record_process.wait()
        record_process = None
        GPIO.output(RECORD_LED_PIN, GPIO.LOW)
        logging.debug("Recording stopped!")
        time.sleep(3)  # Wait for 3 seconds to ensure the device is released

def shutdown_pi():
    logging.debug("Rebooting...")
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    GPIO.cleanup()
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])

try:
    while True:
        current_time = time.time()

        current_stream_button_state = GPIO.input(STREAM_BUTTON_PIN)
        current_record_button_state = GPIO.input(RECORD_BUTTON_PIN)
        current_shutdown_button_state = GPIO.input(SHUTDOWN_BUTTON_PIN)
        
        if current_stream_button_state == GPIO.LOW and last_stream_button_state == GPIO.HIGH:
            if current_time - last_stream_action_time >= ACTION_DELAY:
                last_stream_action_time = current_time
                if recording:
                    stop_recording()
                    recording = False
                if not streaming:
                    start_stream()
                    streaming = True
                else:
                    stop_stream()
                    streaming = False

        if current_record_button_state == GPIO.LOW and last_record_button_state == GPIO.HIGH:
            if current_time - last_record_action_time >= ACTION_DELAY:
                last_record_action_time = current_time
                if streaming:
                    stop_stream()
                    streaming = False
                if not recording:
                    start_recording()
                    recording = True
                else:
                    stop_recording()
                    recording = False

        if current_shutdown_button_state == GPIO.LOW and last_shutdown_button_state == GPIO.HIGH:
            if current_time - last_shutdown_action_time >= ACTION_DELAY:
                last_shutdown_action_time = current_time
                shutdown_pi()
        
        last_stream_button_state = current_stream_button_state
        last_record_button_state = current_record_button_state
        last_shutdown_button_state = current_shutdown_button_state
        time.sleep(0.1)  # adjust this value to suit your needs

except KeyboardInterrupt:
    logging.debug("Script interrupted by user")

finally:
    if streaming:
        stop_stream()
    if recording:
        stop_recording()
    GPIO.cleanup()
