# Speech-to-Text for Arch Linux

A keyboard-triggered speech-to-text application that transcribes your voice and inserts the text at your cursor position.

## Features

- 🎤 **Offline speech recognition** using Vosk
- ⌨️ **Global hotkey** (Super+V) to toggle recording
- 📝 **Auto-insert** transcribed text at cursor position
- 🔔 **Desktop notifications** for status feedback
- 🖥️ **X11 and Wayland** support

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

## Usage

1. **Start the app:**
   ```bash
   ./run.sh
   ```

2. **Place your cursor** in any text field (terminal, editor, browser, etc.)

3. **Press `Super+V`** to start recording

4. **Speak** your text clearly

5. **Press `Super+V`** again to stop and insert the transcribed text

## Configuration

Edit `speech_to_text.py` to customize:

- **Hotkey**: Modify `Config.HOTKEY` (default: Super+V)
- **Audio settings**: Adjust `SAMPLE_RATE` and `CHUNK_SIZE`
- **Model**: Change `MODEL_PATH` to use a different Vosk model

### Using a Different Model

For better accuracy, download a larger model from [Vosk Models](https://alphacephei.com/vosk/models):

```bash
cd ~/.local/share/vosk-models
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
```

Then update `MODEL_PATH` in the config.

## Troubleshooting

### "Model not found" error
Run `./install.sh` to download the Vosk model.

### No audio input
- Check your microphone is connected and working
- Run `arecord -l` to list audio devices
- Check PulseAudio/PipeWire settings

### xdotool/ydotool not working
- **X11**: Install xdotool: `sudo pacman -S xdotool`
- **Wayland**: Install ydotool: `sudo pacman -S ydotool`
  - Wayland may require running ydotool daemon: `sudo ydotoold`

### Hotkey not detected
- The app requires access to input devices
- On Wayland, you may need to add your user to the `input` group:
  ```bash
  sudo usermod -aG input $USER
  # Then log out and back in
  ```

## Dependencies

- Python 3.8+
- vosk (speech recognition)
- pyaudio (audio input)
- pynput (keyboard hotkey)
- xdotool (X11) or ydotool (Wayland)
- libnotify (notifications)

## License

MIT License
