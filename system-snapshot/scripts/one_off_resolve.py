import requests
import re

handles = ['@100xEngineers', '@vaibhavsisinty']
for h in handles:
    r = requests.get(f"https://www.youtube.com/{h}")
    match = re.search(r'"channelId":"(UC[\w-]+)"', r.text)
    if match:
        print(f"{h}: {match.group(1)}")
    else:
        # Try canonical
        match = re.search(r'href="https://www.youtube.com/channel/(UC[\w-]+)"', r.text)
        if match:
            print(f"{h}: {match.group(1)}")
        else:
            print(f"{h}: FAILED")
