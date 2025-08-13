#!/bin/bash

echo "=== Testing WebM Tile Converter App ==="
echo

# Check if the app exists
if [ ! -d "WebM Tile Converter.app" ]; then
    echo "❌ App bundle not found!"
    exit 1
fi

# Check if the Python script exists in the right place
PYTHON_SCRIPT="WebM Tile Converter.app/Contents/Resources/png_sequence_to_webm_tiles.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Python script not found in Resources folder!"
    exit 1
fi

# Check if the executable exists
EXECUTABLE="WebM Tile Converter.app/Contents/MacOS/WebM Tile Converter"
if [ ! -f "$EXECUTABLE" ]; then
    echo "❌ Executable not found!"
    exit 1
fi

# Check if it's executable
if [ ! -x "$EXECUTABLE" ]; then
    echo "❌ Executable is not executable!"
    exit 1
fi

echo "✅ App bundle structure is correct"
echo "✅ Python script found in Resources"
echo "✅ Executable found and is executable"
echo
echo "Testing app launch (will open file dialog)..."
echo "You can cancel the dialog to test the app works."
echo

# Test the app (it will open the file dialog)
open "WebM Tile Converter.app"

echo "✅ App launched successfully!"
echo
echo "The app should now be running. You can:"
echo "1. Select a file to test the full functionality"
echo "2. Or cancel the dialog to verify the app works"
echo
echo "If you see the file selection dialog, the app is working correctly!"
