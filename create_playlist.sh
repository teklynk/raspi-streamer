#!/bin/bash

# Get the user's home directory
HOME_DIR="$HOME"

# Directory containing media files
MEDIA_DIR="$HOME_DIR/raspi-streamer/media"
# Output playlist file
PLAYLIST_FILE="$HOME_DIR/raspi-streamer/playlist.txt"

# Create the directory if it does not exist
mkdir -p "$(dirname "$PLAYLIST_FILE")"

# Empty the playlist file or create it if it doesn't exist
> "$PLAYLIST_FILE"

# Loop through the media files in the directory
for file in "$MEDIA_DIR"/*; do
    # Check if the file is a regular file
    if [[ -f "$file" ]]; then
        # Add the file to the playlist
        echo "file '$file'" >> "$PLAYLIST_FILE"
    fi
done

echo "Playlist created: $PLAYLIST_FILE"
