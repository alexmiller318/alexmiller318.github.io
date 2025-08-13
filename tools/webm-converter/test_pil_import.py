#!/usr/bin/env python3
"""
Test script to verify PIL import works correctly
"""

try:
    from PIL import Image
    print("✅ PIL import successful!")
    print(f"PIL version: {Image.__version__}")
    
    # Test basic PIL functionality
    img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
    print("✅ PIL basic functionality works!")
    
except ImportError as e:
    print(f"❌ PIL import failed: {e}")
    print("Make sure you're using Python 3 and Pillow is installed:")
    print("  python3 -m pip install Pillow")
except Exception as e:
    print(f"❌ PIL test failed: {e}")

# Test other required imports
try:
    import imageio.v3 as iio
    print("✅ imageio import successful!")
except ImportError as e:
    print(f"❌ imageio import failed: {e}")

try:
    import numpy as np
    print("✅ numpy import successful!")
except ImportError as e:
    print(f"❌ numpy import failed: {e}")

try:
    import cairosvg
    print("✅ cairosvg import successful!")
except ImportError as e:
    print(f"❌ cairosvg import failed: {e}")

print("\nAll tests completed!")
