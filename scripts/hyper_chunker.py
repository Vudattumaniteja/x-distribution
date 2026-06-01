import json
import os
import math

HYPER_DIR = "tmp_hyper"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def chunk_json_file(data_path, filename, chunk_size=5):
    filepath = os.path.join(data_path, filename)
    if not os.path.exists(filepath):
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except:
            return

    # Handle if data is under 'items' key
    if isinstance(data, dict) and 'items' in data:
        items = data['items']
    elif isinstance(data, dict) and 'new_discoveries' in data:
        items = data['new_discoveries']
    elif isinstance(data, list):
        items = data
    else:
        # Find largest list
        largest_list = []
        for v in data.values():
            if isinstance(v, list) and len(v) > len(largest_list):
                largest_list = v
        items = largest_list

    total_items = len(items)
    num_chunks = math.ceil(total_items / chunk_size)
    
    sub_dir = os.path.join(HYPER_DIR, filename.split('.')[0])
    ensure_dir(sub_dir)
    
    print(f"Chunking {filename} into {num_chunks} files of size {chunk_size} in {sub_dir}")
    
    for i in range(num_chunks):
        chunk = items[i*chunk_size : (i+1)*chunk_size]
        chunk_file = os.path.join(sub_dir, f"part_{i+1}.json")
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2)

def chunk_transcripts(data_path, chunk_size=50):
    transcript_file = os.path.join(data_path, "mass_transcript_pool.json")
    if not os.path.exists(transcript_file):
        return
        
    with open(transcript_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    sub_dir = os.path.join(HYPER_DIR, "transcripts")
    ensure_dir(sub_dir)
    
    chunk_idx = 1
    for entry in data:
        lines = entry.get('transcript', '').splitlines()
        num_chunks = math.ceil(len(lines) / chunk_size)
        
        for i in range(num_chunks):
            chunk_lines = lines[i*chunk_size : (i+1)*chunk_size]
            chunk_file = os.path.join(sub_dir, f"part_{chunk_idx}.txt")
            with open(chunk_file, 'w', encoding='utf-8') as f:
                f.write(f"VIDEO: {entry.get('title')}\nURL: {entry.get('url')}\n\n")
                f.write('\n'.join(chunk_lines))
            chunk_idx += 1
            
    print(f"Chunked transcripts into {chunk_idx-1} files.")

def main():
    ensure_dir(HYPER_DIR)
    data_path = "data"
    
    # User count mapping: X(2), Corp(2), Reddit(3), YT(4)
    # We just need to chunk everything small.
    
    chunk_json_file(data_path, "x_radar_standalone.json", chunk_size=5)
    chunk_json_file(data_path, "reddit_raw_standalone.json", chunk_size=5)
    chunk_json_file(data_path, "corporate_announcements.json", chunk_size=5)
    chunk_json_file(data_path, "sitemap_history.json", chunk_size=10) # Sitemaps are tiny rows
    
    chunk_transcripts(data_path, chunk_size=50)

if __name__ == "__main__":
    main()
