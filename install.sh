#!/bin/bash

# Get the current working directory and current user
WORK_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Update and upgrade system packages
sudo apt update && sudo apt upgrade -y

# Install necessary packages
sudo apt install -y ffmpeg python3-rpi-lgpio python3-dotenv python3-flask v4l-utils samba samba-common-bin nodejs npm git

# Change to the working directory
cd "$WORK_DIR"

# Update the code base
git pull

# Initialize npm and install node packages
npm init -y
npm install express dotenv

# Rename sample.env to .env if it exists
if [ -f "sample.env" ]; then
    mv sample.env .env
    echo "sample.env renamed to .env"
else
    echo "sample.env not found"
fi

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

if [ ! -f "$SERVICE_FILE" ]; then
    sudo tee "$SERVICE_FILE" > /dev/null <<EOL
[Unit]
Description=Stream Control Service
After=network.target sound.target

[Service]
ExecStartPre=/bin/sleep 10
ExecStartPre=$WORK_DIR/update_audio_device.sh
ExecStartPre=/bin/sleep 1
ExecStart=/usr/bin/sudo -E /usr/bin/python3 $WORK_DIR/stream_control.py
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
else
    echo "stream_control.service already exists"
fi

# Reload systemd daemon and enable/start the stream_control service
sudo systemctl daemon-reload
sudo systemctl enable stream_control.service
sudo systemctl restart stream_control.service

# Get the IP address of the Raspberry Pi
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "Installation complete"
echo "Please reboot the Raspberry Pi and then visit http://$IP_ADDRESS:5000 to access the Web UI."
