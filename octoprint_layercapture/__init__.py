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
        self._current_calibration_file = "calibTODO.json" # Initialize calibration file path
        self._capture_mutex = threading.Lock()
        
    ##~~ SettingsPlugin mixin
    
    def get_settings_defaults(self):
        return {
            # 3D Grid configuration - separate settings for each axis
            "grid_center_x": 125,  # Center position X in mm
            "grid_center_y": 105,  # Center position Y in mm  
            "grid_center_z": 0,    # Center Z offset relative to current layer in mm
            "grid_size_x": 3,      # Number of positions in X direction
            "grid_size_y": 3,      # Number of positions in Y direction
            "grid_size_z": 3,      # Number of positions in Z direction

            "grid_spacing_x": 20,  # Spacing between X positions in mm
            "grid_spacing_y": 20,  # Spacing between Y positions in mm
            "grid_spacing_z": 5,   # Spacing between Z positions in mm
            "z_offset_base": 5,    # Base Z offset above print surface in mm
            
            # Legacy settings for backward compatibility
            "grid_spacing": 20,    # Deprecated: use grid_spacing_x/y instead
            "grid_size": 3,        # Deprecated: use grid_size_x/y instead
            "z_offset": 5,         # Deprecated: use z_offset_base instead
            
            # Printer bed dimensions
            "bed_max_x": 250,      # Printer bed width (X) in mm
            "bed_max_y": 210,      # Printer bed height (Y) in mm
            "bed_width": 250,      # Alias for bed_max_x (backward compatibility)
            "bed_height": 210,     # Alias for bed_max_y (backward compatibility)
            
            # Layer capture configuration
            "capture_every_n_layers": 3,  # Capture every 3rd layer
            "capture_z_heights": [],  # Specific Z heights to capture at
            "min_layer_height": 0.2,  # Minimum layer height in mm
            
            # Camera configuration
            "use_fake_camera": True,  # For debugging without real camera
            "capture_delay": 2,  # Delay between movements and capture in seconds
            "pre_capture_delay": 0.5,  # Additional delay before taking snapshot
            "create_thumbnails": True,  # Create thumbnails for web viewing
            "image_quality": 95,  # JPEG quality (1-100)
            "return_to_origin": True,  # Return to original position after capture
            
            # G-code and movement configuration
            "movement_speed": 3000,  # Movement speed in mm/min
            "pause_timeout": 10,  # Timeout for pause/resume operations in seconds
            "movement_timeout": 5,  # Timeout for movement completion in seconds
            "emergency_resume_attempts": 3,  # Number of emergency resume attempts
            
            # File management
            "capture_folder": "layercapture",  # Folder within uploads for captures
            "save_metadata": True,  # Save JSON metadata files
            
            # Calibration file path (JSON string)
            "calibration_file_path": "",  # Path to calibration JSON file for this print
            
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
        self._current_calibration_file = self._settings.get(["calibration_file_path"])  # Store calibration file path
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
            "file_name": file_info.get("name", "Unknown"),
            "calibration_file_path": self._current_calibration_file
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
            "calibration_file_path": self._current_calibration_file  # Add calibration file path to capture data
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
        """Calculate 3D grid positions for image capture"""
        # Get 3D grid configuration with fallback to legacy settings
        center_x = self._settings.get_float(["grid_center_x"])
        center_y = self._settings.get_float(["grid_center_y"])
        center_z = self._settings.get_float(["grid_center_z"])
        
        # Use new axis-specific settings with fallback to legacy
        grid_size_x = self._settings.get_int(["grid_size_x"]) or self._settings.get_int(["grid_size"])
        grid_size_y = self._settings.get_int(["grid_size_y"]) or self._settings.get_int(["grid_size"])
        grid_size_z = self._settings.get_int(["grid_size_z"]) or 1
        
        spacing_x = self._settings.get_float(["grid_spacing_x"]) or self._settings.get_float(["grid_spacing"])
        spacing_y = self._settings.get_float(["grid_spacing_y"]) or self._settings.get_float(["grid_spacing"])
        spacing_z = self._settings.get_float(["grid_spacing_z"]) or 5.0
        
        z_offset_base = self._settings.get_float(["z_offset_base"]) or self._settings.get_float(["z_offset"])
        
        positions = []
        
        # Calculate 3D grid positions around center
        half_size_x = grid_size_x // 2
        half_size_y = grid_size_y // 2
        half_size_z = grid_size_z // 2
        
        for x_offset in range(-half_size_x, half_size_x + 1):
            for y_offset in range(-half_size_y, half_size_y + 1):
                for z_offset in range(-half_size_z, half_size_z + 1):
                    x = center_x + (x_offset * spacing_x)
                    y = center_y + (y_offset * spacing_y)
                    
                    # Calculate Z position
                    if z_height is not None:
                        # Z position = current layer height + base offset + grid Z offset
                        z = z_height + z_offset_base + center_z + (z_offset * spacing_z)
                    else:
                        # If no layer height provided, use base offset only
                        z = z_offset_base + center_z + (z_offset * spacing_z)
                    
                    # Validate position is within bed boundaries
                    if self._is_position_safe(x, y, z):
                        position = {
                            "x": x, 
                            "y": y, 
                            "z": z,
                            "grid_coords": {
                                "x_offset": x_offset,
                                "y_offset": y_offset,
                                "z_offset": z_offset
                            }
                        }
                        positions.append(position)
        
        self._logger.debug(f"Calculated {len(positions)} 3D grid positions ({grid_size_x}x{grid_size_y}x{grid_size_z})")
        return positions
    
    def _is_position_safe(self, x, y, z=None):
        """Check if position is within safe boundaries"""
        # Get bed dimensions with fallback to legacy settings
        bed_width = self._settings.get_float(["bed_width"]) or self._settings.get_float(["bed_max_x"])
        bed_height = self._settings.get_float(["bed_height"]) or self._settings.get_float(["bed_max_y"])
        margin = self._settings.get_float(["boundary_margin"])
        max_z = self._settings.get_float(["max_z_height"])
        
        # Check X and Y boundaries
        x_safe = margin <= x <= bed_width - margin
        y_safe = margin <= y <= bed_height - margin
        
        # Check Z boundary if provided
        z_safe = True
        if z is not None:
            z_safe = 0 <= z <= max_z
        
        return x_safe and y_safe and z_safe
    
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
            # Create filename with better formatting
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            layer_str = f"{capture_data['layer']:04d}"
            pos_str = f"{position_index:02d}"
            z_height_str = f"{capture_data['z_height']:.2f}".replace('.', '_')
            
            filename = f"layer_{layer_str}_pos_{pos_str}_z_{z_height_str}_{timestamp}.jpg"
            
            # Create capture directory with date-based organization
            capture_folder = self._settings.get(["capture_folder"])
            date_folder = datetime.now().strftime("%Y-%m-%d")
            capture_dir = os.path.join(
                self._file_manager.get_folder_path("uploads"), 
                capture_folder, 
                date_folder
            )
            os.makedirs(capture_dir, exist_ok=True)
            
            image_path = os.path.join(capture_dir, filename)
            
            # Add pre-capture delay if configured
            pre_capture_delay = self._settings.get_float(["pre_capture_delay"])
            if pre_capture_delay > 0:
                self._logger.debug(f"Pre-capture delay: {pre_capture_delay}s")
                time.sleep(pre_capture_delay)
            
            # Capture based on mode
            capture_start_time = time.time()
            if self._settings.get_boolean(["use_fake_camera"]):
                self._logger.debug(f"Using fake camera for position {position_index + 1}")
                self._create_fake_image(image_path, capture_data, position_index)
            else:
                self._logger.debug(f"Using real camera for position {position_index + 1}")
                self._capture_real_image(image_path)
            
            capture_duration = time.time() - capture_start_time
            
            # Validate image was created
            if os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                self._logger.debug(f"Image captured successfully: {filename} ({file_size} bytes, {capture_duration:.2f}s)")
                
                # Optional: Create thumbnail for web viewing
                if self._settings.get_boolean(["create_thumbnails"]):
                    self._create_thumbnail(image_path)
                
                return image_path
            else:
                raise Exception("Image file was not created")
            
        except Exception as e:
            self._logger.error(f"Failed to capture image at position {position_index}: {e}")
            return None
    
    def _create_thumbnail(self, image_path):
        """Create a thumbnail for web viewing"""
        try:
            from PIL import Image
            
            thumbnail_path = image_path.replace('.jpg', '_thumb.jpg')
            thumbnail_size = (160, 120)
            
            with Image.open(image_path) as image:
                image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                image.save(thumbnail_path, 'JPEG', quality=75)
                
            self._logger.debug(f"Created thumbnail: {thumbnail_path}")
            
        except ImportError:
            self._logger.warning("PIL not available for thumbnail creation")
        except Exception as e:
            self._logger.warning(f"Failed to create thumbnail: {e}")
    
    def _create_fake_image(self, image_path, capture_data, position_index):
        """Create a fake image file for testing"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a realistic fake image using PIL
            width, height = 640, 480
            image = Image.new('RGB', (width, height), color='lightblue')
            draw = ImageDraw.Draw(image)
            
            # Try to use a basic font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 20)
                small_font = ImageFont.truetype("arial.ttf", 14)
            except:
                try:
                    font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
                except:
                    font = None
                    small_font = None
            
            # Draw background pattern to simulate print bed
            for i in range(0, width, 20):
                draw.line([(i, 0), (i, height)], fill='lightgray', width=1)
            for i in range(0, height, 20):
                draw.line([(0, i), (width, i)], fill='lightgray', width=1)
            
            # Draw a simple "print object" in the center
            object_x, object_y = width // 2, height // 2
            object_size = min(width, height) // 4
            draw.ellipse([
                object_x - object_size//2, object_y - object_size//2,
                object_x + object_size//2, object_y + object_size//2
            ], fill='orange', outline='darkorange', width=2)
            
            # Add layer visualization (stack effect)
            layer_height = max(1, min(10, capture_data['layer'] // 5))
            for i in range(layer_height):
                offset = i * 2
                draw.ellipse([
                    object_x - object_size//2 + offset, object_y - object_size//2 + offset,
                    object_x + object_size//2 + offset, object_y + object_size//2 + offset
                ], outline='red', width=1)
            
            # Add text information
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            info_lines = [
                f"FAKE CAMERA - LayerCapture Plugin",
                f"Layer: {capture_data['layer']}",
                f"Position: {position_index + 1}",
                f"Z-Height: {capture_data['z_height']:.2f}mm",
                f"Time: {timestamp}",
                f"File: {os.path.basename(capture_data.get('gcode_file', 'unknown.gcode'))}"
            ]
            
            y_offset = 10
            for line in info_lines:
                if font:
                    draw.text((10, y_offset), line, fill='black', font=small_font)
                    y_offset += 18
                else:
                    draw.text((10, y_offset), line, fill='black')
                    y_offset += 15
            
            # Add crosshair to show capture position
            cross_size = 20
            center_x, center_y = width // 2, height // 2
            draw.line([
                (center_x - cross_size, center_y),
                (center_x + cross_size, center_y)
            ], fill='red', width=2)
            draw.line([
                (center_x, center_y - cross_size),
                (center_x, center_y + cross_size)
            ], fill='red', width=2)
            
            # Save as JPEG with configured quality
            quality = self._settings.get_int(["image_quality"])
            image.save(image_path, 'JPEG', quality=quality)
            self._logger.debug(f"Created fake image: {image_path}")
            
        except ImportError:
            # Fallback if PIL is not available - create a simple text file
            self._logger.warning("PIL not available, creating simple text file instead of fake image")
            fake_data = f"""FAKE IMAGE DATA - LayerCapture Plugin
Layer: {capture_data['layer']}
Position: {position_index + 1}
Z-Height: {capture_data['z_height']:.2f}mm
Time: {datetime.now()}
File: {os.path.basename(capture_data.get('gcode_file', 'unknown.gcode'))}

Note: Install PIL/Pillow for realistic fake images: pip install Pillow"""
            
            with open(image_path.replace('.jpg', '.txt'), 'w') as f:
                f.write(fake_data)
                
        except Exception as e:
            self._logger.error(f"Failed to create fake image: {e}")
            # Ultra-simple fallback
            fake_data = f"FAKE IMAGE - Layer: {capture_data['layer']}, Position: {position_index}, Time: {datetime.now()}"
            with open(image_path.replace('.jpg', '.txt'), 'w') as f:
                f.write(fake_data)
    
    def _capture_real_image(self, image_path):
        """Capture real image using OctoPrint's webcam system"""
        try:
            from octoprint.webcams import get_snapshot_webcam, WebcamNotAbleToTakeSnapshotException
            
            # Get the configured snapshot webcam
            webcam = get_snapshot_webcam()
            if not webcam:
                raise Exception("No webcam configured for snapshots")
            
            if not webcam.config.canSnapshot:
                raise WebcamNotAbleToTakeSnapshotException(webcam.config.name)
            
            self._logger.debug(f"Capturing image from webcam '{webcam.config.name}' using provider '{webcam.providerIdentifier}'")
            
            # Take snapshot using the webcam provider plugin
            snapshot_data = webcam.providerPlugin.take_webcam_snapshot(webcam.config.name)
            
            # Save the snapshot data to file
            with open(image_path, 'wb') as f:
                for chunk in snapshot_data:
                    if chunk:
                        f.write(chunk)
                        f.flush()
            
            self._logger.debug(f"Successfully captured real image: {image_path}")
            return True
            
        except WebcamNotAbleToTakeSnapshotException as e:
            self._logger.error(f"Webcam '{e.webcam_name}' cannot take snapshots")
            raise Exception(f"Webcam '{e.webcam_name}' is not configured for snapshots")
            
        except Exception as e:
            self._logger.error(f"Failed to capture real image: {e}")
            raise Exception(f"Camera capture failed: {e}")
    
    def _save_capture_metadata(self, capture_data, captured_images):
        """Save JSON metadata for the capture session"""
        # Get camera information
        camera_info = self._get_camera_info()
        
        metadata = {
            "layer": capture_data["layer"],
            "z_height": capture_data["z_height"],
            "timestamp": capture_data["timestamp"],
            "timestamp_iso": datetime.fromtimestamp(capture_data["timestamp"]).isoformat(),
            "gcode_file": capture_data["gcode_file"],
            "calibration_file_path": capture_data.get("calibration_file_path"),  # Include calibration file path
            "print_start_time": self._print_start_time,
            "print_start_time_iso": datetime.fromtimestamp(self._print_start_time).isoformat() if self._print_start_time else None,
            "images": captured_images,
            "camera": camera_info,
            "settings": {
                "grid_spacing": self._settings.get_float(["grid_spacing"]),
                "grid_center": {
                    "x": self._settings.get_float(["grid_center_x"]),
                    "y": self._settings.get_float(["grid_center_y"])
                },
                "grid_size": self._settings.get_int(["grid_size"]),
                "z_offset": self._settings.get_float(["z_offset"]),
                "image_quality": self._settings.get_int(["image_quality"]),
                "movement_speed": self._settings.get_int(["movement_speed"]),
                "capture_delay": self._settings.get_int(["capture_delay"]),
                "pre_capture_delay": self._settings.get_float(["pre_capture_delay"]),
                "calibration_file_path": self._settings.get(["calibration_file_path"])  # Also include in settings
            },
            "plugin_version": __plugin_version__
        }
        
        # Save metadata file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_filename = f"layer_{capture_data['layer']:04d}_metadata_{timestamp}.json"
        capture_folder = self._settings.get(["capture_folder"])
        date_folder = datetime.now().strftime("%Y-%m-%d")
        capture_dir = os.path.join(
            self._file_manager.get_folder_path("uploads"), 
            capture_folder, 
            date_folder
        )
        metadata_path = os.path.join(capture_dir, metadata_filename)
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            self._logger.debug(f"Metadata saved: {metadata_path}")
        except Exception as e:
            self._logger.error(f"Failed to save metadata: {e}")
    
    def _get_camera_info(self):
        """Get information about the camera being used"""
        camera_info = {
            "type": "fake" if self._settings.get_boolean(["use_fake_camera"]) else "real",
            "timestamp": datetime.now().isoformat()
        }
        
        if not self._settings.get_boolean(["use_fake_camera"]):
            try:
                from octoprint.webcams import get_snapshot_webcam
                
                webcam = get_snapshot_webcam()
                if webcam:
                    camera_info.update({
                        "name": webcam.config.name,
                        "display_name": webcam.config.displayName,
                        "provider": webcam.providerIdentifier,
                        "can_snapshot": webcam.config.canSnapshot,
                        "snapshot_display": webcam.config.snapshotDisplay,
                        "flip_h": webcam.config.flipH,
                        "flip_v": webcam.config.flipV,
                        "rotate_90": webcam.config.rotate90,
                        "extras": webcam.config.extras
                    })
                else:
                    camera_info["error"] = "No webcam configured"
                    
            except Exception as e:
                camera_info["error"] = f"Failed to get webcam info: {e}"
        else:
            camera_info.update({
                "name": "fake_camera",
                "display_name": "Fake Camera (Testing Mode)",
                "provider": "layercapture_plugin",
                "can_snapshot": True,
                "note": "This is a fake camera for testing purposes"
            })
        
        return camera_info
    
    def _cleanup_capture_session(self):
        """Clean up after print session ends"""
        self._capture_queue.clear()
        self._target_layers.clear()
        self._current_layer = 0
        self._print_start_time = None
        self._current_gcode_file = None
        self._current_calibration_file = "" # Clear calibration file path on session end
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