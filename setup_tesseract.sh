#!/data/data/com.termux/files/usr/bin/bash

# Update packages
pkg update -y && pkg upgrade -y

# Install tesseract OCR
pkg install -y tesseract curl

# Create tessdata directory
mkdir -p ~/.local/share/tessdata
cd ~/.local/share/tessdata

# Download English and Japanese traineddata
echo "Downloading Tesseract language files..."
curl -O https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
curl -O https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata

# Set environment variable
echo 'export TESSDATA_PREFIX=$HOME/.local/share/' >> ~/.bashrc
source ~/.bashrc

# Install font directory and DejaVuSans
mkdir -p ~/.fonts
cd ~/.fonts
curl -L -o DejaVuSans.ttf https://github.com/dejavu-fonts/dejavu-fonts/blob/master/ttf/DejaVuSans.ttf?raw=true

echo "All set! You can now use Tesseract with English and Japanese OCR, and custom fonts in Python."
