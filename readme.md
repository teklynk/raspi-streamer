sudo apt install ffmpeg python3-rpi-lgpio samba samba-common-bin pulseaudio

pulseaudio --start

pactl list short sources

# PulseAudio source
PULSE_AUDIO_SOURCE = "alsa_input.usb-EVGA_EVGA_XR1_Lite_Capture_Box_Video_385203099807-02.analog-stereo"

mkdir -p /home/teklynk/raspi-streamer

sudo nano /etc/samba/smb.conf

[raspi-streamer]
path = /home/teklynk/raspi-streamer
browseable = yes
writable = yes
only guest = no
create mask = 0777
directory mask = 0777
public = yes

sudo smbpasswd -a teklynk

sudo systemctl restart smbd

id -u teklynk

# Install as a system service 
sudo nano /etc/systemd/system/stream_control.service

[Unit]
Description=Stream Control Service
After=network.target sound.target

[Service]
ExecStart=/usr/bin/sudo -E /usr/bin/python3 /home/teklynk/raspi-streamer/stream_control.py
WorkingDirectory=/home/teklynk/raspi-streamer
StandardOutput=inherit
StandardError=inherit
Restart=always
User=teklynk
Group=teklynk
Environment="PYTHONUNBUFFERED=1"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse/"  # Ensure the correct user ID is here

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable stream_control.service
sudo systemctl restart stream_control.service

sudo systemctl status stream_control.service