#!/bin/bash
#
# Speech-to-Text App - Installation Script for Arch Linux
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HOME/.local/share/vosk-models"
MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"

echo "=========================================="
echo "Speech-to-Text App Installer (Arch Linux)"
echo "=========================================="
echo

# Detect display server
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    DISPLAY_SERVER="wayland"
    TYPING_TOOL="ydotool"
else
    DISPLAY_SERVER="x11"
    TYPING_TOOL="xdotool"
fi

echo "Detected display server: $DISPLAY_SERVER"
echo "Will use: $TYPING_TOOL for text input"
echo

# Step 1: Install system dependencies
echo "[1/4] Installing system dependencies..."
echo "This may require sudo password."

PACKAGES="base-devel python python-pip python-pyaudio libnotify $TYPING_TOOL"

if ! pacman -Q portaudio &>/dev/null; then
    PACKAGES="$PACKAGES portaudio"
fi

sudo pacman -S --needed --noconfirm $PACKAGES

echo "✓ System dependencies installed"
echo

# Step 2: Create virtual environment
echo "[2/4] Setting up Python virtual environment..."

cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate and install Python packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "✓ Python packages installed"
echo

# Step 3: Download Vosk model
echo "[3/4] Downloading Vosk speech recognition model..."

mkdir -p "$MODEL_DIR"

if [ -d "$MODEL_DIR/$MODEL_NAME" ]; then
    echo "✓ Model already downloaded"
else
    echo "Downloading model (~40MB)..."
    cd "$MODEL_DIR"
    
    if command -v wget &>/dev/null; then
        wget -q --show-progress "$MODEL_URL" -O model.zip
    else
        curl -L --progress-bar "$MODEL_URL" -o model.zip
    fi
    
    echo "Extracting model..."
    unzip -q model.zip
    rm model.zip
    
    echo "✓ Model downloaded to $MODEL_DIR/$MODEL_NAME"
fi

echo

# Step 4: Create launcher script
echo "[4/4] Creating launcher script..."

cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python speech_to_text.py
EOF

chmod +x "$SCRIPT_DIR/run.sh"

echo "✓ Launcher script created"
echo

# Done!
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo
echo "To run the application:"
echo "  cd $SCRIPT_DIR"
echo "  ./run.sh"
echo
echo "Or run directly:"
echo "  $SCRIPT_DIR/run.sh"
echo
echo "Usage:"
echo "  1. Press Super+V to start recording"
echo "  2. Speak your text"
echo "  3. Press Super+V again to stop and insert text"
echo
echo "Note: Make sure your cursor is in a text field before"
echo "      pressing the hotkey to insert the text there."
echo "=========================================="
