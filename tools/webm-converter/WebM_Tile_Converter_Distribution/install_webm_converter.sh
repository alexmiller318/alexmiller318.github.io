#!/bin/bash

# WebM Tile Converter Installer
echo "Installing WebM Tile Converter..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
python3 -m pip install --user pillow "imageio[ffmpeg]" numpy cairosvg

# Install FFmpeg if not available
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew not found. Please install FFmpeg manually from ffmpeg.org"
        echo "Or install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
fi

echo "✅ Installation complete!"
echo "You can now run the WebM Tile Converter app."
