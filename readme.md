# Project Overview: Raspberry Pi Streaming and Recording Setup
This project aims to do one thing well and that is to stream to a rtmp endpoint with very little setup and effort. 

Transform a Raspberry Pi into a powerful yet simple and convenient streaming and recording device using a USB capture card and a Web UI. The compact setup allows for seamless streaming to platforms like Twitch, Owncast, PeerTube, YouTube, and recording captured video and audio.

All you have to do is connect it to the internet, plug in your HDMI source from a console, Steam Deck, TV, or any device that can be captured via HDMI. When you are ready to stream, press the Start Stream button. Press the Stop Stream button when you are done. It can also record whatever is being captured with a different button.

You can also control the Raspi-Streamer using the Web UI from any web browser. Just visit http://<ip_address_of_pi>:5000 from your mobile device connected to the same network to start, stop, and manage your streams and recordings remotely.

## Key Features
- __Streaming:__ Capture video via a USB capture device and stream it in real-time to an RTMP server, ensuring smooth and reliable video output.
- __Audio Synchronization:__ Achieve perfect sync between audio and video using ALSA for audio input.
- __Automated Control:__ A Python script runs as a system service, enabling the device to handle streaming and recording commands autonomously.
- __Network Accessibility:__ With Samba configured, easily access and manage your recordings over the network from any device.
- __Web UI:__ Control and configure Raspi-Streamer from any web browser. Just visit http://<ip_address_of_pi>:5000 from your mobile device connected to the same network.
- __Versatile Use Cases:__ Ideal for streaming and recording gameplay, live events, concerts, GoPro cameras, and any other HDMI output devices.
- __Compact and Convenient:__ The small form factor of the Raspberry Pi makes it easy to integrate into any setup, offering a simple and portable solution for streaming and recording.

## Components Used
- __Raspberry Pi 4:__ The core of the setup, handling all processing and control logic.
- __USB Capture Device:__ Captures video from an external source.
- __ALSA (Advanced Linux Sound Architecture):__ Handles audio input and audio capture.

# Setup guide

## Prerequisites
- You have already installed the Lite version of Raspberry Pi OS.
- A user has been created.

# Install necessary packages
```bash
sudo apt install git
```

# Installer script
- Clone this repo to your Raspberry Pi. 
- `git clone https://github.com/teklynk/raspi-streamer`
- `cd raspi-streamer`
- `./install.sh`
- That's it. No need to manually install.

# Manual install

These steps are only nessasary if you do not want to use the `install.sh` script.

```bash
sudo apt install ffmpeg python3-dotenv python3-flask v4l-utils samba samba-common-bin nodejs npm git
```

# Web UI setup
```bash
npm init -y
npm install express dotenv
```

# Identify the audio source
```bash
arecord -l
```

```bash
**** List of CAPTURE Hardware Devices ****
card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

This will list the available capture hardware devices. Note the device identifier (e.g., "hw:1,0" for card 1, device 0).

You can use the `update_audio_device.sh` script to automatically set your capture card audio. 

Review and modify the `update_audio_device.sh` script for your specific device. Run: `arecord -l` to get details about the connected audio/video devices.


# Create project directory
```bash
mkdir -p /home/teklynk/raspi-streamer
```

# Setup Samba share

Edit Samba configuration file
```bash
sudo nano /etc/samba/smb.conf
```

```bash
[raspi-streamer]
path = /home/teklynk/raspi-streamer
browseable = yes
writable = yes
only guest = no
create mask = 0777
directory mask = 0777
public = yes
```

## Set Samba password for the user
```bash
sudo smbpasswd -a teklynk
```

## Restart Samba service
```bash
sudo systemctl restart smbd
```

# Install as a system service 

## Create systemd service file

```bash
[Unit]
Description=Stream Control Service
After=network.target sound.target

[Service]
ExecStartPre=/bin/sleep 10
ExecStartPre=/home/teklynk/raspi-streamer/update_audio_device.sh
ExecStartPre=/bin/sleep 1
ExecStart=/usr/bin/sudo -E /usr/bin/python3 /home/teklynk/raspi-streamer/stream_control.py
WorkingDirectory=/home/teklynk/raspi-streamer
StandardOutput=inherit
StandardError=inherit
Restart=always
User=teklynk
Group=teklynk
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

This will ensure that the `update_audio_device.sh` script runs before the `stream_control.py` script starts

## Reload systemd daemon and enable/start the service

```bash
sudo systemctl daemon-reload

sudo systemctl enable stream_control.service

sudo systemctl restart stream_control.service

sudo systemctl status stream_control.service
```

Rename `sample.env` to `.env` and update it with your specific settings.

# Static IP Address

```bash
nmcli connection show
```
```bash
sudo nmcli connection modify "Wired connection 1" ipv4.addresses 192.168.0.100/24 ipv4.gateway 192.168.0.1 ipv4.dns "192.168.0.1 8.8.8.8" ipv4.method manual
```
```bash
sudo nmcli connection down "Wired connection 1" && sudo nmcli connection up "Wired connection 1"
```
```bash
nmcli connection show "Wired connection 1"
```

# Disable WiFi and Bluetooth

```bash
sudo nano /boot/firmware/config.txt
```
```bash
dtoverlay=disable-bt
dtoverlay=disable-wifi
```
To prevent the Bluetooth service from starting

```bash
sudo systemctl disable hciuart
```
```bash
sudo reboot
```

# Additional Notes
- __Samba Setup:__
  - Customize the Samba configuration (smb.conf) according to your security and network requirements.
  - Adjust permissions (create mask, directory mask) in the Samba share configuration as necessary for your use case.
- __Audio Latency:__
  - Audio latency may need adjustment depending on your capture device. Experiment with different -itsoffset values in stream_control.py. Start with: "-itsoffset", "0.1".
- __Service Management:__
  - If you make changes to the stream_control.py script or .env, restart the stream_control service to apply the updates.
- __Performance Tips:__
  - The values in `sample.env` worked best for testing on a Raspberry Pi 4 8GB with Twitch and Owncast. Your experience may vary.
  - KEYFRAME_INTERVAL=60 corresponds to a 2-second keyframe interval, calculated as framerate * 2 (e.g., 30 fps * 2 = 60).
- __Stream & Record:__
  - If you would like to record while you stream you will need to set the m3u8 URL. The Stream & Record feature will not work if this is not set. Recordings are saved in the recordings directory.
- __Twitch Streaming:__
  - Visit [Twitch list of ingest servers](https://help.twitch.tv/s/twitch-ingest-recommendation?language=en_US) to find the rtmp url needed to stream to Twitch.
- __File Stream:__
  - File streaming can stream a mp4 or playlist.txt file. The stream will loop the file or playlist. File streaming does not re-encoded the file (I tried but the Pi could not handle it. CPU=100%). Use files that are properly converted and able to stream. If streaming a playlist.txt of files, be sure that all of the files are a consistent format, bitrate, resolution... Do not try to stream a 4k or Bluray quality file. Convert the file down to 1280x720 with a program like HandBrake.

# Troubleshooting
Find out what resolutions your capture device is capable of:

```bash
v4l2-ctl --list-formats-ext
```

```bash
ffmpeg -list_formats all -f v4l2 -i /dev/video0
```

## Update device firmware
In my case with the EVGA XR1 Lite usb capture device, I had to update its firmware in order for `v4l2-ctl --list-formats-ext` to show resolutions above 1280x720 30fps. After the firmware update it now shows 1080p and 720p at 60fps. It also allowed me to disable HDCP. Check if your device has a firmware update.

## USB 3.0 Devices
Make sure that your capture device is connected to the (blue) USB 3.0 port and that you are using a USB 3.0 cable.

## Service status
Check the status of stream_control for errors.
```bash
sudo service stream_control status
```

# Screenshots

## Here is my setup:
- Raspberry Pi 4 8gb
- Argon One case
- EVGA XR1 USB Capture card
- HDMI Splitter 1 in 2 Out

This is all stored under my entertainment center and powered on when I want to stream from my game consoles. I use the Web UI from my phone to control Raspi-Streamer.

<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer_rpi_1.png?raw=true" style=" width:400px;" />
</div>

## Web UI
<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/screenshot_webui_1.png?raw=true" style=" width:400px;" />
</div>
<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/screenshot_webui_2.png?raw=true" style=" width:400px;" />
</div>

# Future Plans
This project is ongoing, with exciting future enhancements in the pipeline:
- __Web UI:__
  - Ability to create multiple config files for various platforms and/or stream settings and choose a config to use for streaming or recording.