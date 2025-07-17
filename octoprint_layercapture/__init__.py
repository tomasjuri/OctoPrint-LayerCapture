"""
OctoPrint LayerCapture Plugin

Captures images at specified print layers with configurable grid coordinates.
"""

import os
import json
import time
import threading
from datetime import datetime

import octoprint.plugin
from octoprint.events import Events
from octoprint.util import RepeatedTimer


class LayerCapturePlugin(
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.WebcamProviderPlugin,
):
    
    def __init__(self):
        self._capture_queue = []
        self._capture_in_progress = False
        self._current_layer = 0
        self._target_layers = set()
        self._print_start_time = None
        self._current_gcode_file = None
        self._capture_mutex = threading.Lock()
        
    ##~~ SettingsPlugin mixin
    
    def get_settings_defaults(self):
        return {
            # Grid configuration
            "grid_spacing": 20,  # 2cm spacing in mm
            "grid_center_x": 125,  # Center position X in mm
            "grid_center_y": 105,  # Center position Y in mm  
            "grid_size": 3,  # 3x3 grid (center + 8 around)
            "z_offset": 5,  # Z offset above print surface in mm
            "bed_max_x": 250,  # Printer bed width (X) in mm
            "bed_max_y": 210,  # Printer bed height (Y) in mm
            
            # Layer capture configuration
            "capture_every_n_layers": 3,  # Capture every 3rd layer
            "capture_z_heights": [],  # Specific Z heights to capture at
            "min_layer_height": 0.2,  # Minimum layer height in mm
            
            # Camera configuration
            "use_fake_camera": True,  # For debugging without real camera
            "capture_delay": 2,  # Delay between movements and capture in seconds
            "return_to_origin": True,  # Return to original position after capture
            
            # File management
            "capture_folder": "layercapture",  # Folder within uploads for captures
            "save_metadata": True,  # Save JSON metadata files
            
            # Safety settings
            "max_z_height": 300,  # Maximum Z height limit in mm
            "boundary_margin": 10,  # Safety margin from bed edges in mm
        }
    
    ##~~ TemplatePlugin mixin
    
    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": "Layer Capture",
                "template": "layercapture_settings.jinja2",
                "custom_bindings": True,
            }
        ]
    
    ##~~ AssetPlugin mixin
    
    def get_assets(self):
        return {
            "js": ["js/layercapture.js"],
            "css": ["css/layercapture.css"],
        }
    
    ##~~ EventHandlerPlugin mixin
    
    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self._on_print_started(payload)
        elif event == Events.PRINT_DONE:
            self._on_print_done(payload)
        elif event == Events.PRINT_FAILED:
            self._on_print_failed(payload)
        elif event == Events.PRINT_CANCELLED:
            self._on_print_cancelled(payload)
        elif event == Events.Z_CHANGE:
            self._on_z_change(payload)
    
    def _on_print_started(self, payload):
        """Initialize capture session when print starts"""
        self._logger.info("Print started, initializing layer capture")
        self._print_start_time = time.time()
        self._current_layer = 0
        self._current_gcode_file = payload.get("file", {}).get("path")
        self._capture_queue.clear()
        
        # Calculate target layers based on settings
        self._calculate_target_layers()
        
        self._logger.info(f"Target layers for capture: {sorted(self._target_layers)}")
    
    def _on_print_done(self, payload):
        """Clean up when print completes"""
        self._logger.info("Print completed, layer capture session ended")
        self._cleanup_capture_session()
    
    def _on_print_failed(self, payload):
        """Clean up when print fails"""
        self._logger.info("Print failed, layer capture session ended")
        self._cleanup_capture_session()
    
    def _on_print_cancelled(self, payload):
        """Clean up when print is cancelled"""
        self._logger.info("Print cancelled, layer capture session ended")
        self._cleanup_capture_session()
    
    def _on_z_change(self, payload):
        """Handle layer changes and trigger captures"""
        old_z = payload.get("old")
        new_z = payload.get("new")
        
        if new_z is None:
            return
            
        # Calculate current layer
        min_layer_height = self._settings.get_float(["min_layer_height"])
        current_layer = int(new_z / min_layer_height)
        
        if current_layer != self._current_layer:
            self._current_layer = current_layer
            self._logger.debug(f"Layer changed to {current_layer} at Z={new_z}")
            
            # Check if we should capture at this layer
            if current_layer in self._target_layers:
                self._logger.info(f"Triggering capture for layer {current_layer} at Z={new_z}")
                self._trigger_layer_capture(current_layer, new_z)
    
    def _calculate_target_layers(self):
        """Calculate which layers to capture based on settings"""
        self._target_layers.clear()
        
        capture_every_n = self._settings.get_int(["capture_every_n_layers"])
        if capture_every_n > 0:
            # For now, calculate first 20 target layers - in real implementation
            # this would be based on actual print height/layer count
            for layer in range(capture_every_n, 200, capture_every_n):
                self._target_layers.add(layer)
        
        # Add specific Z heights if configured
        z_heights = self._settings.get(["capture_z_heights"])
        min_layer_height = self._settings.get_float(["min_layer_height"])
        for z_height in z_heights:
            layer = int(z_height / min_layer_height)
            self._target_layers.add(layer)
    
    def _trigger_layer_capture(self, layer, z_height):
        """Trigger the capture sequence for a specific layer"""
        if self._capture_in_progress:
            self._logger.warning(f"Capture already in progress, skipping layer {layer}")
            return
        
        # Add to capture queue
        capture_data = {
            "layer": layer,
            "z_height": z_height,
            "timestamp": time.time(),
            "gcode_file": self._current_gcode_file,
        }
        
        self._capture_queue.append(capture_data)
        
        # Start capture sequence in background thread
        capture_thread = threading.Thread(target=self._execute_capture_sequence, args=(capture_data,))
        capture_thread.daemon = True
        capture_thread.start()
    
    def _execute_capture_sequence(self, capture_data):
        """Execute the complete capture sequence"""
        with self._capture_mutex:
            self._capture_in_progress = True
            
            try:
                self._logger.info(f"Starting capture sequence for layer {capture_data['layer']}")
                
                # 1. Pause the print
                self._printer.pause_print()
                time.sleep(1)  # Wait for pause to take effect
                
                # 2. Get current position (to return to later)
                current_pos = self._get_current_position()
                
                # 3. Calculate grid positions
                grid_positions = self._calculate_grid_positions(capture_data["z_height"])
                
                # 4. Move to each position and capture
                captured_images = []
                for i, position in enumerate(grid_positions):
                    self._logger.debug(f"Moving to position {i+1}/{len(grid_positions)}: {position}")
                    
                    # Move to position
                    self._move_to_position(position)
                    
                    # Wait for movement to complete
                    time.sleep(self._settings.get_int(["capture_delay"]))
                    
                    # Capture image
                    image_path = self._capture_image(capture_data, i)
                    if image_path:
                        captured_images.append({
                            "path": image_path,
                            "position": position,
                            "index": i
                        })
                
                # 5. Return to original position
                if self._settings.get_boolean(["return_to_origin"]) and current_pos:
                    self._move_to_position(current_pos)
                    time.sleep(1)
                
                # 6. Save metadata
                if self._settings.get_boolean(["save_metadata"]):
                    self._save_capture_metadata(capture_data, captured_images)
                
                # 7. Resume print
                self._printer.resume_print()
                
                self._logger.info(f"Capture sequence completed for layer {capture_data['layer']}, captured {len(captured_images)} images")
                
            except Exception as e:
                self._logger.error(f"Error during capture sequence: {e}")
                # Try to resume print even if capture failed
                try:
                    self._printer.resume_print()
                except:
                    pass
                    
            finally:
                self._capture_in_progress = False
    
    def _get_current_position(self):
        """Get current printer position - placeholder for now"""
        # In real implementation, this would query the printer for current position
        return {"x": 100, "y": 100, "z": 10}
    
    def _calculate_grid_positions(self, z_height=None):
        """Calculate grid positions for image capture"""
        center_x = self._settings.get_float(["grid_center_x"])
        center_y = self._settings.get_float(["grid_center_y"])
        spacing = self._settings.get_float(["grid_spacing"])
        grid_size = self._settings.get_int(["grid_size"])
        z_offset = self._settings.get_float(["z_offset"])
        
        positions = []
        
        # Calculate grid positions around center
        half_size = grid_size // 2
        for x_offset in range(-half_size, half_size + 1):
            for y_offset in range(-half_size, half_size + 1):
                x = center_x + (x_offset * spacing)
                y = center_y + (y_offset * spacing)
                
                # Validate position is within bed boundaries
                if self._is_position_safe(x, y):
                    position = {"x": x, "y": y}
                    if z_height is not None:
                        # Add Z offset to the current layer height
                        position["z"] = z_height + z_offset
                    positions.append(position)
        
        return positions
    
    def _is_position_safe(self, x, y):
        """Check if position is within safe boundaries"""
        bed_width = self._settings.get_float(["bed_width"])
        bed_height = self._settings.get_float(["bed_height"])
        margin = self._settings.get_float(["boundary_margin"])
        
        return (margin <= x <= bed_width - margin and 
                margin <= y <= bed_height - margin)
    
    def _move_to_position(self, position):
        """Move printer head to specified position"""
        x, y = position["x"], position["y"]
        z = position.get("z")  # Z coordinate is optional
        
        if z is not None:
            gcode_command = f"G1 X{x} Y{y} Z{z} F3000"  # Move at 3000 mm/min
        else:
            gcode_command = f"G1 X{x} Y{y} F3000"  # Move at 3000 mm/min
        
        self._logger.debug(f"Sending movement command: {gcode_command}")
        self._printer.commands([gcode_command])
    
    def _capture_image(self, capture_data, position_index):
        """Capture image at current position"""
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"layer_{capture_data['layer']:04d}_pos_{position_index:02d}_{timestamp}.jpg"
            
            # Create capture directory
            capture_folder = self._settings.get(["capture_folder"])
            capture_dir = os.path.join(self._file_manager.get_folder_path("uploads"), capture_folder)
            os.makedirs(capture_dir, exist_ok=True)
            
            image_path = os.path.join(capture_dir, filename)
            
            if self._settings.get_boolean(["use_fake_camera"]):
                # Create fake image for testing
                self._create_fake_image(image_path, capture_data, position_index)
            else:
                # Use real camera capture
                self._capture_real_image(image_path)
            
            self._logger.debug(f"Image captured: {image_path}")
            return image_path
            
        except Exception as e:
            self._logger.error(f"Failed to capture image: {e}")
            return None
    
    def _create_fake_image(self, image_path, capture_data, position_index):
        """Create a fake image file for testing"""
        # Create a simple text file as placeholder for now
        # In real implementation, this could generate a test image
        fake_data = f"FAKE IMAGE - Layer: {capture_data['layer']}, Position: {position_index}, Time: {datetime.now()}"
        with open(image_path, 'w') as f:
            f.write(fake_data)
    
    def _capture_real_image(self, image_path):
        """Capture real image using webcam"""
        # This would use OctoPrint's webcam system to capture actual images
        # For now, placeholder implementation
        raise NotImplementedError("Real camera capture not implemented yet")
    
    def _save_capture_metadata(self, capture_data, captured_images):
        """Save JSON metadata for the capture session"""
        metadata = {
            "layer": capture_data["layer"],
            "z_height": capture_data["z_height"],
            "timestamp": capture_data["timestamp"],
            "gcode_file": capture_data["gcode_file"],
            "print_start_time": self._print_start_time,
            "images": captured_images,
            "settings": {
                "grid_spacing": self._settings.get_float(["grid_spacing"]),
                "grid_center": {
                    "x": self._settings.get_float(["grid_center_x"]),
                    "y": self._settings.get_float(["grid_center_y"])
                },
                "grid_size": self._settings.get_int(["grid_size"])
            }
        }
        
        # Save metadata file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_filename = f"layer_{capture_data['layer']:04d}_metadata_{timestamp}.json"
        capture_folder = self._settings.get(["capture_folder"])
        capture_dir = os.path.join(self._file_manager.get_folder_path("uploads"), capture_folder)
        metadata_path = os.path.join(capture_dir, metadata_filename)
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            self._logger.debug(f"Metadata saved: {metadata_path}")
        except Exception as e:
            self._logger.error(f"Failed to save metadata: {e}")
    
    def _cleanup_capture_session(self):
        """Clean up after print session ends"""
        self._capture_queue.clear()
        self._target_layers.clear()
        self._current_layer = 0
        self._print_start_time = None
        self._current_gcode_file = None
        self._capture_in_progress = False


# Plugin metadata
__plugin_name__ = "Layer Capture"
__plugin_author__ = "Tomas Jurica"
__plugin_description__ = "Automatically captures images at specified print layers with configurable grid positions"
__plugin_version__ = "0.1.0"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = LayerCapturePlugin()

# Plugin hooks
__plugin_hooks__ = {
    "octoprint.events.register_custom_events": lambda: ["layer_capture_started", "layer_capture_completed", "layer_capture_failed"]
} 