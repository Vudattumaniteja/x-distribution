import json
import os
import math

def partition_news_queue():
    queue_path = 'data/news_queue.json'
    segments_dir = 'tmp_segments'
    num_agents = 6

    if not os.path.exists(segments_dir):
        os.makedirs(segments_dir)

    if not os.path.exists(queue_path):
        print(f"Error: {queue_path} not found.")
        return

    from intelligence_queue import load_queue
    _, data = load_queue()
    if not isinstance(data, list):
        print("Error: 'items' in news_queue.json is not a list.")
        return

    total_items = len(data)
    chunk_size = math.ceil(total_items / num_agents)
    
    print(f"Splitting {total_items} items into {num_agents} segments (chunk size ~{chunk_size})...")

    for i in range(num_agents):
        segment = data[i * chunk_size : (i + 1) * chunk_size]
        segment_path = os.path.join(segments_dir, f'segment_{i+1}.json')
        with open(segment_path, 'w', encoding='utf-8') as f:
            json.dump(segment, f, indent=2)
        print(f"  -> Saved segment_{i+1}.json ({len(segment)} items)")

if __name__ == "__main__":
    partition_news_queue()
