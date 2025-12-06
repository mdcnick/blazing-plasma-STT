#!/usr/bin/env python3
"""
Speech-to-Text Application for Arch Linux
Triggered by keyboard shortcut, inserts transcribed text at cursor position.
"""

import os
import sys
import json
import queue
import subprocess
import threading
import tempfile
import time
from pathlib import Path

try:
    import vosk
except ImportError:
    print("Error: vosk not installed. Run: pip install vosk")
    sys.exit(1)

try:
    import pyaudio
except ImportError:
    print("Error: pyaudio not installed. Run: pip install pyaudio")
    sys.exit(1)

try:
    from pynput import keyboard
except ImportError:
    print("Error: pynput not installed. Run: pip install pynput")
    sys.exit(1)


class Config:
    """Configuration for the speech-to-text app."""
    
    # Default hotkey: Ctrl+Alt+R
    HOTKEY = {keyboard.Key.ctrl, keyboard.Key.alt, keyboard.KeyCode.from_char('r')}
    
    # Vosk model path - will be downloaded to ~/.local/share/vosk-models
    MODEL_PATH = Path.home() / ".local" / "share" / "vosk-models" / "vosk-model-small-en-us-0.15"
    
    # Audio settings
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 4000  # Smaller chunks for more responsive streaming
    
    # Streaming mode settings
    STREAMING_MODE = True  # Set to False for batch transcription
    STREAMING_INTERVAL = 0.1  # Seconds between text updates
    
    # Display server detection
    @staticmethod
    def get_display_server():
        """Detect X11 or Wayland."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "x11")
        return session_type.lower()
    
    @staticmethod
    def get_typing_tool():
        """Get the appropriate tool for typing text."""
        if Config.get_display_server() == "wayland":
            return "ydotool"
        return "xdotool"


class Notifier:
    """Send desktop notifications."""
    
    @staticmethod
    def send(title: str, message: str, urgency: str = "normal"):
        """Send a desktop notification."""
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=False,
                capture_output=True
            )
        except FileNotFoundError:
            print(f"[{title}] {message}")


class TextTyper:
    """Type text at cursor position using clipboard paste."""
    
    def __init__(self):
        self.display_server = Config.get_display_server()
        self._check_tools()
        self._last_partial_len = 0  # Track length of last partial text typed
        self._kb = None
    
    def _get_keyboard(self):
        """Get keyboard controller lazily."""
        if self._kb is None:
            from pynput.keyboard import Controller
            self._kb = Controller()
        return self._kb
    
    def _check_tools(self):
        """Verify required tools are available."""
        if self.display_server == "wayland":
            # Check for wl-copy (from wl-clipboard)
            try:
                subprocess.run(["wl-copy", "--version"], capture_output=True, check=False)
            except FileNotFoundError:
                Notifier.send(
                    "Speech-to-Text Error",
                    "wl-clipboard not found. Install with: sudo pacman -S wl-clipboard",
                    "critical"
                )
                print("Error: wl-clipboard not installed. Run: sudo pacman -S wl-clipboard")
                sys.exit(1)
        else:
            # Check for xclip for X11
            try:
                subprocess.run(["xclip", "-version"], capture_output=True, check=False)
            except FileNotFoundError:
                Notifier.send(
                    "Speech-to-Text Error",
                    "xclip not found. Install with: sudo pacman -S xclip",
                    "critical"
                )
                print("Error: xclip not installed. Run: sudo pacman -S xclip")
                sys.exit(1)
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard."""
        if self.display_server == "wayland":
            proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode())
        else:
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode())
    
    def _send_backspaces(self, count: int):
        """Send backspace keys to delete characters."""
        if count <= 0:
            return
        from pynput.keyboard import Key
        kb = self._get_keyboard()
        for _ in range(count):
            kb.press(Key.backspace)
            kb.release(Key.backspace)
            time.sleep(0.005)  # Small delay between backspaces
    
    def _paste(self):
        """Simulate Ctrl+V paste."""
        from pynput.keyboard import Key
        kb = self._get_keyboard()
        kb.press(Key.ctrl)
        kb.press('v')
        kb.release('v')
        kb.release(Key.ctrl)
    
    def type_text(self, text: str):
        """Type text at the current cursor position using clipboard paste."""
        if not text.strip():
            return
        
        self._copy_to_clipboard(text)
        time.sleep(0.05)
        self._paste()
        self._last_partial_len = 0  # Reset for next session
    
    def type_incremental(self, new_text: str, is_final: bool = False):
        """
        Type text incrementally, updating previous partial text.
        
        For partial results: backspace previous text and type new text.
        For final results: commit the text (no more backspacing this segment).
        """
        # Delete the previous partial text
        if self._last_partial_len > 0:
            self._send_backspaces(self._last_partial_len)
        
        if new_text:
            # Copy and paste the new text
            self._copy_to_clipboard(new_text)
            time.sleep(0.03)
            self._paste()
        
        if is_final:
            # Add a space after final text and reset counter
            time.sleep(0.03)
            self._copy_to_clipboard(" ")
            time.sleep(0.02)
            self._paste()
            self._last_partial_len = 0
        else:
            # Track length for next backspace operation
            self._last_partial_len = len(new_text)
    
    def reset_incremental(self):
        """Reset incremental typing state."""
        self._last_partial_len = 0


class SpeechRecognizer:
    """Handle speech recognition using Vosk."""
    
    def __init__(self):
        self.model = None
        self.recognizer = None
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self._load_model()
    
    def _load_model(self):
        """Load the Vosk model."""
        model_path = Config.MODEL_PATH
        
        if not model_path.exists():
            Notifier.send(
                "Speech-to-Text",
                f"Model not found. Run install.sh to download it.",
                "critical"
            )
            print(f"Error: Vosk model not found at {model_path}")
            print("Please run the install.sh script to download the model.")
            sys.exit(1)
        
        vosk.SetLogLevel(-1)  # Suppress Vosk logs
        self.model = vosk.Model(str(model_path))
        self.recognizer = vosk.KaldiRecognizer(self.model, Config.SAMPLE_RATE)
    
    def _init_audio(self):
        """Initialize PyAudio."""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
    
    def start_recording(self):
        """Start recording audio from microphone."""
        self._init_audio()
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=Config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=Config.CHUNK_SIZE
            )
            self.is_recording = True
            Notifier.send("Speech-to-Text", "🎤 Recording... Press hotkey to stop")
            print("Recording started...")
        except Exception as e:
            Notifier.send("Speech-to-Text Error", f"Microphone error: {e}", "critical")
            self.is_recording = False
    
    def stop_recording_and_transcribe(self) -> str:
        """Stop recording and return transcribed text."""
        if not self.is_recording:
            return ""
        
        self.is_recording = False
        
        # Collect all audio data
        audio_data = []
        while self.stream and self.stream.is_active():
            try:
                data = self.stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                audio_data.append(data)
            except:
                break
        
        # Stop and close stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        Notifier.send("Speech-to-Text", "⏳ Transcribing...")
        print("Transcribing...")
        
        # Process audio through Vosk
        for data in audio_data:
            self.recognizer.AcceptWaveform(data)
        
        result = json.loads(self.recognizer.FinalResult())
        text = result.get("text", "")
        
        # Reset recognizer for next recording
        self.recognizer = vosk.KaldiRecognizer(self.model, Config.SAMPLE_RATE)
        
        return text
    
    def record_and_transcribe(self) -> str:
        """Record audio continuously and transcribe when stopped."""
        self._init_audio()
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=Config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=Config.CHUNK_SIZE
            )
        except Exception as e:
            Notifier.send("Speech-to-Text Error", f"Microphone error: {e}", "critical")
            return ""
        
        self.is_recording = True
        Notifier.send("Speech-to-Text", "🎤 Recording... Press hotkey to stop")
        print("Recording started... Press hotkey again to stop.")
        
        # Record while is_recording is True
        while self.is_recording:
            try:
                data = self.stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                self.recognizer.AcceptWaveform(data)
            except Exception as e:
                print(f"Audio error: {e}")
                break
        
        # Stop stream
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        
        # Get final result
        result = json.loads(self.recognizer.FinalResult())
        text = result.get("text", "")
        
        # Reset recognizer
        self.recognizer = vosk.KaldiRecognizer(self.model, Config.SAMPLE_RATE)
        
        return text
    
    def stream_and_transcribe(self, callback):
        """
        Stream audio and call callback with partial/final results.
        
        callback(text, is_final): Called with transcription results
            - text: The transcribed text
            - is_final: True if this is a complete phrase, False for partial
        """
        self._init_audio()
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=Config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=Config.CHUNK_SIZE
            )
        except Exception as e:
            Notifier.send("Speech-to-Text Error", f"Microphone error: {e}", "critical")
            return
        
        self.is_recording = True
        Notifier.send("Speech-to-Text", "🎤 Streaming... Speak now!")
        print("Streaming started... Press hotkey again to stop.")
        
        last_partial = ""
        
        while self.is_recording:
            try:
                data = self.stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    # Got a final result for a phrase
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        callback(text, is_final=True)
                        last_partial = ""
                else:
                    # Got a partial result
                    partial = json.loads(self.recognizer.PartialResult())
                    text = partial.get("partial", "")
                    if text and text != last_partial:
                        callback(text, is_final=False)
                        last_partial = text
                        
            except Exception as e:
                print(f"Streaming error: {e}")
                break
        
        # Get any remaining final result
        result = json.loads(self.recognizer.FinalResult())
        text = result.get("text", "")
        if text:
            callback(text, is_final=True)
        
        # Cleanup
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        
        # Reset recognizer
        self.recognizer = vosk.KaldiRecognizer(self.model, Config.SAMPLE_RATE)
    
    def cleanup(self):
        """Clean up audio resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()



class SpeechToTextApp:
    """Main application class."""
    
    def __init__(self):
        self.recognizer = SpeechRecognizer()
        self.typer = TextTyper()
        self.current_keys = set()
        self.recording_thread = None
        self.hotkey_pressed = False
    
    def _on_press(self, key):
        """Handle key press events."""
        self.current_keys.add(key)
        
        # Check if hotkey combination is pressed
        if Config.HOTKEY.issubset(self.current_keys):
            if not self.hotkey_pressed:
                self.hotkey_pressed = True
                self._toggle_recording()
    
    def _on_release(self, key):
        """Handle key release events."""
        try:
            self.current_keys.discard(key)
        except KeyError:
            pass
        
        # Reset hotkey state when any key in the combo is released
        if not Config.HOTKEY.issubset(self.current_keys):
            self.hotkey_pressed = False
    
    def _toggle_recording(self):
        """Toggle recording state."""
        if self.recognizer.is_recording:
            # Stop recording
            self.recognizer.is_recording = False
        else:
            # Start recording in a separate thread
            if Config.STREAMING_MODE:
                self.recording_thread = threading.Thread(target=self._stream_and_type)
            else:
                self.recording_thread = threading.Thread(target=self._record_and_type)
            self.recording_thread.start()
    
    def _on_transcription(self, text: str, is_final: bool):
        """Callback for streaming transcription results."""
        if is_final:
            print(f"  [FINAL] {text}")
            self.typer.type_incremental(text, is_final=True)
        else:
            print(f"  [partial] {text}")
            self.typer.type_incremental(text, is_final=False)
    
    def _stream_and_type(self):
        """Stream audio, transcribe, and type results in real-time."""
        self.typer.reset_incremental()
        self.recognizer.stream_and_transcribe(self._on_transcription)
        Notifier.send("Speech-to-Text", "✅ Streaming complete!")
        print("Streaming complete.")
    
    def _record_and_type(self):
        """Record audio, transcribe, and type the result (batch mode)."""
        text = self.recognizer.record_and_transcribe()
        
        if text:
            Notifier.send("Speech-to-Text", f"✅ Inserting: {text[:50]}...")
            print(f"Transcribed: {text}")
            self.typer.type_text(text)
        else:
            Notifier.send("Speech-to-Text", "No speech detected")
            print("No speech detected.")
    
    def run(self):
        """Run the application."""
        mode_str = "STREAMING (real-time)" if Config.STREAMING_MODE else "BATCH (after recording)"
        
        print("=" * 50)
        print("Speech-to-Text Application")
        print("=" * 50)
        print(f"Display Server: {Config.get_display_server()}")
        print(f"Mode: {mode_str}")
        print(f"Hotkey: Ctrl+Alt+R")
        print("-" * 50)
        print("Press Ctrl+Alt+R to start/stop recording")
        print("Press Ctrl+C to exit")
        print("=" * 50)
        
        Notifier.send("Speech-to-Text", f"Ready! Mode: {mode_str}")
        
        try:
            with keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            ) as listener:
                listener.join()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.recognizer.cleanup()


def main():
    """Entry point."""
    app = SpeechToTextApp()
    app.run()


if __name__ == "__main__":
    main()

