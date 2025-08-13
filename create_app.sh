#!/bin/bash

# WebM Tile Converter App Creator
# This script creates a standalone macOS app that can be shared

set -e

echo "=== WebM Tile Converter App Creator ==="
echo "Creating a standalone app that you can share with friends..."
echo

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only."
    exit 1
fi

# Create app bundle structure
APP_NAME="WebM Tile Converter"
APP_BUNDLE="${APP_NAME}.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "Creating app bundle structure..."
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

# Create Info.plist
cat > "${CONTENTS_DIR}/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>WebM Tile Converter</string>
    <key>CFBundleIdentifier</key>
    <string>com.webmtiles.converter</string>
    <key>CFBundleName</key>
    <string>WebM Tile Converter</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

# Create the main executable script
cat > "${MACOS_DIR}/WebM Tile Converter" << 'EOF'
#!/bin/bash

# WebM Tile Converter - Main App
# This is the main executable for the WebM Tile Converter app

# Get the directory where this app is located
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." &> /dev/null && pwd )"
RESOURCES_DIR="${APP_DIR}/Contents/Resources"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    osascript -e 'display alert "Error" message "Python 3 is not installed. Please install Python 3 from python.org"'
    exit 1
fi

# Check if required Python packages are installed
check_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

missing_packages=()

if ! check_package "PIL"; then
    missing_packages+=("pillow")
fi

if ! check_package "imageio"; then
    missing_packages+=("imageio[ffmpeg]")
fi

if ! check_package "numpy"; then
    missing_packages+=("numpy")
fi

if ! check_package "tkinter"; then
    osascript -e 'display alert "Error" message "Tkinter is not available. Please install Python with Tkinter support."'
    exit 1
fi

# Install missing packages if any
if [ ${#missing_packages[@]} -ne 0 ]; then
    echo "Installing missing packages: ${missing_packages[*]}"
    for package in "${missing_packages[@]}"; do
        python3 -m pip install "$package" --user
    done
fi

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    # Try to install FFmpeg using Homebrew
    if command -v brew &> /dev/null; then
        echo "Installing FFmpeg using Homebrew..."
        brew install ffmpeg
    else
        osascript -e 'display alert "Error" message "FFmpeg is not installed. Please install FFmpeg from ffmpeg.org or install Homebrew and run: brew install ffmpeg"'
        exit 1
    fi
fi

# Get the script directory (where the Python script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." &> /dev/null && pwd )"
PYTHON_SCRIPT="${RESOURCES_DIR}/png_sequence_to_webm_tiles.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    osascript -e 'display alert "Error" message "Could not find the main Python script. Please ensure the app bundle is complete."'
    exit 1
fi

# Run the Python script
cd "$RESOURCES_DIR"
python3 "$PYTHON_SCRIPT"

# Check if the script ran successfully
if [ $? -ne 0 ]; then
    osascript -e 'display alert "Error" message "The WebM Tile Converter encountered an error. Please check the terminal output for details."'
fi
EOF

# Make the executable script executable
chmod +x "${MACOS_DIR}/WebM Tile Converter"

# Copy the Python script to resources
cp png_sequence_to_webm_tiles.py "${RESOURCES_DIR}/"

# Create a simple icon (we'll use a text-based approach for now)
cat > "${RESOURCES_DIR}/icon.txt" << 'EOF'
WebM Tile Converter
===================

A powerful tool to convert animations and videos 
into custom-sized WebM tiles for Telegram emoji packs.

Features:
- Multiple input formats (PNG, SVG, WebP, GIF, MP4, etc.)
- Automatic FPS detection
- Custom tile sizing
- High quality WebM output with transparency

Double-click to run!
EOF

# Create a README for the app
cat > "${RESOURCES_DIR}/README.txt" << 'EOF'
WebM Tile Converter
===================

A standalone app to convert animations and videos into WebM tiles.

HOW TO USE:
1. Double-click this app to launch
2. Select your input file or folder
3. Choose frame duration (or use detected FPS)
4. Set tile dimensions
5. Wait for processing
6. Find output in Desktop/WEBM folder

SUPPORTED FORMATS:
- PNG sequences (numbered PNG files in a folder)
- SVG sequences (numbered SVG files in a folder)
- Animated WebP files
- GIF animations
- MP4, AVI, MOV, WebM videos
- Any format FFmpeg supports

REQUIREMENTS:
- macOS 10.14 or later
- Python 3 (will be installed automatically if needed)
- FFmpeg (will be installed automatically if Homebrew is available)

TROUBLESHOOTING:
- If the app won't start, right-click and select "Open"
- Make sure you have internet connection for package installation
- Check that input files are valid and accessible

Created with ❤️ for the animation community
EOF

# Create a simple installer script
cat > "install_webm_converter.sh" << 'EOF'
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
EOF

chmod +x "install_webm_converter.sh"

# Create a distribution package
echo "Creating distribution package..."
mkdir -p "WebM_Tile_Converter_Distribution"
cp -r "${APP_BUNDLE}" "WebM_Tile_Converter_Distribution/"
cp "install_webm_converter.sh" "WebM_Tile_Converter_Distribution/"
cp "README.md" "WebM_Tile_Converter_Distribution/" 2>/dev/null || echo "# WebM Tile Converter\n\nSee the app bundle for usage instructions." > "WebM_Tile_Converter_Distribution/README.md"

# Create a simple launcher
cat > "WebM_Tile_Converter_Distribution/Launch WebM Converter.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
open "WebM Tile Converter.app"
EOF

chmod +x "WebM_Tile_Converter_Distribution/Launch WebM Converter.command"

echo
echo "🎉 App creation complete!"
echo
echo "Created files:"
echo "- ${APP_BUNDLE} (main app bundle)"
echo "- install_webm_converter.sh (installer script)"
echo "- WebM_Tile_Converter_Distribution/ (distribution folder)"
echo
echo "To share with friends:"
echo "1. Copy the 'WebM_Tile_Converter_Distribution' folder"
echo "2. They can run 'install_webm_converter.sh' first (optional)"
echo "3. Then double-click 'Launch WebM Converter.command'"
echo "4. Or double-click the app bundle directly"
echo
echo "Note: Friends may need to right-click and 'Open' the first time"
echo "due to macOS security (not signed with Apple Developer ID)"
echo
echo "The app will automatically install required dependencies on first run."
