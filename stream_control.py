import RPi.GPIO as GPIO
import time
import subprocess
import os
import logging

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

# RTMP stream settings
STREAM_KEY = "abc123"  # Replace with your actual stream key
RTMP_SERVER = "192.168.0.40"
RTMP_PORT = "1935"

# PulseAudio source
PULSE_AUDIO_SOURCE = "alsa_input.usb-EVGA_EVGA_XR1_Lite_Capture_Box_Video_385203099807-02.analog-stereo"

# Initialize variables
streaming = False
recording = False
last_stream_button_state = GPIO.input(STREAM_BUTTON_PIN)
last_record_button_state = GPIO.input(RECORD_BUTTON_PIN)
last_shutdown_button_state = GPIO.input(SHUTDOWN_BUTTON_PIN)
stream_process = None
record_process = None

def ensure_recordings_directory():
    if not os.path.exists('recordings'):
        os.makedirs('recordings')

def start_stream():
    global stream_process
    logging.debug("Starting stream...")
    stream_command = [
        "ffmpeg",
        "-itsoffset", "-0.8",  # Adjust the offset value for audio sync
        "-f", "pulse", "-ac", "2", "-i", PULSE_AUDIO_SOURCE,  # Input from PulseAudio
        "-thread_queue_size", "64",
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental",  # Flags for low latency
        "-f", "v4l2", "-framerate", "60", "-video_size", "1280x720", "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-probesize", "32", "-analyzeduration", "0",  # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", "60",  # Video filter and keyframe interval
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100",  # Audio encoding settings
        "-max_delay", "0",  # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-async", "1",  # Sync audio with video
        "-f", "flv", f"rtmp://{RTMP_SERVER}:{RTMP_PORT}/live/{STREAM_KEY}"  # Output to RTMP server
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
        "-itsoffset", "-0.8",  # Adjust the offset value for audio sync
        "-f", "pulse", "-ac", "2", "-i", PULSE_AUDIO_SOURCE,  # Input from PulseAudio
        "-thread_queue_size", "64",
        "-fflags", "nobuffer", "-flags", "low_delay", "-strict", "experimental",  # Flags for low latency
        "-f", "v4l2", "-framerate", "60", "-video_size", "1280x720", "-input_format", "yuyv422", "-i", "/dev/video0",  # Video input settings
        "-probesize", "32", "-analyzeduration", "0",  # Lower probing size and analysis duration for reduced latency
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",  # Video encoding settings
        "-vf", "format=yuv420p", "-g", "60",  # Video filter and keyframe interval
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100",  # Audio encoding settings
        "-max_delay", "0",  # Max delay set to 0 for low latency
        "-use_wallclock_as_timestamps", "1",  # Use wallclock timestamps
        "-flush_packets", "1",  # Flush packets
        "-async", "1",  # Sync audio with video
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
        current_stream_button_state = GPIO.input(STREAM_BUTTON_PIN)
        current_record_button_state = GPIO.input(RECORD_BUTTON_PIN)
        current_shutdown_button_state = GPIO.input(SHUTDOWN_BUTTON_PIN)
        
        if current_stream_button_state == GPIO.LOW and last_stream_button_state == GPIO.HIGH:
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
