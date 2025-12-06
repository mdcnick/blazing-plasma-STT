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

# Step 4: Create launcher scripts
echo "[4/6] Creating launcher scripts..."

cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python speech_to_text.py "$@"
EOF

chmod +x "$SCRIPT_DIR/run.sh"

# Create daemon launcher (no terminal output)
cat > "$SCRIPT_DIR/stt-daemon.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
exec python speech_to_text.py --daemon
EOF

chmod +x "$SCRIPT_DIR/stt-daemon.sh"

echo "✓ Launcher scripts created"
echo

# Step 5: Setup user config
echo "[5/6] Setting up user configuration..."

CONFIG_DIR="$HOME/.config/speech-to-text"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cp "$SCRIPT_DIR/config.json" "$CONFIG_DIR/config.json"
    echo "✓ Config copied to $CONFIG_DIR/config.json"
else
    echo "  Config already exists (kept existing)"
fi

echo

# Step 6: Setup autostart and CLI access
echo "[6/6] Setting up system integration..."

# Autostart directory
mkdir -p "$HOME/.config/autostart"

# Create desktop file with correct path
cat > "$HOME/.config/autostart/speech-to-text.desktop" << EOF
[Desktop Entry]
Name=Speech to Text
Comment=Voice-activated speech-to-text with global hotkey
Exec=$SCRIPT_DIR/stt-daemon.sh
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;Accessibility;
Keywords=speech;voice;transcription;dictation;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

echo "✓ Autostart entry created"

# Create CLI symlink
mkdir -p "$HOME/.local/bin"
ln -sf "$SCRIPT_DIR/run.sh" "$HOME/.local/bin/speech-to-text"
echo "✓ CLI command 'speech-to-text' created"

echo

# Done!
echo "==========================================="
echo "Installation complete!"
echo "==========================================="
echo
echo "The app will start automatically on login."
echo
echo "You can also start it manually:"
echo "  speech-to-text          # With terminal output"
echo "  speech-to-text --daemon # Silent (no terminal)"
echo
echo "Configure the hotkey by editing:"
echo "  $CONFIG_DIR/config.json"
echo
echo "Current hotkey: Ctrl+Shift+Space"
echo
echo "To uninstall, run:"
echo "  $SCRIPT_DIR/uninstall.sh"
echo "==========================================="

