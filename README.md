# Speech-to-Text for Arch Linux

A keyboard-triggered speech-to-text application that transcribes your voice and inserts the text at your cursor position.

## Features

- 🎤 **Offline speech recognition** using Vosk
- ⌨️ **Configurable global hotkey** (default: Ctrl+Shift+Space)
- 📝 **Auto-insert** transcribed text at cursor position
- 🔔 **Desktop notifications** for status feedback
- 🖥️ **X11 and Wayland** support
- 🚀 **Auto-start on login** (no terminal needed)

## Installation

```bash
# Clone/download this directory, then:
cd /path/to/this/directory
chmod +x install.sh
./install.sh
```

The installer will:
1. Install system packages (python, xdotool/ydotool, etc.)
2. Create a Python virtual environment
3. Install Python dependencies
4. Download the Vosk speech model (~40MB)
5. Set up autostart (runs on login)
6. Create CLI command `speech-to-text`

## Usage

The app starts automatically on login. Just:

1. **Place your cursor** in any text field
2. **Press `Ctrl+Shift+Space`** to start recording
3. **Speak** your text clearly  
4. **Press `Ctrl+Shift+Space`** again to stop and insert

### Manual Start

```bash
speech-to-text          # With terminal output
speech-to-text --daemon # Silent (no terminal)
```

## Configuration

Edit `~/.config/speech-to-text/config.json` to customize:

```json
{
    "hotkey": {
        "modifiers": ["ctrl", "shift"],
        "key": "space"
    },
    "streaming_mode": true,
    "notifications": true
}
```

### Hotkey Options

**Modifiers**: `ctrl`, `alt`, `shift`, `super` (Meta/Win key)  
**Keys**: Any letter, `space`, `enter`, `tab`, `esc`, or function keys (`f1`-`f12`)

Examples:
- `{"modifiers": ["super", "shift"], "key": "s"}` → Super+Shift+S
- `{"modifiers": ["ctrl", "alt"], "key": "v"}` → Ctrl+Alt+V

Restart the app after changing the hotkey.

### Using a Different Model

For better accuracy, download a larger model from [Vosk Models](https://alphacephei.com/vosk/models):

```bash
cd ~/.local/share/vosk-models
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
```

Then set `"model_path"` in config.json.

## Uninstall

```bash
./uninstall.sh
```

## Troubleshooting

### Hotkey not detected
- The app requires access to input devices
- On Wayland, add your user to the `input` group:
  ```bash
  sudo usermod -aG input $USER
  # Then log out and back in
  ```

### No audio input
- Check microphone: `arecord -l`
- Check PulseAudio/PipeWire settings

## Dependencies

- Python 3.8+
- vosk, pyaudio, pynput
- xclip (X11) or wl-clipboard (Wayland)
- libnotify

## License

MIT License

