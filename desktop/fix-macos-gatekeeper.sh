#!/bin/bash
# Fix macOS Gatekeeper "app is damaged" error
# Run this script if VPACK.app shows "damaged" error

APP_PATH="$1"

if [ -z "$APP_PATH" ]; then
    # Try to find VPACK.app in common locations
    if [ -d "/Applications/VPACK.app" ]; then
        APP_PATH="/Applications/VPACK.app"
    elif [ -d "$HOME/Applications/VPACK.app" ]; then
        APP_PATH="$HOME/Applications/VPACK.app"
    elif [ -d "./VPACK.app" ]; then
        APP_PATH="./VPACK.app"
    else
        echo "Usage: $0 /path/to/VPACK.app"
        echo "Or place VPACK.app in current directory"
        exit 1
    fi
fi

echo "Fixing Gatekeeper issue for: $APP_PATH"

# Remove quarantine attribute
echo "1. Removing quarantine attributes..."
xattr -cr "$APP_PATH"

# Ad-hoc code sign
echo "2. Applying ad-hoc code signature..."
codesign --force --deep --sign - "$APP_PATH"

# Verify
echo "3. Verifying signature..."
codesign --verify --verbose "$APP_PATH"

echo ""
echo "✅ Done! Try opening VPACK.app now."
echo ""
echo "If still blocked, try:"
echo "  1. Right-click VPACK.app → Open"
echo "  2. Or: System Settings → Privacy & Security → Allow anyway"
