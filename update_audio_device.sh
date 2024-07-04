#!/bin/bash

# The purpose of this script: 
# Sometimes when the Pi reboots it will randomly assign the capture device hw:1,0 or sometimes it would set it to: hw:2,0 or hw:3,0.
# I tried various things like creating a udev rule and an alias but nothing seemed to work. This solution is low effort and works.
# You may not even need this script if `arecord -l` shows consistent card:device after each reboot.
# Be sure that this script runs before the stream_control.py starts. Check the readme for including this script with the service. 
# Run: `arecord -l` to get a list of connected usb devices. 
# Update: `if [[ $line == *"EVGA XR1 Lite Capture Box Video"* ]]; then` to match your device name.

# Function to get the audio device
get_audio_device() {
    arecord_output=$(arecord -l)
    while IFS= read -r line; do
        if [[ $line == *"EVGA XR1 Lite Capture Box Video"* ]]; then
            card=$(echo "$line" | awk '{print $2}' | tr -d ':')
            device=$(echo "$line" | grep -oP '(?<=device )\d+')
            echo "hw:${card},${device}"
            return
        fi
    done <<< "$arecord_output"
}

# Function to update the .env file
update_env_file() {
    local audio_device="$1"
    local env_file=".env"
    
    if [[ -f "$env_file" ]]; then
        if grep -q "^ALSA_AUDIO_SOURCE=" "$env_file"; then
            sed -i "s/^ALSA_AUDIO_SOURCE=.*/ALSA_AUDIO_SOURCE=${audio_device}/" "$env_file"
        else
            echo "ALSA_AUDIO_SOURCE=${audio_device}" >> "$env_file"
        fi
    else
        echo "ALSA_AUDIO_SOURCE=${audio_device}" > "$env_file"
    fi
}

# Main script logic
audio_device=$(get_audio_device)
if [[ -n "$audio_device" ]]; then
    update_env_file "$audio_device"
    echo "Updated .env file with ALSA_AUDIO_SOURCE=${audio_device}"
else
    echo "No suitable audio device found"
fi
