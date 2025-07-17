#!/usr/bin/env python3
"""
Test script for the LayerCapture OctoPrint plugin.
This script helps validate installation and basic functionality.
"""

import sys
import importlib.util
import json
import tempfile
import os
from datetime import datetime

def test_plugin_import():
    """Test if the plugin can be imported successfully."""
    print("Testing plugin import...")
    try:
        import octoprint_layercapture
        print("✓ Plugin import successful")
        return True
    except ImportError as e:
        print(f"✗ Plugin import failed: {e}")
        return False

def test_plugin_class():
    """Test if the plugin class can be instantiated."""
    print("Testing plugin class instantiation...")
    try:
        from octoprint_layercapture import LayerCapturePlugin
        plugin = LayerCapturePlugin()
        print("✓ Plugin class instantiation successful")
        return True, plugin
    except Exception as e:
        print(f"✗ Plugin class instantiation failed: {e}")
        return False, None

def test_settings_defaults(plugin):
    """Test if settings defaults are properly configured."""
    print("Testing settings defaults...")
    try:
        defaults = plugin.get_settings_defaults()
        required_keys = [
            'grid_spacing', 'grid_center_x', 'grid_center_y', 'grid_size',
            'bed_width', 'bed_height', 'capture_every_n_layers',
            'min_layer_height', 'use_fake_camera', 'capture_delay'
        ]
        
        missing_keys = [key for key in required_keys if key not in defaults]
        if missing_keys:
            print(f"✗ Missing required settings keys: {missing_keys}")
            return False
        
        print("✓ Settings defaults are properly configured")
        print(f"  Grid spacing: {defaults['grid_spacing']}mm")
        print(f"  Grid center: ({defaults['grid_center_x']}, {defaults['grid_center_y']})")
        print(f"  Capture interval: every {defaults['capture_every_n_layers']} layers")
        return True
    except Exception as e:
        print(f"✗ Settings defaults test failed: {e}")
        return False

def test_grid_calculation(plugin):
    """Test grid position calculation."""
    print("Testing grid position calculation...")
    try:
        # Mock settings for testing
        class MockSettings:
            def __init__(self, defaults):
                self.defaults = defaults
            
            def get_float(self, key_path):
                key = key_path[0] if isinstance(key_path, list) else key_path
                return float(self.defaults.get(key, 0))
            
            def get_int(self, key_path):
                key = key_path[0] if isinstance(key_path, list) else key_path
                return int(self.defaults.get(key, 0))
        
        plugin._settings = MockSettings(plugin.get_settings_defaults())
        
        positions = plugin._calculate_grid_positions()
        
        if not positions:
            print("✗ Grid calculation returned no positions")
            return False
        
        print(f"✓ Grid calculation successful - {len(positions)} positions generated")
        for i, pos in enumerate(positions[:5]):  # Show first 5 positions
            print(f"  Position {i+1}: X={pos['x']}, Y={pos['y']}")
        if len(positions) > 5:
            print(f"  ... and {len(positions) - 5} more positions")
        
        return True
    except Exception as e:
        print(f"✗ Grid calculation test failed: {e}")
        return False

def test_safety_check(plugin):
    """Test boundary safety checking."""
    print("Testing safety boundary checking...")
    try:
        # Mock settings
        class MockSettings:
            def get_float(self, key_path):
                key = key_path[0] if isinstance(key_path, list) else key_path
                defaults = {
                    'bed_width': 200,
                    'bed_height': 200,
                    'boundary_margin': 10
                }
                return float(defaults.get(key, 0))
        
        plugin._settings = MockSettings()
        
        # Test safe position
        safe_result = plugin._is_position_safe(100, 100)
        if not safe_result:
            print("✗ Safe position incorrectly marked as unsafe")
            return False
        
        # Test unsafe position (too close to edge)
        unsafe_result = plugin._is_position_safe(5, 5)
        if unsafe_result:
            print("✗ Unsafe position incorrectly marked as safe")
            return False
        
        print("✓ Safety boundary checking working correctly")
        return True
    except Exception as e:
        print(f"✗ Safety check test failed: {e}")
        return False

def test_fake_image_creation(plugin):
    """Test fake image creation for debugging."""
    print("Testing fake image creation...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "test_image.jpg")
            capture_data = {
                'layer': 10,
                'z_height': 2.0,
                'timestamp': datetime.now().timestamp()
            }
            
            plugin._create_fake_image(image_path, capture_data, 0)
            
            if not os.path.exists(image_path):
                print("✗ Fake image file was not created")
                return False
            
            with open(image_path, 'r') as f:
                content = f.read()
            
            if "FAKE IMAGE" not in content or "Layer: 10" not in content:
                print("✗ Fake image content is incorrect")
                return False
            
            print("✓ Fake image creation working correctly")
            return True
    except Exception as e:
        print(f"✗ Fake image creation test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and return overall success status."""
    print("=" * 50)
    print("LayerCapture Plugin Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Import
    if test_plugin_import():
        tests_passed += 1
    print()
    
    # Test 2: Class instantiation
    success, plugin = test_plugin_class()
    if success:
        tests_passed += 1
    print()
    
    if plugin is None:
        print("Cannot continue with remaining tests - plugin instantiation failed")
        print(f"Final Result: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    # Test 3: Settings defaults
    if test_settings_defaults(plugin):
        tests_passed += 1
    print()
    
    # Test 4: Grid calculation
    if test_grid_calculation(plugin):
        tests_passed += 1
    print()
    
    # Test 5: Safety checking
    if test_safety_check(plugin):
        tests_passed += 1
    print()
    
    # Test 6: Fake image creation
    if test_fake_image_creation(plugin):
        tests_passed += 1
    print()
    
    print("=" * 50)
    print(f"Final Result: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Plugin appears to be working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 