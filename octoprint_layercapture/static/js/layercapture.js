$(function() {
    function LayerCaptureViewModel(parameters) {
        var self = this;
        
        self.settings = parameters[0];
        self.printerState = parameters[1];
        
        // Observable for tracking capture status
        self.captureInProgress = ko.observable(false);
        self.currentLayer = ko.observable(0);
        self.targetLayers = ko.observableArray([]);
        
        // Grid preview functionality
        self.showGridPreview = function() {
            // Calculate grid positions based on current settings
            var centerX = parseFloat(self.settings.settings.plugins.layercapture.grid_center_x());
            var centerY = parseFloat(self.settings.settings.plugins.layercapture.grid_center_y());
            var spacing = parseFloat(self.settings.settings.plugins.layercapture.grid_spacing());
            var gridSize = parseInt(self.settings.settings.plugins.layercapture.grid_size());
            var bedWidth = parseFloat(self.settings.settings.plugins.layercapture.bed_width());
            var bedHeight = parseFloat(self.settings.settings.plugins.layercapture.bed_height());
            var margin = parseFloat(self.settings.settings.plugins.layercapture.boundary_margin());
            
            var positions = [];
            var halfSize = Math.floor(gridSize / 2);
            
            for (var x = -halfSize; x <= halfSize; x++) {
                for (var y = -halfSize; y <= halfSize; y++) {
                    var posX = centerX + (x * spacing);
                    var posY = centerY + (y * spacing);
                    
                    // Check if position is within safe boundaries
                    var isSafe = (posX >= margin && posX <= bedWidth - margin && 
                                 posY >= margin && posY <= bedHeight - margin);
                    
                    positions.push({
                        x: posX,
                        y: posY,
                        safe: isSafe
                    });
                }
            }
            
            // Create preview dialog
            var previewHtml = '<div class="modal-header">' +
                '<h3>Grid Preview</h3>' +
                '</div>' +
                '<div class="modal-body">' +
                '<p>Grid positions for capture (center: ' + centerX + ', ' + centerY + '):</p>' +
                '<table class="table table-striped">' +
                '<thead><tr><th>Position</th><th>X (mm)</th><th>Y (mm)</th><th>Status</th></tr></thead>' +
                '<tbody>';
            
            for (var i = 0; i < positions.length; i++) {
                var pos = positions[i];
                var status = pos.safe ? '<span class="text-success">Safe</span>' : '<span class="text-error">Out of bounds</span>';
                previewHtml += '<tr>' +
                    '<td>' + (i + 1) + '</td>' +
                    '<td>' + pos.x.toFixed(1) + '</td>' +
                    '<td>' + pos.y.toFixed(1) + '</td>' +
                    '<td>' + status + '</td>' +
                    '</tr>';
            }
            
            previewHtml += '</tbody></table>' +
                '<p><strong>Total positions:</strong> ' + positions.length + '</p>' +
                '<p><strong>Safe positions:</strong> ' + positions.filter(function(p) { return p.safe; }).length + '</p>' +
                '</div>' +
                '<div class="modal-footer">' +
                '<button class="btn" data-dismiss="modal">Close</button>' +
                '</div>';
            
            // Show modal
            var dialog = $('<div class="modal hide fade" style="width: 500px; margin-left: -250px;">' + previewHtml + '</div>');
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