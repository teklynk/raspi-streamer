<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/static/assets/icons/android-chrome-256x256.png?raw=true" />
</div>

# Project Overview: Raspberry Pi Streaming and Recording Setup
- The project aims to provide easy streaming to a rtmp endpoint using a Raspberry Pi, USB capture card, and Web UI.
- Seamless streaming to platforms like Twitch, Owncast, PeerTube, YouTube, with video and audio recording capabilities.
- Simple setup: connect to the internet, plug in HDMI source from any device, and control with Start Stream and Stop Stream buttons.
- Web UI for remote control from any web browser, allowing management of streams and recordings.
- Comparable to professional-grade devices like LiveStream Broadcaster Pro and BoxCaster, but without high costs and subscription fees.
- Ideal for live events, concerts, churches, conferences, and seminars when used with a professional camera.

## Key Features
- __Streaming:__ Capture video via a USB capture device and stream it in real-time to an RTMP server, ensuring smooth and reliable video output.
- __Audio Synchronization:__ Achieve perfect sync between audio and video using ALSA for audio input.
- __Automated Control:__ A Python script runs as a system service, enabling the device to handle streaming and recording commands autonomously.
- __Network Accessibility:__ With Samba configured, easily access and manage your recordings over the network from any device.
- __Web UI:__ Control and configure Raspi-Streamer from any web browser. Just visit http://<ip_address_of_pi>:5000 from your mobile device connected to the same network.
- __Versatile Use Cases:__ Ideal for streaming and recording gameplay, live events, concerts, GoPro cameras, and any other HDMI output devices.
- __Compact and Convenient:__ The small form factor of the Raspberry Pi makes it easy to integrate into any setup, offering a simple and portable solution for streaming and recording.

## Components Used
- __Raspberry Pi 5:__ The core of the setup, handling all processing and control logic.
- __USB Capture Device:__ Captures video from an external source.
- __ALSA (Advanced Linux Sound Architecture):__ Handles audio input and audio capture.

# Setup guide

## Prerequisites before installing
- You have already installed the Lite version of Raspberry Pi OS.
- A user has been created.
- Your capture device is currently plugged into the Raspberry Pi.

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
- Review the `install.sh` script if you would like to see what it installs and how.

# Additional Notes
- __Samba Setup:__
  - Customize the Samba configuration (smb.conf) according to your security and network requirements.
  - Adjust permissions (create mask, directory mask) in the Samba share configuration as necessary for your use case.
- __Audio Latency:__
  - Audio latency may need adjustment depending on your capture device. Experiment with different -itsoffset values in stream_control.py. Start with: "-itsoffset", "0.1".
- __Service Management:__
  - If you make changes to the stream_control.py script or .env, restart the stream_control service to apply the updates.
- __Performance Tips:__
  - Raspberry Pi 5 will give you the best results.
  - The values in `sample.env` worked best for testing on a Raspberry Pi 4 8GB with Twitch and Owncast. Your experience may vary.
  - KEYFRAME_INTERVAL=60 corresponds to a 2-second keyframe interval, calculated as framerate * 2 (e.g., 30 fps * 2 = 60).
- __Stream & Record:__
  - If you would like to record a local copy while you stream you will need to set the m3u8 URL. The Stream & Record feature will not work if this is not set. This is becuase the stream & record feature is simply recording the stream using the m3u8 url. Keep in mind that if the stream goes does down, then so does the recording. Recordings are saved in the recordings directory. Some platforms like Twitch, Kick, YouTube, DLive will automatically save a stream/VOD that you can download. You may not even need to use this feature. I mainly use this feature with my Owncast server since Owncast does not automatically save the stream/VOD. 
- __Twitch Streaming:__
  - Visit [Twitch list of ingest servers](https://help.twitch.tv/s/twitch-ingest-recommendation?language=en_US) to find the rtmp url needed to stream to Twitch.
- __File Stream:__
  - File streaming can stream a mp4 or playlist.txt file. The stream will loop the file or playlist. File streaming does not re-encoded the file (I tried but the Pi could not handle it. CPU=100%). Use files that are properly converted and able to stream. If streaming a playlist.txt of files, be sure that all of the files are a consistent format, bitrate, resolution... Do not try to stream a 4k or Bluray quality file. Convert the file down to 1280x720 with a program like HandBrake. 
  - PLAYLIST: Place files inside a folder called `media` and run the `create_playlist.sh` script. This will generate a `playlist.txt` file inside the `/home/<user>/raspi-streamer/` directory. In the web UI you can set the File Stream Path to: `/home/<user>/raspi-streamer/playlist.txt`

# Troubleshooting

## Test recording before doing a stream
You can do a test recording before doing a stream to check if the capture device is working and the quality. Recordings are saved in the recordings directory. You can access the recording from the smb share or directly from the sd card.

## Find out what resolutions your capture device is capable of
```bash
v4l2-ctl --list-formats-ext
```

```bash
ffmpeg -list_formats all -f v4l2 -i /dev/video0
```
Choose a Format option that your capture card supports (mjpeg, yuyv422, nv12). 

## Update device firmware
In my case with the EVGA XR1 Lite usb capture device, I had to update its firmware in order for `v4l2-ctl --list-formats-ext` to show resolutions above 1280x720 30fps. After the firmware update it now shows 1080p and 720p at 60fps. It also allowed me to disable HDCP. Check if your device has a firmware update.

## USB 3.0 Devices
Make sure that your capture device is connected to the (blue) USB 3.0 port and that you are using a USB 3.0 cable.

## Service status
Check the status of stream_control for errors.
```bash
sudo service stream_control status
```

## Remove and add capture device from the command line
This is handy if the device seems to be in a hung state or it is producing strange results. Capture devices are not perfect or consistent.
```bash
sudo modprobe -r uvcvideo && sudo modprobe uvcvideo
```

## Overclocking
You can try to overclock the Raspberry Pi 4 to squeeze a bit more processing power out of it. This may help improve streaming and recording.
```bash
sudo nano /boot/firmware/config.txt
```
__Raspberry Pi 4__

Add this to the end of config.txt.
```bash
over_voltage=6
arm_freq=2000
```

__Raspberry Pi 5__

Add this the end of config.txt.
```bash
arm_freq=2600
gpu_freq=1000
over_voltage_delta=40000
```

## Static IP Address
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

## Re-install to re-configure
Run the `install.sh` script again to pull down the latest updates, reconfigure smb share, set a new username and password, set a new capture device.

# Screenshots

## Here is my setup:
- Raspberry Pi 4 8gb
- EVGA XR1 USB Capture card
- HDMI Splitter 1 in 2 Out

This is all stored under my entertainment center and powered on when I want to stream from my game consoles. I use the Web UI from my phone to control Raspi-Streamer.

<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer_rpi_1.png?raw=true" style="width:400px;" />
</div>

Here is a more compact setup using a cheap [($14) USB capture device](https://a.co/d/he5fanX) and [2 right angled USB 3 connectors](https://a.co/d/fuRkyZH). All purchased from Amazon. The capture device is held in place with heavy duty double sided tape.

<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer-setup-800w.png?raw=true" style="width:400px;" />
</div>

## Web UI
<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer-1.png?raw=true" style="width:400px;" />
</div>
<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer-2.png?raw=true" style="width:400px;" />
</div>
<div style="text-align:center;margin:4px;display:block;">
<img src="https://github.com/teklynk/raspi-streamer/blob/main/screenshots/raspi-streamer-3.png?raw=true" style="width:400px;" />
</div>

# Future Plans
This project is ongoing, with exciting future enhancements in the pipeline:
- __Web UI:__
  - Ability to create multiple config files for various platforms and/or stream settings and choose a config to use for streaming or recording.
  - Schedule a stream (regularly recurring streams)
