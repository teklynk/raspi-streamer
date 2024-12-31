#!/bin/bash

convert_file() {
    local input_file="$1"
    local filename=$(basename "$input_file")
    local output_dir="$HOME/raspi-streamer/media"
    local output_file="$output_dir/${filename%.*}.mp4"

    # Create the output directory if it doesn't exist
    mkdir -p "$output_dir"

    # Convert video using ffmpeg - Burn in subtitles if .srt file exists
    if [ -f "$input_file" ]; then
      filename_no_ext="${input_file%.*}"
      if [ -f "$filename_no_ext.srt" ]; then
        ffmpeg -i "$input_file" -vf "scale=1280:-2, subtitles=$filename_no_ext.srt" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 96k "$output_file"
      else
        ffmpeg -i "$input_file" -vf "scale=1280:-2" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 96k "$output_file"
      fi
    else
      echo "Error: Input file not found."
    fi
    
    echo "Conversion complete. Output saved to $output_file"
}

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 -f <input_file> | -d <input_directory>"
    exit 1
fi

option="$1"
input_path="$2"

# List of supported video extensions
video_extensions="avi mkv mp4 m4v ts vid"

# Function to check if a file has a valid video extension
is_video_file() {
    local file="$1"
    local extension="${file##*.}"
    for ext in $video_extensions; do
        if [[ "$extension" == "$ext" ]]; then
            return 0
        fi
    done
    return 1
}

if [ "$option" == "-f" ]; then
    if [ -f "$input_path" ]; then
        if is_video_file "$input_path"; then
            convert_file "$input_path"
        else
            echo "Error: $input_path is not a valid video file."
            exit 1
        fi
    else
        echo "Error: $input_path is not a valid file."
        exit 1
    fi
elif [ "$option" == "-d" ]; then
    if [ -d "$input_path" ]; then
        for file in "$input_path"/*; do
            if [ -f "$file" ] && is_video_file "$file"; then
                convert_file "$file"
            fi
        done
    else
        echo "Error: $input_path is not a valid directory."
        exit 1
    fi
else
    echo "Usage: $0 -f <input_file> | -d <input_directory>"
    exit 1
fi
