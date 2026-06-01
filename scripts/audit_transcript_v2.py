import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'data' / 'transcript_ddQq04IVLZU.txt'
with file_path.open('r', encoding='utf-8') as f:
    text = f.read()

# Categories
hardware_keywords = ['chip', 'GPU', 'NVIDIA', 'TPU', 'H100', 'B100', 'B200', 'hardware', 'M2.7', 'M2', 'M1']
valuation_keywords = ['valuation', 'billion', 'million', 'acquisition', 'merger', 'funding', 'M&A', 'buyout', 'sold', 'acquired']
product_keywords = ['Miniax', 'Max Hermes', 'Hermes', 'Open Claw', 'Kim Claw', 'Max Claw', 'Manis', 'Miniaax', 'Max floor', 'Kimy', 'Kimmy', 'Claude', 'Opus']
timeline_keywords = ['2026', '2027', 'Q1', 'Q2', 'Q3', 'Q4', 'launch', 'release', 'roadmap']

def find_matches(keywords, is_word=True):
    results = []
    for k in keywords:
        if is_word:
            pattern = re.compile(rf'.{{0,100}}\b{re.escape(k)}\b.{{0,100}}', re.IGNORECASE)
        else:
            pattern = re.compile(rf'.{{0,100}}{re.escape(k)}.{{0,100}}', re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            results.append(f"--- Matches for: {k} ---")
            results.extend([m.strip() for m in matches])
            results.append("")
    return results

print("=== HARDWARE/CHIPS ===")
print("\n".join(find_matches(hardware_keywords)))

print("=== VALUATIONS/M&A ===")
print("\n".join(find_matches(valuation_keywords)))

print("=== PRODUCT NAMES ===")
print("\n".join(find_matches(product_keywords)))

print("=== TIMELINES (2026/2027) ===")
print("\n".join(find_matches(timeline_keywords)))

# Look for any 4-digit years
years = re.findall(r'\b202\d\b', text)
if years:
    print("=== POTENTIAL YEARS FOUND ===")
    print(list(set(years)))

# Look for dollar amounts
dollars = re.findall(r'\$\d+(?:\.\d+)?\s*(?:billion|million|B|M)?', text, re.IGNORECASE)
if dollars:
    print("=== POTENTIAL VALUATIONS/FUNDING FOUND ===")
    print(list(set(dollars)))
