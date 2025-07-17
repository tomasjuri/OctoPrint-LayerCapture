# OctoPrint Layer Capture Plugin

An OctoPrint plugin that automatically captures images at specified print layers with configurable grid positions for 3D print monitoring and analysis.

## Features

- 🔄 **Automatic Layer Detection**: Captures images at predefined layer intervals
- 📍 **Configurable Grid Capture**: Takes multiple images in a grid pattern around the print
- 🎯 **Precise Positioning**: Moves print head to exact X, Y, and Z coordinates for consistent captures
- 🖼️ **Multiple Formats**: Saves images as JPG with comprehensive JSON metadata
- 🛡️ **Safety Features**: Boundary checking and position validation
- 🧪 **Debug Mode**: Fake camera support for testing without hardware
- ⚙️ **Highly Configurable**: Extensive settings for grid spacing, layer intervals, and capture behavior

## Installation

### Manual Installation

1. Clone or download this repository to your local machine
2. Navigate to the plugin directory:
   ```bash
   cd OctoPrint-LayerCapture
   ```

3. Install the plugin using pip in your OctoPrint environment:
   ```bash
   pip install .
   ```

4. Restart OctoPrint

### Plugin Manager Installation (Future)

This plugin will be available through the OctoPrint Plugin Manager in future releases.

## Configuration

After installation, go to **Settings > Plugins > Layer Capture** to configure:

### Grid Configuration
- **Grid Center**: X/Y coordinates of the capture grid center
- **Grid Spacing**: Distance between capture points (default: 20mm)
- **Grid Size**: Number of capture positions (1x1, 3x3, or 5x5)
- **Z Offset**: Distance above print surface for capture positions (default: 5mm)
- **Bed Boundaries**: Maximum X/Y coordinates for safety validation

### Layer Capture Settings
- **Capture Frequency**: Every N layers (default: every 3rd layer)
- **Specific Z Heights**: Optional specific Z coordinates for capture
- **Minimum Layer Height**: Minimum layer height to trigger capture

### Camera Settings
- **Fake Camera Mode**: Enable for testing without real camera hardware
- **Capture Delay**: Time to wait after movement before capturing
- **Pre-Capture Delay**: Additional delay before taking snapshot for stabilization
- **Image Quality**: JPEG compression quality (1-100)
- **Create Thumbnails**: Generate small preview images for web viewing
- **Return to Origin**: Whether to return to original position after capture

### G-code and Movement Settings
- **Movement Speed**: Print head movement speed during captures (mm/min)
- **Pause/Resume Timeout**: Timeout for pause and resume operations
- **Movement Timeout**: Wait time after movement commands
- **Emergency Resume Attempts**: Number of attempts to resume print in emergency

## How It Works

### Layer Detection
The plugin monitors Z-change events during printing to detect layer changes. When a target layer is reached, the print is automatically paused.

### Grid Positioning
For each capture, the plugin calculates a grid of positions around the configured center point:
- **X Coordinate**: Horizontal position on the print bed
- **Y Coordinate**: Vertical position on the print bed  
- **Z Coordinate**: Current layer height + Z offset for optimal capture angle

### Capture Sequence
1. **Pause Print**: Safely pauses the print job with timeout validation
2. **Move to Position**: Moves print head to each grid position with safety checks
3. **Capture Image**: Takes photo at current X, Y, Z coordinates
4. **Save Metadata**: Records position data and print information
5. **Resume Print**: Safely resumes the print job with error recovery

### Metadata Output
Each capture session generates a JSON file containing:
**Note**: The Z coordinate in position data includes the configured Z offset (e.g., if layer height is 3.0mm and Z offset is 5.0mm, the capture Z position will be 8.0mm).
```json
{
  "layer": 15,
  "z_height": 3.0,
  "timestamp": "2024-01-15T10:30:00",
  "gcode_file": "print.gcode",
  "print_start_time": "2024-01-15T10:00:00",
  "images": [
    {
      "path": "layer_0015_pos_00_20240115_103000.jpg",
      "position": {
        "x": 125.0,
        "y": 105.0,
        "z": 8.0
      },
      "index": 0
    }
  ],
  "settings": {
    "grid_spacing": 20.0,
    "grid_center": {
      "x": 125.0,
      "y": 105.0
    },
    "grid_size": 3
  }
}
```

## Camera System

### Real Camera Support
The plugin integrates with OctoPrint's webcam system to capture high-quality images from real cameras:
- **USB Webcams**: Logitech C270, C920, C922, and other UVC cameras
- **Raspberry Pi Camera**: Official Pi Camera Module v1/v2/HQ
- **IP Cameras**: Any camera providing MJPEG streams
- **Automatic Detection**: Uses configured snapshot webcam from OctoPrint

### Fake Camera for Testing
Advanced fake camera generates realistic test images with:
- **Print bed simulation**: Grid pattern background
- **Layer visualization**: Progressive stack effect showing layer height
- **Metadata overlay**: Layer info, position, timestamps
- **Crosshair indicator**: Shows capture position
- **PIL/Pillow support**: Creates actual JPEG images when available

### Camera Setup
For detailed camera setup instructions, see: **[OCTOPRINT_CAMERA_SETUP.md](OCTOPRINT_CAMERA_SETUP.md)**

## File Structure

Captured files are organized by date in the configured capture folder:
```
uploads/layercapture/
├── 2024-01-15/
│   ├── layer_0003_pos_00_z_0_60_20240115_103000.jpg
│   ├── layer_0003_pos_01_z_0_60_20240115_103001.jpg
│   ├── layer_0003_pos_00_z_0_60_20240115_103000_thumb.jpg
│   ├── layer_0003_metadata_20240115_103000.json
│   └── ...
├── 2024-01-16/
│   └── ...
```

## Development

### Testing with Fake Camera
Enable "Fake Camera Mode" in settings to test the plugin without real camera hardware. This creates placeholder files for development and testing.

### Debug Mode
Enable debug logging in OctoPrint settings to see detailed capture sequence information.

## Troubleshooting

### Common Issues
- **Print doesn't pause**: Check that layer detection is working and target layers are configured
- **Position errors**: Verify bed boundaries and grid center coordinates
- **No images captured**: Check camera settings and fake camera mode for testing

### Logs
Check OctoPrint logs for detailed error messages and capture sequence information.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This plugin is licensed under the AGPLv3 license.

## Support

For support and questions:
- Create an issue on GitHub
- Check the OctoPrint community forum
- Review the plugin documentation

---

**Note**: This plugin is designed for 3D printing enthusiasts who want to monitor their prints at specific layers. Always ensure your printer is properly calibrated and safe to operate before using automated capture features.
