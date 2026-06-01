import json
import os
import glob
import math

SEGMENTS_DIR = "tmp_segments"
DATA_DIR = "data"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def chunk_json_file(filename, chunk_size=30, list_key=None):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {filepath}")
            return

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if list_key and list_key in data:
            items = data[list_key]
        else:
            # Find the largest list in the dict
            largest_list = []
            best_key = None
            for k, v in data.items():
                if isinstance(v, list) and len(v) > len(largest_list):
                    largest_list = v
                    best_key = k
            if best_key:
                items = largest_list
            else:
                print(f"No list found in {filepath}")
                return
    else:
        print(f"Unsupported JSON structure in {filepath}")
        return

    total_items = len(items)
    num_chunks = math.ceil(total_items / chunk_size)
    print(f"Chunking {filename} ({total_items} items) into {num_chunks} chunks of size {chunk_size}")

    base_name = os.path.splitext(filename)[0]
    for i in range(num_chunks):
        chunk_items = items[i*chunk_size : (i+1)*chunk_size]
        chunk_filename = f"{base_name}_chunk_{i+1}.json"
        chunk_filepath = os.path.join(SEGMENTS_DIR, chunk_filename)
        with open(chunk_filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk_items, f, indent=2)

def main():
    ensure_dir(SEGMENTS_DIR)
    
    # Files to chunk and their chunk sizes
    files_to_chunk = [
        ("x_radar_standalone.json", 30),
        ("sitemap_history.json", 30),
        ("reddit_raw_standalone.json", 30),
        ("corporate_announcements.json", 30),
        ("arxiv_raw_standalone.json", 30),
        ("mass_transcript_pool.json", 5), # Transcripts are large, chunk size 5
        ("new_videos_queue.json", 30)
    ]
    
    for filename, chunk_size in files_to_chunk:
        chunk_json_file(filename, chunk_size)
        
    print("Chunking complete.")

if __name__ == "__main__":
    main()
