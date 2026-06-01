import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'data' / 'transcript_ddQq04IVLZU.txt'
with file_path.open('r', encoding='utf-8') as f:
    text = f.read()

keywords = [
    'chip', 'GPU', 'NVIDIA', 'TPU', 'H100', 'B100', 'B200', 'hardware',
    'valuation', 'billion', 'million', 'acquisition', 'merger', 'funding',
    '2026', '2027', 'Miniax', 'Max Hermes', 'Hermes', 'Open Claw', 
    'Kim Claw', 'Max Claw', 'Manis', 'Kim Hermes', 'Max Hermes Cloud', 'Minimax'
]

results = []
for k in keywords:
    # Use word boundaries for better matching where appropriate
    pattern = re.compile(f'.{{0,100}}{re.escape(k)}.{{0,100}}', re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        results.append(f"--- Matches for: {k} ---")
        results.extend(matches)
        results.append("")

print("\n".join(results))
