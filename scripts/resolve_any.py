import requests
import re
import sys

def resolve(handle):
    if not handle.startswith('@'): handle = '@' + handle
    r = requests.get(f"https://www.youtube.com/{handle}")
    match = re.search(r'"channelId":"(UC[\w-]+)"', r.text)
    if match: return match.group(1)
    match = re.search(r'href="https://www.youtube.com/channel/(UC[\w-]+)"', r.text)
    if match: return match.group(1)
    return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cid = resolve(sys.argv[1])
        if cid: print(cid)
        else: print("FAILED")
