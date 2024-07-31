#!/bin/bash

# Get the user's current directory
CUR_DIR="$(pwd)"

# Directory containing media files
MEDIA_DIR="$CUR_DIR/media"
# Output playlist file
PLAYLIST_FILE="$CUR_DIR/playlist.txt"

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

