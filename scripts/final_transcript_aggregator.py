import json
import os
from datetime import datetime, timezone

def aggregate_all_transcripts():
    transcripts_dir = 'data/transcripts'
    output_path = 'data/mass_transcript_pool.json'
    
    if not os.path.exists(transcripts_dir):
        print(f"Directory not found: {transcripts_dir}")
        return

    pool = []
    
    # Get all .txt files in the directory
    files = [f for f in os.listdir(transcripts_dir) if f.endswith('.txt')]
    print(f"Found {len(files)} transcript files. Aggregating...")
    
    for filename in files:
        file_path = os.path.join(transcripts_dir, filename)
        
        # Try to parse video ID and Title from filename (Format: ID_Title.txt)
        if "_" in filename:
            video_id = filename.split("_")[0]
            title = filename.split("_", 1)[1].replace(".txt", "")
        else:
            video_id = "unknown"
            title = filename.replace(".txt", "")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            pool.append({
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id != "unknown" else "N/A",
                "transcript": content[:10000], # Include first 10k chars for agent scanning
                "full_transcript_path": file_path,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            print(f"  ✗ Error reading {filename}: {e}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pool, f, indent=2)
    
    print(f"Success! {len(pool)} transcripts consolidated into {output_path}")

if __name__ == "__main__":
    aggregate_all_transcripts()
