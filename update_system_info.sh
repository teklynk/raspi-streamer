#!/bin/bash

# Define the output file
OUTPUT_FILE="system_info.txt"

# Truncate the output file
> "$OUTPUT_FILE"

# Run lsub and append the output to the file
echo "Output of lsusb:" >> "$OUTPUT_FILE"
lsusb >> "$OUTPUT_FILE"
echo -e "\n" >> "$OUTPUT_FILE"

# Run arecord -l and append the output to the file
echo "Output of arecord -l:" >> "$OUTPUT_FILE"
arecord -l >> "$OUTPUT_FILE"
echo -e "\n" >> "$OUTPUT_FILE"

# Run v4l2-ctl --list-formats-ext and append the output to the file
echo "Output of v4l2-ctl --list-formats-ext:" >> "$OUTPUT_FILE"
v4l2-ctl --list-formats-ext >> "$OUTPUT_FILE"
echo -e "\n" >> "$OUTPUT_FILE"

echo "System information saved to $OUTPUT_FILE"