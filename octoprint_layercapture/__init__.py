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
            
            # G-code and movement configuration
            "movement_speed": 3000,  # Movement speed in mm/min
            "pause_timeout": 10,  # Timeout for pause/resume operations in seconds
            "movement_timeout": 5,  # Timeout for movement completion in seconds
            "emergency_resume_attempts": 3,  # Number of emergency resume attempts
            
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
    
    ##~~ SimpleApiPlugin mixin
    
    def get_api_commands(self):
        return {
            "status": [],
            "test": ["test"]
        }
    
    def on_api_command(self, command, data):
        if command == "status":
            return {
                "current_layer": self._current_layer,
                "target_layers": sorted(self._target_layers),
                "capture_in_progress": self._capture_in_progress,
                "print_start_time": self._print_start_time,
                "current_gcode_file": self._current_gcode_file
            }
        elif command == "test":
            return {"result": "LayerCapture plugin is working!"}
    
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
        
        # Log print information
        file_info = payload.get("file", {})
        self._logger.info(f"Print file: {file_info.get('name', 'Unknown')}")
        self._logger.info(f"Target layers for capture: {sorted(self._target_layers)}")
        
        # Send notification to frontend
        self._plugin_manager.send_plugin_message("layercapture", {
            "type": "print_started",
            "target_layers": sorted(self._target_layers),
            "file_name": file_info.get("name", "Unknown")
        })
    
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
            
        # Calculate current layer with better precision
        min_layer_height = self._settings.get_float(["min_layer_height"])
        current_layer = self._calculate_layer_number(new_z, min_layer_height)
        
        if current_layer != self._current_layer and current_layer > 0:
            self._current_layer = current_layer
            self._logger.debug(f"Layer changed to {current_layer} at Z={new_z:.3f}")
            
            # Check if we should capture at this layer
            if current_layer in self._target_layers:
                self._logger.info(f"Triggering capture for layer {current_layer} at Z={new_z:.3f}")
                self._trigger_layer_capture(current_layer, new_z)
            else:
                self._logger.debug(f"Layer {current_layer} not in target layers: {sorted(self._target_layers)}")
    
    def _calculate_layer_number(self, z_height, min_layer_height):
        """Calculate layer number from Z height with better precision"""
        if z_height <= 0:
            return 0
            
        # Use rounding to handle floating point precision issues
        layer = round(z_height / min_layer_height)
        
        # Ensure we don't have negative layers
        return max(0, layer)
    
    def _calculate_target_layers(self):
        """Calculate which layers to capture based on settings"""
        self._target_layers.clear()
        
        capture_every_n = self._settings.get_int(["capture_every_n_layers"])
        min_layer_height = self._settings.get_float(["min_layer_height"])
        max_z_height = self._settings.get_float(["max_z_height"])
        
        if capture_every_n > 0:
            # Calculate target layers based on max Z height
            max_layers = int(max_z_height / min_layer_height)
            for layer in range(capture_every_n, max_layers + 1, capture_every_n):
                self._target_layers.add(layer)
            
            self._logger.info(f"Calculated {len(self._target_layers)} target layers every {capture_every_n} layers")
        
        # Add specific Z heights if configured
        z_heights = self._settings.get(["capture_z_heights"])
        for z_height in z_heights:
            if z_height > 0:
                layer = self._calculate_layer_number(z_height, min_layer_height)
                self._target_layers.add(layer)
                self._logger.debug(f"Added specific Z height {z_height}mm as layer {layer}")
        
        self._logger.info(f"Total target layers: {sorted(self._target_layers)}")
    
    def _trigger_layer_capture(self, layer, z_height):
        """Trigger the capture sequence for a specific layer"""
        if self._capture_in_progress:
            self._logger.warning(f"Capture already in progress, skipping layer {layer}")
            return
        
        # Validate printer state before capture
        if not self._validate_printer_state():
            self._logger.warning(f"Printer not in safe state for capture, skipping layer {layer}")
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
    
    def _validate_printer_state(self):
        """Validate that printer is in a safe state for capture"""
        try:
            # Check if printer is printing
            if not self._printer.is_printing():
                self._logger.warning("Printer is not currently printing")
                return False
            
            # Check if printer is connected
            if not self._printer.is_operational():
                self._logger.warning("Printer is not operational")
                return False
            
            # Check if printer is not paused or cancelled
            if self._printer.is_paused() or self._printer.is_cancelling():
                self._logger.warning("Printer is paused or cancelling")
                return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error validating printer state: {e}")
            return False
    
    def _execute_capture_sequence(self, capture_data):
        """Execute the complete capture sequence"""
        with self._capture_mutex:
            self._capture_in_progress = True
            original_position = None
            print_resumed = False
            
            try:
                self._logger.info(f"Starting capture sequence for layer {capture_data['layer']}")
                
                # Send notification to frontend
                self._plugin_manager.send_plugin_message("layercapture", {
                    "type": "capture_started",
                    "layer": capture_data["layer"],
                    "z_height": capture_data["z_height"]
                })
                
                # 1. Pause the print safely
                if not self._pause_print_safely():
                    raise Exception("Failed to pause print safely")
                
                # 2. Get and store current position
                original_position = self._get_current_position()
                if not original_position:
                    raise Exception("Could not determine current position")
                
                self._logger.debug(f"Original position: {original_position}")
                
                # 3. Calculate grid positions
                grid_positions = self._calculate_grid_positions(capture_data["z_height"])
                if not grid_positions:
                    raise Exception("No valid grid positions calculated")
                
                self._logger.info(f"Calculated {len(grid_positions)} capture positions")
                
                # 4. Move to each position and capture
                captured_images = []
                for i, position in enumerate(grid_positions):
                    self._logger.debug(f"Processing position {i+1}/{len(grid_positions)}: {position}")
                    
                    # Move to position with safety checks
                    if not self._move_to_position_safely(position):
                        self._logger.warning(f"Failed to move to position {i+1}, skipping capture")
                        continue
                    
                    # Wait for movement to complete and stabilize
                    time.sleep(self._settings.get_int(["capture_delay"]))
                    
                    # Capture image
                    image_path = self._capture_image(capture_data, i)
                    if image_path:
                        captured_images.append({
                            "path": image_path,
                            "position": position,
                            "index": i
                        })
                        self._logger.debug(f"Successfully captured image {i+1}: {image_path}")
                
                # 5. Return to original position safely
                if self._settings.get_boolean(["return_to_origin"]) and original_position:
                    self._logger.debug("Returning to original position")
                    if not self._move_to_position_safely(original_position):
                        self._logger.warning("Failed to return to original position")
                    else:
                        time.sleep(1)  # Stabilize after return movement
                
                # 6. Save metadata
                if self._settings.get_boolean(["save_metadata"]):
                    self._save_capture_metadata(capture_data, captured_images)
                
                # 7. Resume print safely
                if self._resume_print_safely():
                    print_resumed = True
                    self._logger.info(f"Capture sequence completed for layer {capture_data['layer']}, captured {len(captured_images)} images")
                else:
                    raise Exception("Failed to resume print")
                
                # Send success notification
                self._plugin_manager.send_plugin_message("layercapture", {
                    "type": "capture_completed",
                    "layer": capture_data["layer"],
                    "images_count": len(captured_images)
                })
                
            except Exception as e:
                self._logger.error(f"Error during capture sequence: {e}")
                
                # Send error notification
                self._plugin_manager.send_plugin_message("layercapture", {
                    "type": "capture_failed",
                    "layer": capture_data["layer"],
                    "error": str(e)
                })
                
                # Emergency recovery: try to resume print
                if not print_resumed:
                    self._emergency_resume_print()
                    
            finally:
                self._capture_in_progress = False
    
    def _get_current_position(self):
        """Get current printer position"""
        try:
            # Get current position from printer state
            current_pos = self._printer.get_current_position()
            if current_pos:
                return {
                    "x": current_pos.get("x", 0),
                    "y": current_pos.get("y", 0), 
                    "z": current_pos.get("z", 0)
                }
        except Exception as e:
            self._logger.warning(f"Could not get current position: {e}")
        
        # Fallback to safe position
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
        speed = self._settings.get_int(["movement_speed"])
        
        if z is not None:
            gcode_command = f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} F{speed}"
        else:
            gcode_command = f"G1 X{x:.3f} Y{y:.3f} F{speed}"
        
        self._logger.debug(f"Sending movement command: {gcode_command}")
        self._printer.commands([gcode_command])
    
    def _pause_print_safely(self):
        """Pause print with safety checks and timeout"""
        try:
            self._logger.debug("Attempting to pause print")
            
            # Check if already paused
            if self._printer.is_paused():
                self._logger.debug("Print already paused")
                return True
            
            # Pause the print
            self._printer.pause_print()
            
            # Wait for pause to take effect with timeout
            timeout = self._settings.get_int(["pause_timeout"])
            start_time = time.time()
            while not self._printer.is_paused() and (time.time() - start_time) < timeout:
                time.sleep(0.5)
            
            if self._printer.is_paused():
                self._logger.debug("Print paused successfully")
                time.sleep(1)  # Additional stabilization time
                return True
            else:
                self._logger.error("Failed to pause print within timeout")
                return False
                
        except Exception as e:
            self._logger.error(f"Error pausing print: {e}")
            return False
    
    def _resume_print_safely(self):
        """Resume print with safety checks and timeout"""
        try:
            self._logger.debug("Attempting to resume print")
            
            # Check if already printing
            if self._printer.is_printing() and not self._printer.is_paused():
                self._logger.debug("Print already running")
                return True
            
            # Resume the print
            self._printer.resume_print()
            
            # Wait for resume to take effect with timeout
            timeout = self._settings.get_int(["pause_timeout"])
            start_time = time.time()
            while self._printer.is_paused() and (time.time() - start_time) < timeout:
                time.sleep(0.5)
            
            if self._printer.is_printing() and not self._printer.is_paused():
                self._logger.debug("Print resumed successfully")
                return True
            else:
                self._logger.error("Failed to resume print within timeout")
                return False
                
        except Exception as e:
            self._logger.error(f"Error resuming print: {e}")
            return False
    
    def _move_to_position_safely(self, position):
        """Move to position with safety checks and validation"""
        try:
            x, y = position["x"], position["y"]
            z = position.get("z")
            
            # Validate position is safe
            if not self._is_position_safe(x, y):
                self._logger.warning(f"Position {position} is not safe, skipping movement")
                return False
            
            # Check Z height limit
            max_z = self._settings.get_float(["max_z_height"])
            if z and z > max_z:
                self._logger.warning(f"Z position {z} exceeds maximum {max_z}, skipping movement")
                return False
            
            # Get current position for comparison
            current_pos = self._get_current_position()
            
            # Calculate movement distance for safety
            if current_pos:
                distance = ((x - current_pos["x"])**2 + (y - current_pos["y"])**2)**0.5
                if distance > 200:  # Large movement safety check
                    self._logger.warning(f"Large movement detected ({distance:.1f}mm), confirming safety")
            
            # Send movement command
            if z is not None:
                gcode_command = f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} F3000"
            else:
                gcode_command = f"G1 X{x:.3f} Y{y:.3f} F3000"
            
            self._logger.debug(f"Sending movement command: {gcode_command}")
            self._printer.commands([gcode_command])
            
            # Wait for movement to complete
            movement_timeout = self._settings.get_int(["movement_timeout"])
            time.sleep(movement_timeout)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error moving to position {position}: {e}")
            return False
    
    def _emergency_resume_print(self):
        """Emergency print resume in case of errors"""
        try:
            self._logger.warning("Attempting emergency print resume")
            
            # Force resume multiple times if needed
            max_attempts = self._settings.get_int(["emergency_resume_attempts"])
            for attempt in range(max_attempts):
                try:
                    self._printer.resume_print()
                    time.sleep(1)
                    
                    if self._printer.is_printing() and not self._printer.is_paused():
                        self._logger.info("Emergency resume successful")
                        return True
                        
                except Exception as e:
                    self._logger.error(f"Emergency resume attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
            
            self._logger.error("All emergency resume attempts failed")
            return False
            
        except Exception as e:
            self._logger.error(f"Critical error in emergency resume: {e}")
            return False
    
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