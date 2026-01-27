#!/bin/bash

# Function to confirm installation with the user
confirm_installation() {
    echo "This script will install and configure the Raspi-Streamer application."
    echo "It will perform the following actions:"
    echo " - Update and upgrade system packages."
    echo " - Install required software: ffmpeg, alsa-utils, python3-venv, pip, samba, git."
    echo " - Set up a Python virtual environment and install dependencies."
    echo " - Configure a Samba share for network access to recordings."
    echo " - Create and enable a systemd service to run the application on boot."
    echo " - Prompt you for a username/password for the web UI."
    echo " - Prompt you to specify a custom recordings directory."
    echo " - Prompt you to select an audio capture device."
    echo ""
    read -rp "Do you wish to continue? (y/n) " choice
    case "$choice" in
      y|Y ) echo "Starting installation...";;
      * ) echo "Installation cancelled."; exit 1;;
    esac
}

# Function to prompt for and save basic auth credentials
set_basic_auth_credentials() {
    read -rp "Enter the Basic Auth username: " username
    read -rsp "Enter the Basic Auth password: " password
    echo

    auth_file=".auth"

    echo "BASIC_AUTH_USERNAME=$username" > "$auth_file"
    echo "BASIC_AUTH_PASSWORD=$password" >> "$auth_file"
    echo "BASIC_AUTH_FORCE=True" >> "$auth_file"

    echo "Basic Auth credentials have been saved to $auth_file"
}

# Function to prompt for and configure recordings directory
setup_recordings_directory() {
    DEFAULT_RECORDINGS_DIR="$WORK_DIR/recordings"
    
    echo ""
    echo "By default, recordings are saved to: $DEFAULT_RECORDINGS_DIR"
    read -rp "Do you want to use a custom directory for recordings? (y/n) " choice
    
    case "$choice" in 
        y|Y )
            read -rp "Enter the full path for the recordings directory: " custom_dir
            
            # Remove trailing slash
            custom_dir="${custom_dir%/}"

            if [ "$custom_dir" == "$DEFAULT_RECORDINGS_DIR" ]; then
                echo "Custom directory is the same as default. No changes made."
                return
            fi

            # Create custom directory if it doesn't exist
            if [ ! -d "$custom_dir" ]; then
                echo "Directory $custom_dir does not exist. Creating it..."
                if ! mkdir -p "$custom_dir" 2>/dev/null; then
                     echo "Failed to create directory as current user, trying sudo..."
                     sudo mkdir -p "$custom_dir"
                     sudo chown "$CURRENT_USER":"$CURRENT_USER" "$custom_dir"
                fi
            fi
            
            # Handle existing recordings directory
            if [ -d "$DEFAULT_RECORDINGS_DIR" ] && [ ! -L "$DEFAULT_RECORDINGS_DIR" ]; then
                echo "Moving existing recordings from $DEFAULT_RECORDINGS_DIR to $custom_dir..."
                mv "$DEFAULT_RECORDINGS_DIR"/* "$custom_dir/" 2>/dev/null
                rm -rf "$DEFAULT_RECORDINGS_DIR"
            elif [ -L "$DEFAULT_RECORDINGS_DIR" ]; then
                rm "$DEFAULT_RECORDINGS_DIR"
            fi
            
            # Create symlink
            ln -s "$custom_dir" "$DEFAULT_RECORDINGS_DIR"
            echo "Symlink created: $DEFAULT_RECORDINGS_DIR -> $custom_dir"
            ;;
        * )
            echo "Using default recordings directory."
            if [ ! -d "$DEFAULT_RECORDINGS_DIR" ]; then
                mkdir -p "$DEFAULT_RECORDINGS_DIR"
            fi
            ;;
    esac
}

# Function to list audio devices and prompt user for selection
select_audio_device() {
    arecord_output=$(arecord -l)
    device_list=()
    echo "Available audio devices:"
    while IFS= read -r line; do
        if [[ $line == *"card"* && $line == *"device"* ]]; then
            device_list+=("$line")
            echo "${#device_list[@]}: $line"
        fi
    done <<< "$arecord_output"

    if [ ${#device_list[@]} -eq 0 ]; then
        echo "No audio devices found. Exiting."
        exit 1
    fi

    echo -n "Enter the number of the audio device you want to use: "
    read -r device_number

    if ! [[ "$device_number" =~ ^[0-9]+$ ]] || [ "$device_number" -lt 1 ] || [ "$device_number" -gt ${#device_list[@]} ]; then
        echo "Invalid selection. Exiting."
        exit 1
    fi

    chosen_device="${device_list[$((device_number - 1))]}"
    device_name=$(echo "$chosen_device" | awk -F '[][]' '{print $2}')

    echo "$device_name" > audio_device.txt
    echo "Audio device $device_name has been written to audio_device.txt"
    echo "Run the installer again if you need to change this device. You can also manually change the device in the audio_device.txt file."
}

# Get the current working directory and current user
WORK_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Confirm with the user before starting
confirm_installation

# Update and upgrade system packages
sudo apt update && sudo apt upgrade -y

# Install necessary packages
sudo apt install -y ffmpeg alsa-tools alsa-utils python3-venv python3-pip v4l-utils samba samba-common-bin git wget

# Install USB Automount Utility
echo "Installing USB Automount Utility..."
wget -O pi-usb-automount.deb https://github.com/fasteddy516/pi-usb-automount/releases/latest/download/pi-usb-automount.deb
sudo dpkg -i pi-usb-automount.deb
rm pi-usb-automount.deb

# Set permissions for USB mount point
if mountpoint -q /media/usb0; then
    echo "usb drive detected and mounted on: /media/usb0"
    echo "Setting permissions on /media/usb0"
    sudo chown -R "$CURRENT_USER":"$CURRENT_USER" /media/usb0
    sudo chmod -R 777 /media/usb0
else
    echo "No USB drive found. Skipping automount."
fi

# Update the Raspberry Pi Firmware
sudo rpi-update
# Change to the working directory
cd "$WORK_DIR"

# Create python virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate

# Update the code base
git pull

# Rename sample.env to .env if it exists
if [ -f "sample.env" ]; then
    mv sample.env .env
    echo "sample.env renamed to .env"
else
    echo "sample.env not found"
fi

# Rename sample.auth to .auth if it exists
if [ -f "sample.auth" ]; then
    mv sample.auth .auth
    echo "sample.auth renamed to .auth"
else
    echo "sample.auth not found"
fi

# Prompt for and save basic auth credentials
set_basic_auth_credentials

# Setup recordings directory
setup_recordings_directory

# Setup Samba share configuration
SAMBA_CONF="/etc/samba/smb.conf"
SHARE_CONF="[raspi-streamer]
   path = $WORK_DIR
   browseable = yes
   writable = yes
   only guest = no
   create mask = 0777
   directory mask = 0777
   public = yes"

# Remove any existing raspi-streamer configuration
sudo sed -i '/\[raspi-streamer\]/,/^$/d' "$SAMBA_CONF"

# Add the new configuration
echo "$SHARE_CONF" | sudo tee -a "$SAMBA_CONF"
sudo smbpasswd -a $CURRENT_USER
sudo systemctl restart smbd
echo "Samba share configured"

# Create stream_control service file
SERVICE_FILE="/etc/systemd/system/stream_control.service"

# Remove existing service file if it exists
if [ -f "$SERVICE_FILE" ]; then
    sudo rm "$SERVICE_FILE"
    echo "Existing stream_control.service deleted"
fi

# Create the new service file
sudo tee "$SERVICE_FILE" > /dev/null <<EOL
[Unit]
Description=Stream Control Service
After=network.target sound.target

[Service]
StartDelaySec=3
ExecStart=/usr/bin/sudo -E $WORK_DIR/.venv/bin/python $WORK_DIR/stream_control.py
WorkingDirectory=$WORK_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$CURRENT_USER
Group=$CURRENT_USER
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOL

echo "stream_control.service created"

# Reload systemd daemon and enable/start the stream_control service
sudo systemctl daemon-reload
sudo systemctl enable stream_control.service
sudo systemctl restart stream_control.service

# Get the IP address of the Raspberry Pi
IP_ADDRESS=$(hostname -I | awk '{print $1}')

# Select audio device
select_audio_device

echo "Installation complete"
echo "Please reboot the Raspberry Pi and then visit http://$IP_ADDRESS:5000 to access the Web UI."
