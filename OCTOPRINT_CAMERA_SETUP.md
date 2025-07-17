# OctoPrint Camera Setup Guide

This guide explains how to set up and configure cameras with OctoPrint for use with the LayerCapture plugin.

## Overview

OctoPrint supports various camera types through its webcam system. The LayerCapture plugin uses this system to capture images during printing. You can use either real cameras or the built-in fake camera for testing.

## Camera Types Supported

### 1. USB Webcams (Most Common)
- **Compatible**: Most USB UVC (USB Video Class) cameras
- **Recommended**: Logitech C270, C920, C922, Raspberry Pi Camera Module
- **Setup**: Usually plug-and-play on Linux systems

### 2. IP Cameras
- **Compatible**: Cameras that provide MJPEG streams
- **Examples**: Many security cameras, IP webcams
- **Setup**: Requires network configuration

### 3. Raspberry Pi Camera Module
- **Hardware**: Official Raspberry Pi Camera Module v1/v2/HQ
- **Setup**: Enable camera interface in Raspberry Pi configuration

## Setup Methods

### Method 1: OctoPi (Recommended for Raspberry Pi)

**OctoPi** is the official Raspberry Pi image that includes OctoPrint with pre-configured camera support.

1. **Download OctoPi**
   - Get latest image from: https://octoprint.org/download/
   - Use Raspberry Pi Imager for easy installation

2. **Flash to SD Card**
   ```bash
   # Using Raspberry Pi Imager (recommended)
   # Or using dd command:
   sudo dd bs=4M if=octopi-1.0.0.img of=/dev/sdX conv=fsync
   ```

3. **Configure WiFi** (before first boot)
   - Edit `octopi-wpa-supplicant.txt` on the SD card
   - Add your WiFi credentials

4. **Enable Camera** (if using Pi Camera)
   - SSH into the Pi: `ssh pi@octopi.local`
   - Run: `sudo raspi-config`
   - Navigate to "Interfacing Options" → "Camera" → "Enable"
   - Reboot: `sudo reboot`

### Method 2: Manual OctoPrint Installation

If you're installing OctoPrint manually, you'll need to set up the camera system separately.

#### For Raspberry Pi with Pi Camera:

1. **Enable Camera Interface**
   ```bash
   sudo raspi-config
   # Interfacing Options → Camera → Enable
   sudo reboot
   ```

2. **Install MJPG-Streamer**
   ```bash
   sudo apt update
   sudo apt install cmake libjpeg-dev
   
   cd ~
   git clone https://github.com/jacksonliam/mjpg-streamer.git
   cd mjpg-streamer/mjpg-streamer-experimental
   make
   sudo make install
   ```

3. **Create Startup Script**
   ```bash
   sudo nano /etc/systemd/system/mjpg-streamer.service
   ```
   
   Add content:
   ```ini
   [Unit]
   Description=MJPG Streamer
   After=network.target
   
   [Service]
   Type=forking
   User=pi
   ExecStart=/usr/local/bin/mjpg_streamer -i "input_raspicam.so -fps 10 -q 50 -x 640 -y 480" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
   
   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and Start Service**
   ```bash
   sudo systemctl enable mjpg-streamer
   sudo systemctl start mjpg-streamer
   ```

#### For USB Webcams:

1. **Check Camera Detection**
   ```bash
   lsusb  # Should list your USB camera
   ls /dev/video*  # Should show video devices
   ```

2. **Install Required Packages**
   ```bash
   sudo apt update
   sudo apt install fswebcam v4l-utils
   ```

3. **Test Camera**
   ```bash
   # Test image capture
   fswebcam -r 640x480 --jpeg 85 -D 1 test.jpg
   
   # Check camera capabilities
   v4l2-ctl --list-devices
   v4l2-ctl --list-formats
   ```

4. **Configure MJPG-Streamer for USB**
   ```bash
   # Example startup command for USB camera
   mjpg_streamer -i "input_uvc.so -d /dev/video0 -fps 10 -r 640x480" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
   ```

## OctoPrint Camera Configuration

### 1. Classic Webcam Setup (Built-in Plugin)

1. **Access OctoPrint Settings**
   - Open OctoPrint web interface
   - Go to Settings (wrench icon) → Webcam & Timelapse

2. **Configure Stream Settings**
   ```
   Stream URL: http://127.0.0.1:8080/?action=stream
   Snapshot URL: http://127.0.0.1:8080/?action=snapshot
   Path to FFMPEG: /usr/bin/ffmpeg
   ```

3. **Test Configuration**
   - Save settings
   - Reload OctoPrint interface
   - Check if webcam stream appears in Control tab

### 2. LayerCapture Plugin Configuration

1. **Install LayerCapture Plugin**
   - Go to Settings → Plugin Manager → Get More
   - Search for "LayerCapture" (or install manually)

2. **Configure Camera Settings**
   ```
   Use Fake Camera: ☐ (uncheck for real camera)
   Capture Delay: 2 seconds
   Pre-Capture Delay: 0.5 seconds
   Image Quality: 85
   Create Thumbnails: ☑ (check if desired)
   ```

3. **Test Capture**
   - Enable fake camera mode first
   - Start a test print
   - Monitor logs for capture events

## Troubleshooting

### Common Issues

1. **No Camera Stream**
   ```bash
   # Check if MJPG-Streamer is running
   ps aux | grep mjpg
   
   # Check if port is listening
   netstat -ln | grep 8080
   
   # Restart MJPG-Streamer
   sudo systemctl restart mjpg-streamer
   ```

2. **Permission Errors**
   ```bash
   # Add user to video group
   sudo usermod -a -G video pi
   
   # Fix device permissions
   sudo chmod 666 /dev/video0
   ```

3. **Poor Image Quality**
   - Adjust MJPG-Streamer quality settings (-q parameter)
   - Change resolution (-r parameter)
   - Adjust lighting conditions
   - Clean camera lens

4. **LayerCapture Errors**
   ```
   Check OctoPrint logs:
   - Go to Settings → Logs
   - Look for "layercapture" entries
   - Enable debug logging if needed
   ```

### Hardware-Specific Notes

#### Raspberry Pi Camera:
- **V1 (5MP)**: Good for basic timelapse, limited low-light performance
- **V2 (8MP)**: Better image quality, improved low-light
- **HQ Camera**: Excellent quality, requires C/CS mount lens

#### USB Webcams:
- **Logitech C270**: Budget option, 720p, good compatibility
- **Logitech C920**: Popular choice, 1080p, good quality
- **Logitech C922**: Similar to C920 with better low-light

## Performance Optimization

### 1. Camera Settings
```bash
# Lower resolution for better performance
-r 640x480    # Instead of 1920x1080

# Reduce framerate
-fps 5        # Instead of 30

# Adjust quality
-q 50         # Lower quality = smaller files
```

### 2. System Resources
```bash
# Monitor CPU usage
htop

# Check memory usage
free -h

# Monitor temperature (Raspberry Pi)
vcgencmd measure_temp
```

### 3. Network Optimization
- Use wired Ethernet instead of WiFi when possible
- Reduce stream quality for remote access
- Consider using VPN instead of port forwarding

## Security Considerations

⚠️ **Important Security Notes:**

1. **Network Exposure**
   - Never expose OctoPrint directly to the internet
   - Use VPN for remote access
   - Change default passwords

2. **Camera Privacy**
   - Camera streams may be accessible to network users
   - Consider physical camera shutters
   - Monitor access logs

3. **Authentication**
   - Enable OctoPrint access controls
   - Use strong passwords
   - Consider two-factor authentication

## Testing Your Setup

### 1. Basic Camera Test
```bash
# Test snapshot capture
curl http://127.0.0.1:8080/?action=snapshot -o test_snapshot.jpg

# Test stream access
curl -v http://127.0.0.1:8080/?action=stream
```

### 2. LayerCapture Plugin Test
1. Enable "Use Fake Camera" in plugin settings
2. Start a test print with virtual printer
3. Check if fake images are created in uploads/layercapture/
4. Disable fake camera and test real capture

### 3. Performance Test
```bash
# Monitor system during capture
while true; do
    echo "$(date): $(vcgencmd measure_temp) - $(free -m | grep Mem)"
    sleep 5
done
```

## Advanced Configuration

### Custom Camera Scripts
Create custom scripts for advanced camera control:

```bash
#!/bin/bash
# /home/pi/camera_control.sh

case "$1" in
    start)
        mjpg_streamer -i "input_raspicam.so -fps 10 -q 50 -x 640 -y 480" \
                     -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www" &
        ;;
    stop)
        pkill mjpg_streamer
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
esac
```

### Multiple Cameras
For setups with multiple cameras, configure additional MJPG-Streamer instances:

```bash
# Camera 1 (Pi Camera)
mjpg_streamer -i "input_raspicam.so" -o "output_http.so -p 8080" &

# Camera 2 (USB)
mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8081" &
```

## Support and Resources

- **OctoPrint Documentation**: https://docs.octoprint.org/
- **MJPG-Streamer**: https://github.com/jacksonliam/mjpg-streamer
- **OctoPrint Community**: https://community.octoprint.org/
- **LayerCapture Plugin Issues**: Create issues on the plugin's GitHub repository

---

**Note**: This guide covers the most common setups. Your specific hardware may require additional configuration. Always refer to your camera manufacturer's documentation for detailed specifications and requirements. 