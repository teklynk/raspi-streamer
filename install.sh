#!/bin/bash

set -e

# Install runtime packages using the host distribution's package manager.
install_system_packages() {
    if [ ! -r /etc/os-release ]; then
        echo "Cannot identify this Linux distribution (/etc/os-release is missing)."
        exit 1
    fi

    . /etc/os-release
    DISTRO_NAME=${PRETTY_NAME:-${ID:-Linux}}

    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg alsa-tools alsa-utils python3-venv python3-pip v4l-utils samba git kmod
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y ffmpeg alsa-utils python3 python3-pip v4l-utils samba git kmod
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y ffmpeg alsa-utils python3 python3-pip v4l-utils samba git kmod
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --needed --noconfirm ffmpeg alsa-utils alsa-tools python python-pip v4l-utils samba git kmod
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper --non-interactive refresh
        sudo zypper --non-interactive install ffmpeg alsa-utils alsa-tools python3 python3-pip v4l-utils samba git kmod
    elif command -v apk >/dev/null 2>&1; then
        sudo apk add ffmpeg alsa-utils python3 py3-pip py3-virtualenv v4l-utils samba git kmod
    else
        echo "No supported package manager found. Install ffmpeg, ALSA utilities, Python 3 with venv/pip, v4l-utils, Samba, git, and kmod manually."
        exit 1
    fi

    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "ffmpeg was not installed. Enable your distribution's repository that provides FFmpeg, then rerun this installer."
        exit 1
    fi

    echo "Installed runtime packages for $DISTRO_NAME."
}

# Function to confirm installation with the user
confirm_installation() {
    if [ "$EUID" -eq 0 ]; then
        echo "Please do not run this script as root (sudo). Run it as a regular user."
        echo "The script will ask for your sudo password when necessary."
        exit 1
    fi

    echo "This script will install and configure the Stream Control application."
    echo "It will perform the following actions:"
    echo " - Install required software using your Linux distribution's package manager."
    echo " - Set up a Python virtual environment and install dependencies."
    echo " - Configure a Samba share for network access to recordings."
    echo " - Create and enable a systemd service to run the application on boot."
    echo " - Prompt you for a username/password for the web UI."
    echo " - Prompt you to specify a custom recordings directory."
    echo " - Prompt you to select an audio capture device, if one is available."
    echo "USB storage mounting is managed by your Linux distribution; mounted drives can be selected for recordings."
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
            custom_dir=""
            mounted_drives=()
            for mount_dir in /media/usb* "/run/media/$CURRENT_USER"/* /media/"$CURRENT_USER"/*; do
                if [ -d "$mount_dir" ] && mountpoint -q "$mount_dir"; then
                    mounted_drives+=("$mount_dir")
                fi
            done

            if [ ${#mounted_drives[@]} -gt 0 ]; then
                echo "Mounted storage devices:"
                for i in "${!mounted_drives[@]}"; do
                    echo "$((i + 1)): ${mounted_drives[$i]}"
                done
                read -rp "Enter a device number to store recordings there, or press Enter to enter a path: " drive_number
                if [[ "$drive_number" =~ ^[0-9]+$ ]] && [ "$drive_number" -ge 1 ] && [ "$drive_number" -le ${#mounted_drives[@]} ]; then
                    custom_dir="${mounted_drives[$((drive_number - 1))]}/recordings"
                fi
            fi

            if [ -z "$custom_dir" ]; then
                read -rp "Enter the full path for the recordings directory: " custom_dir
            fi
            
            # Remove trailing slash
            custom_dir="${custom_dir%/}"

            if [ "$custom_dir" == "$DEFAULT_RECORDINGS_DIR" ]; then
                echo "Custom directory is the same as default. No changes made."
                return
            fi

            if [ -z "$custom_dir" ]; then
                echo "No recordings path was provided. Keeping the default directory."
                return
            fi

            mkdir -p "$custom_dir" 2>/dev/null || {
                sudo mkdir -p "$custom_dir"
                sudo chown "$CURRENT_USER":"$CURRENT_GROUP" "$custom_dir"
            }
            
            # Handle existing recordings directory
            if [ -d "$DEFAULT_RECORDINGS_DIR" ] && [ ! -L "$DEFAULT_RECORDINGS_DIR" ]; then
                echo "Moving existing recordings from $DEFAULT_RECORDINGS_DIR to $custom_dir..."
                sudo cp -a "$DEFAULT_RECORDINGS_DIR/." "$custom_dir/"
                sudo rm -rf "$DEFAULT_RECORDINGS_DIR"
            elif [ -L "$DEFAULT_RECORDINGS_DIR" ]; then
                sudo rm "$DEFAULT_RECORDINGS_DIR"
            fi
            
            # Create symlink
            ln -s "$custom_dir" "$DEFAULT_RECORDINGS_DIR"
            echo "Symlink created: $DEFAULT_RECORDINGS_DIR -> $custom_dir"
            ;;
        * )
            echo "Using default recordings directory."
            mkdir -p "$DEFAULT_RECORDINGS_DIR"
            ;;
    esac
}

# Function to list audio devices and prompt user for selection
select_audio_device() {
    arecord_output=$(arecord -l 2>/dev/null || true)
    device_list=()
    echo "Available audio devices:"
    while IFS= read -r line; do
        if [[ $line == *"card"* && $line == *"device"* ]]; then
            device_list+=("$line")
            echo "${#device_list[@]}: $line"
        fi
    done <<< "$arecord_output"

    if [ ${#device_list[@]} -eq 0 ]; then
        echo "No audio devices found. Skipping selection; configure ALSA_AUDIO_SOURCE when an audio device is available."
        return
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
CURRENT_GROUP=$(id -gn "$CURRENT_USER")

# Confirm with the user before starting
confirm_installation

if [ ! -d /run/systemd/system ] || ! command -v systemctl >/dev/null 2>&1; then
    echo "This installer requires a running systemd system to install the application service."
    exit 1
fi

# Install required packages without upgrading the whole operating system.
install_system_packages
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

# Setup a Samba share for recordings only; the application directory contains credentials.
SAMBA_CONF="/etc/samba/smb.conf"
SHARE_CONF="[stream-control-recordings]
   path = $WORK_DIR/recordings
   browseable = yes
   writable = yes
   guest ok = no
   valid users = $CURRENT_USER
   create mask = 0660
   directory mask = 0770"

# Remove any existing stream-control share configuration.
sudo sed -i '/^\[raspi-streamer\]/,/^$/d; /^\[stream-control-recordings\]/,/^$/d' "$SAMBA_CONF"

# Add the new configuration
echo "$SHARE_CONF" | sudo tee -a "$SAMBA_CONF"
sudo smbpasswd -a "$CURRENT_USER"
if sudo systemctl enable --now smbd 2>/dev/null; then
    sudo systemctl restart smbd
elif sudo systemctl enable --now smb 2>/dev/null; then
    sudo systemctl restart smb
else
    echo "Samba was installed, but its service unit was not found. Start the Samba service using your distribution's unit name."
fi
echo "Samba recordings share configured"

# Create stream_control service file
SERVICE_FILE="/etc/systemd/system/stream_control.service"

MODPROBE_PATH=$(command -v modprobe)
SUDOERS_FILE="/etc/sudoers.d/010_${CURRENT_USER}-uvcvideo"
echo "Allowing only the video-driver reload commands required by the app..."
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
$CURRENT_USER ALL=(root) NOPASSWD: $MODPROBE_PATH -r uvcvideo, $MODPROBE_PATH uvcvideo
EOF
sudo chmod 440 "$SUDOERS_FILE"

if sudo visudo -c -f "$SUDOERS_FILE"; then
    echo "Restricted uvcvideo sudo rule added."
else
    echo "Error: Invalid sudoers syntax in $SUDOERS_FILE"
    exit 1
fi

# Create the new service file
sudo tee "$SERVICE_FILE" > /dev/null <<EOL
[Unit]
LEGACY_SUDOERS_FILE="/etc/sudoers.d/010_${CURRENT_USER}-nopasswd"
if [ -f "$LEGACY_SUDOERS_FILE" ] && sudo grep -Fxq "$CURRENT_USER ALL=(ALL) NOPASSWD: ALL" "$LEGACY_SUDOERS_FILE"; then
    sudo rm "$LEGACY_SUDOERS_FILE"
    echo "Removed the legacy passwordless sudo-all rule."
fi
Description=Stream Control Service
Wants=network-online.target
After=network.target sound.target

[Service]
ExecStartPre=/bin/sleep 5
ExecStart=$WORK_DIR/.venv/bin/python $WORK_DIR/stream_control.py
WorkingDirectory=$WORK_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
RestartSec=5
User=$CURRENT_USER
Group=$CURRENT_GROUP
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOL

echo "stream_control.service created"

# Select audio before starting the service so the saved device is used on startup.
select_audio_device

# Reload systemd daemon and enable/start the stream_control service
sudo systemctl daemon-reload
sudo systemctl enable stream_control.service
sudo systemctl restart stream_control.service

# Get the IP address of the Raspberry Pi
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "Installation complete"
echo "Visit http://$IP_ADDRESS:5000 to access the Web UI."
