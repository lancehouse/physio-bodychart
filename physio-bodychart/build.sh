#!/usr/bin/env bash
# PhysioChart — build script for Fedora 43
# Run this from the physio-bodychart/ directory

set -e

echo "=== PhysioChart build ==="

# Install dependencies (only needed once)
if ! rpm -q gtk4-devel &>/dev/null; then
    echo "Installing build dependencies..."
    sudo dnf install -y \
        gcc \
        meson \
        ninja-build \
        gtk4-devel \
        cairo-devel \
        librsvg2-devel \
        json-c-devel \
        libinput-devel
fi

# Configure (first time only — meson setup is idempotent)
if [ ! -d build ]; then
    echo "Configuring build..."
    meson setup build --buildtype=debugoptimized
fi

# Compile
echo "Building..."
ninja -C build

echo ""
echo "=== Build complete ==="
echo "Run with:  ./build/physio-bodychart"
echo ""
echo "Keyboard shortcuts:"
echo "  Q/W/E/R/T   — symptom type (pain/intermt/pins/numb/ache)"
echo "  D/X/L       — draw / erase / link tool"
echo "  O           — toggle overlay"
echo "  1/2/3       — overlay category (dermatome/peripheral/somatic)"
echo "  [  ]        — previous / next overlay"
echo "  F1–F8       — body view (ant/post/lat-r/lat-l/hand×2/foot×2)"
echo "  F9          — toggle 4-view / single view"
echo "  Ctrl+Z      — undo"
echo "  Ctrl+Del    — clear all"
