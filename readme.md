# Project Overview: Raspberry Pi Streaming and Recording Setup
This project aims to transform a Raspberry Pi into a powerful yet simple and convenient streaming and recording device using a USB capture card, push buttons, LEDs, and a Web UI. The compact setup allows for seamless streaming to platforms like Twitch, Owncast, PeerTube, YouTube, and recording high-quality video and audio, making it perfect for live streaming enthusiasts, content creators, and anyone interested in leveraging open-source tools to build custom media solutions.

It's a box that will stream or record whatever is connected to it via HDMI. All you have to do is connect it to the internet, plug in your HDMI source from a console, Steam Deck, TV, or any device that can be captured via HDMI. When you are ready to stream, just press the button on the box. An LED turns on to let you know you are streaming or recording. Press the button again when you are done. It can also record whatever is being captured with a different button.

For added convenience, you can also control the Raspi-Streamer using the Web UI from any web browser. Just visit http://<ip_address_of_pi>:5000 from your mobile device connected to the same network to start, stop, and manage your streams and recordings remotely.

## Key Features
- __Hardware Integration:__ Utilize the GPIO pins on the Raspberry Pi to connect push buttons and LEDs, providing a physical interface to start/stop streaming and recording with visual feedback.
- __High-Quality Streaming:__ Capture video via a USB capture device and stream it in real-time to an RTMP server, ensuring smooth and reliable video output.
- __Audio Synchronization:__ Achieve perfect sync between audio and video using ALSA for audio input, making sure your streams and recordings maintain professional quality.
- __Automated Control:__ A Python script runs as a system service, enabling the device to handle streaming and recording commands autonomously and recover gracefully from errors.
- __Network Accessibility:__ With Samba configured, easily access and manage your recordings over the network from any device.
- __Web UI:__ Control and configure Raspi-Streamer from any web browser. Just visit http://<ip_address_of_pi>:5000 from your mobile device connected to the same network.
- __Versatile Use Cases:__ Ideal for streaming and recording gameplay, live events, concerts, GoPro cameras, and any other HDMI output devices.
- __Compact and Convenient:__ The small form factor of the Raspberry Pi makes it easy to integrate into any setup, offering a simple and portable solution for high-quality streaming and recording.

## Components Used
- __Raspberry Pi 4:__ The core of the setup, handling all processing and control logic.
- __USB Capture Device:__ Captures high-definition video from an external source.
Push Buttons and LEDs: Provide a user-friendly interface for controlling the streaming and recording processes.
- __ALSA (Advanced Linux Sound Architecture):__ Handles audio input, ensuring low-latency and high-quality audio capture.

# Setup guide
## Prerequisites
- You have already installed the Lite version of Raspberry Pi OS.
- A user has been created and you have enabled Remote GPIO from `raspi-config`.

# Install necessary packages
```bash
sudo apt install ffmpeg python3-rpi-lgpio python3-dotenv python3-flask v4l-utils samba samba-common-bin nodejs npm
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

You can use the `update_audio_device.sh` script to automatically set your capture card audio. Review and modify the script for your specific device. Run: `arecord -l` to get details about the connected audio/video devices.


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
sudo nano /etc/systemd/system/stream_control.service
```

```bash
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

[Install]
WantedBy=multi-user.target
```

If using the `update_audio_device.sh` script you can add the script to the service like this:

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

# Additional Notes
- Rename `sample.env` to `.env` and update it with your specific settings.
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

# Future Plans
This project is ongoing, with exciting future enhancements in the pipeline:
- __Hardware Upgrade:__
  - We plan to incorporate the [Geekworm Raspberry Pi X630 V1.5 Hdmi to CSI-2 Module](https://geekworm.com/products/x630) to replace the current USB capture device. This module will be integrated onto a custom circuit board along with LEDs, buttons, and GPIO headers, creating a "hat" for the Raspberry Pi. This will streamline the setup, making it almost a plug-and-play solution.
- __Web UI:__
  - Ability to create multiple config files for various platforms and/or stream settings and choose a config to use for streaming or recording. A way to manage config files (create, edit, delete).
- __Installer:__
  - Install script that will install everything needed to get up and running. 