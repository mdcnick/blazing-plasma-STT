#!/bin/bash
#
# Speech-to-Text App - Uninstall Script
#

echo "====================================="
echo "Speech-to-Text Uninstaller"
echo "====================================="
echo

# Remove autostart entry
if [ -f "$HOME/.config/autostart/speech-to-text.desktop" ]; then
    rm "$HOME/.config/autostart/speech-to-text.desktop"
    echo "✓ Removed autostart entry"
else
    echo "  Autostart entry not found (skipped)"
fi

# Remove CLI symlink
if [ -L "$HOME/.local/bin/speech-to-text" ]; then
    rm "$HOME/.local/bin/speech-to-text"
    echo "✓ Removed CLI symlink"
else
    echo "  CLI symlink not found (skipped)"
fi

# Ask about config
echo
read -p "Remove user config (~/.config/speech-to-text)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/speech-to-text"
    echo "✓ Removed user config"
else
    echo "  Kept user config"
fi

# Ask about Vosk model
echo
read -p "Remove Vosk model (~/.local/share/vosk-models)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.local/share/vosk-models"
    echo "✓ Removed Vosk model"
else
    echo "  Kept Vosk model"
fi

echo
echo "====================================="
echo "Uninstall complete!"
echo "====================================="
echo
echo "Note: The application directory was NOT removed."
echo "You can delete it manually if desired:"
echo "  rm -rf $(dirname "$0")"
