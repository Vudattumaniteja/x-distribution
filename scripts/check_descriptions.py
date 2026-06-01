import requests
import re

def get_yt_description(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        # Look for the description in the page source
        # Usually it's in a script tag or meta tag
        match = re.search(r'"shortDescription":"(.*?)"', response.text)
        if match:
            return match.group(1).encode().decode('unicode_escape')
    except Exception as e:
        return str(e)
    return "Description not found"

print("Description for AIi6L26HGCU:")
print(get_yt_description("https://www.youtube.com/shorts/AIi6L26HGCU"))
print("\nDescription for gP9231d8uk4:")
print(get_yt_description("https://www.youtube.com/shorts/gP9231d8uk4"))
