#!/bin/bash

# Function to get the value from audio_device.txt
get_device_value() {
    local device_file="audio_device.txt"
    if [[ -f "$device_file" ]]; then
        cat "$device_file"
    else
        echo "audio_device.txt file not found"
        exit 1
    fi
}

# Function to get the audio device
get_audio_device() {
    local device_value="$1"
    arecord_output=$(arecord -l)
    while IFS= read -r line; do
        if [[ $line == *"$device_value"* ]]; then
            card=$(echo "$line" | awk '{print $2}' | tr -d ':')
            device=$(echo "$line" | grep -oP '(?<=device )\d+')
            if [[ $device_value == hw:* || $device_value == plughw:* ]]; then
                echo "${device_value}${card},${device}"
            else
                echo "hw:${card},${device}"
            fi
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
device_value=$(get_device_value)
audio_device=$(get_audio_device "$device_value")
if [[ -n "$audio_device" ]]; then
    update_env_file "$audio_device"
    echo "Updated .env file with ALSA_AUDIO_SOURCE=${audio_device}"
else
    echo "No suitable audio device found"
fi
