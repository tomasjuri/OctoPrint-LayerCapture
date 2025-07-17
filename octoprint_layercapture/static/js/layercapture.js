$(function() {
    function LayerCaptureViewModel(parameters) {
        var self = this;
        
        self.settings = parameters[0];
        self.printerState = parameters[1];
        
        // Observable for tracking capture status
        self.captureInProgress = ko.observable(false);
        self.currentLayer = ko.observable(0);
        self.targetLayers = ko.observableArray([]);
        self.printStartTime = ko.observable(null);
        self.currentGcodeFile = ko.observable("");
        
        // Update status periodically
        self.updateStatus = function() {
            $.ajax({
                url: API_BASEURL + "plugin/layercapture",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "status"
                }),
                contentType: "application/json; charset=UTF-8",
                success: function(data) {
                    self.currentLayer(data.current_layer || 0);
                    self.targetLayers(data.target_layers || []);
                    self.captureInProgress(data.capture_in_progress || false);
                    self.printStartTime(data.print_start_time);
                    self.currentGcodeFile(data.current_gcode_file || "");
                },
                error: function() {
                    // Silently fail for status updates
                }
            });
        };
        
        // 3D Grid preview functionality
        self.showGridPreview = function() {
            // Calculate 3D grid positions based on current settings
            var centerX = parseFloat(self.settings.settings.plugins.layercapture.grid_center_x());
            var centerY = parseFloat(self.settings.settings.plugins.layercapture.grid_center_y());
            var centerZ = parseFloat(self.settings.settings.plugins.layercapture.grid_center_z());
            
            // Use new settings with fallback to legacy
            var gridSizeX = parseInt(self.settings.settings.plugins.layercapture.grid_size_x()) || parseInt(self.settings.settings.plugins.layercapture.grid_size());
            var gridSizeY = parseInt(self.settings.settings.plugins.layercapture.grid_size_y()) || parseInt(self.settings.settings.plugins.layercapture.grid_size());
            var gridSizeZ = parseInt(self.settings.settings.plugins.layercapture.grid_size_z()) || 1;
            
            var spacingX = parseFloat(self.settings.settings.plugins.layercapture.grid_spacing_x()) || parseFloat(self.settings.settings.plugins.layercapture.grid_spacing());
            var spacingY = parseFloat(self.settings.settings.plugins.layercapture.grid_spacing_y()) || parseFloat(self.settings.settings.plugins.layercapture.grid_spacing());
            var spacingZ = parseFloat(self.settings.settings.plugins.layercapture.grid_spacing_z()) || 5.0;
            
            var zOffsetBase = parseFloat(self.settings.settings.plugins.layercapture.z_offset_base()) || parseFloat(self.settings.settings.plugins.layercapture.z_offset());
            var bedWidth = parseFloat(self.settings.settings.plugins.layercapture.bed_width()) || parseFloat(self.settings.settings.plugins.layercapture.bed_max_x());
            var bedHeight = parseFloat(self.settings.settings.plugins.layercapture.bed_height()) || parseFloat(self.settings.settings.plugins.layercapture.bed_max_y());
            var margin = parseFloat(self.settings.settings.plugins.layercapture.boundary_margin());
            var maxZ = parseFloat(self.settings.settings.plugins.layercapture.max_z_height());
            
            var positions = [];
            var halfSizeX = Math.floor(gridSizeX / 2);
            var halfSizeY = Math.floor(gridSizeY / 2);
            var halfSizeZ = Math.floor(gridSizeZ / 2);
            
            for (var x = -halfSizeX; x <= halfSizeX; x++) {
                for (var y = -halfSizeY; y <= halfSizeY; y++) {
                    for (var z = -halfSizeZ; z <= halfSizeZ; z++) {
                        var posX = centerX + (x * spacingX);
                        var posY = centerY + (y * spacingY);
                        // Example layer height of 2.0mm
                        var posZ = 2.0 + zOffsetBase + centerZ + (z * spacingZ);
                        
                        // Check if position is within safe boundaries
                        var xSafe = posX >= margin && posX <= bedWidth - margin;
                        var ySafe = posY >= margin && posY <= bedHeight - margin;
                        var zSafe = posZ >= 0 && posZ <= maxZ;
                        var isSafe = xSafe && ySafe && zSafe;
                        
                        positions.push({
                            x: posX,
                            y: posY,
                            z: posZ,
                            gridCoords: {x: x, y: y, z: z},
                            safe: isSafe
                        });
                    }
                }
            }
            
            // Create 3D preview dialog
            var previewHtml = '<div class="modal-header">' +
                '<h3>3D Grid Preview</h3>' +
                '</div>' +
                '<div class="modal-body layercapture-grid-preview">' +
                '<p><strong>3D Grid Configuration:</strong></p>' +
                '<ul>' +
                '<li>Grid Center: (' + centerX + ', ' + centerY + ', ' + centerZ + ')</li>' +
                '<li>Grid Dimensions: ' + gridSizeX + ' × ' + gridSizeY + ' × ' + gridSizeZ + '</li>' +
                '<li>Grid Spacing: ' + spacingX + 'mm × ' + spacingY + 'mm × ' + spacingZ + 'mm</li>' +
                '<li>Base Z Offset: ' + zOffsetBase + 'mm</li>' +
                '</ul>' +
                '<p><em>Example positions at layer height 2.0mm:</em></p>' +
                '<table class="table table-striped table-condensed layercapture-preview-table">' +
                '<thead><tr><th>#</th><th>Grid (X,Y,Z)</th><th>Position X</th><th>Position Y</th><th>Position Z</th><th>Status</th></tr></thead>' +
                '<tbody>';
            
            for (var i = 0; i < positions.length; i++) {
                var pos = positions[i];
                var status = pos.safe ? '<span class="layercapture-position-safe">✓ Safe</span>' : '<span class="layercapture-position-unsafe">✗ Out of bounds</span>';
                var gridCoordStr = '(' + pos.gridCoords.x + ',' + pos.gridCoords.y + ',' + pos.gridCoords.z + ')';
                
                previewHtml += '<tr>' +
                    '<td>' + (i + 1) + '</td>' +
                    '<td>' + gridCoordStr + '</td>' +
                    '<td>' + pos.x.toFixed(1) + '</td>' +
                    '<td>' + pos.y.toFixed(1) + '</td>' +
                    '<td>' + pos.z.toFixed(1) + '</td>' +
                    '<td>' + status + '</td>' +
                    '</tr>';
            }
            
            var safePositions = positions.filter(function(p) { return p.safe; }).length;
            var totalImages = safePositions;
            
            previewHtml += '</tbody></table>' +
                '<div class="layercapture-summary">' +
                '<p><strong>Summary:</strong></p>' +
                '<ul>' +
                '<li>Total positions: ' + positions.length + '</li>' +
                '<li>Safe positions: ' + safePositions + '</li>' +
                '<li>Images per layer: ' + totalImages + '</li>' +
                '<li>Estimated capture time: ~' + Math.ceil(totalImages * 3) + ' seconds per layer</li>' +
                '</ul>' +
                '</div>' +
                '</div>' +
                '<div class="modal-footer">' +
                '<button class="btn" data-dismiss="modal">Close</button>' +
                '</div>';
            
            // Show modal with larger size for 3D data
            var dialog = $('<div class="modal hide fade" style="width: 700px; margin-left: -350px;">' + previewHtml + '</div>');
            dialog.modal('show');
            dialog.on('hidden', function() {
                dialog.remove();
            });
        };
        
        // Listen for plugin messages
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "layercapture") {
                return;
            }
            
            if (data.type === "capture_started") {
                self.captureInProgress(true);
                new PNotify({
                    title: "Layer Capture",
                    text: "Started capturing layer " + data.layer,
                    type: "info"
                });
            } else if (data.type === "capture_completed") {
                self.captureInProgress(false);
                new PNotify({
                    title: "Layer Capture",
                    text: "Completed capturing layer " + data.layer + " (" + data.images_count + " images)",
                    type: "success"
                });
            } else if (data.type === "capture_failed") {
                self.captureInProgress(false);
                new PNotify({
                    title: "Layer Capture",
                    text: "Failed to capture layer " + data.layer + ": " + data.error,
                    type: "error"
                });
            }
        };
        
        // Settings validation
        self.onSettingsShown = function() {
            // Add validation for grid positions when settings are shown
            // Start status updates when settings are shown
            self.updateStatus();
            self.statusInterval = setInterval(self.updateStatus, 2000); // Update every 2 seconds
        };
        
        self.onSettingsHidden = function() {
            // Stop status updates when settings are hidden
            if (self.statusInterval) {
                clearInterval(self.statusInterval);
                self.statusInterval = null;
            }
        };
        
        self.onSettingsBeforeSave = function() {
            // Validate settings before saving
            var centerX = parseFloat(self.settings.settings.plugins.layercapture.grid_center_x());
            var centerY = parseFloat(self.settings.settings.plugins.layercapture.grid_center_y());
            var bedWidth = parseFloat(self.settings.settings.plugins.layercapture.bed_width());
            var bedHeight = parseFloat(self.settings.settings.plugins.layercapture.bed_height());
            var margin = parseFloat(self.settings.settings.plugins.layercapture.boundary_margin());
            
            // Check if center position is within bed bounds
            if (centerX < margin || centerX > bedWidth - margin ||
                centerY < margin || centerY > bedHeight - margin) {
                
                new PNotify({
                    title: "Layer Capture Settings",
                    text: "Warning: Grid center position is outside safe bed boundaries!",
                    type: "warning"
                });
            }
            
            return true; // Allow save to continue
        };
    }
    
    // Register the view model
    OCTOPRINT_VIEWMODELS.push({
        construct: LayerCaptureViewModel,
        dependencies: ["settingsViewModel", "printerStateViewModel"],
        elements: ["#settings_plugin_layercapture"]
    });
}); 