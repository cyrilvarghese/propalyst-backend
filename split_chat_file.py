#!/usr/bin/env python3
"""
Script to split @_chat.txt into 100 chunks and store them in a folder
"""
import os
import math

def split_file_into_chunks(input_file: str, num_chunks: int = 100, output_folder: str = "chat_chunks"):
    """
    Split a file into specified number of chunks

    Args:
        input_file: Path to the input file
        num_chunks: Number of chunks to create (default: 100)
        output_folder: Folder to store chunks (default: "chat_chunks")
    """
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found!")
        return

    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder: {output_folder}")

    # Get file size
    file_size = os.path.getsize(input_file)
    print(f"File size: {file_size:,} bytes")

    # Calculate chunk size
    chunk_size = math.ceil(file_size / num_chunks)
    print(f"Chunk size: {chunk_size:,} bytes")
    print(f"Creating {num_chunks} chunks...")

    # Read and split file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    total_length = len(content)
    chunk_length = math.ceil(total_length / num_chunks)

    # Write chunks
    for i in range(num_chunks):
        start_idx = i * chunk_length
        end_idx = min((i + 1) * chunk_length, total_length)

        # Skip if we've reached the end
        if start_idx >= total_length:
            break

        chunk_content = content[start_idx:end_idx]

        # Create chunk filename with zero-padded numbers
        chunk_filename = os.path.join(output_folder, f"chunk_{i+1:03d}.txt")

        with open(chunk_filename, 'w', encoding='utf-8') as chunk_file:
            chunk_file.write(chunk_content)

        print(f"  ✓ Created {chunk_filename} ({len(chunk_content):,} chars)")

    print(f"\n✓ Successfully split file into {num_chunks} chunks in '{output_folder}' folder")


if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "_chat.txt"
    NUM_CHUNKS = 100
    OUTPUT_FOLDER = "chat_chunks"

    print(f"=== File Splitter ===")
    print(f"Input: {INPUT_FILE}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Number of chunks: {NUM_CHUNKS}")
    print("=" * 50)

    split_file_into_chunks(INPUT_FILE, NUM_CHUNKS, OUTPUT_FOLDER)
