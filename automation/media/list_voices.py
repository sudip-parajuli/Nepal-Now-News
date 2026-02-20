import os
import requests

api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLAB_API_KEY")

def list_voices():
    if not api_key:
        print("No API key found in env.")
        return
        
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": api_key}
    print("Fetching voices...")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        voices = response.json().get("voices", [])
        for v in voices:
            name = v.get('name')
            vid = v.get('voice_id')
            cat = v.get('category')
            if 'jessica' in name.lower() or 'nepal' in name.lower() or cat == 'cloned' or cat == 'generated':
                print(f"MATCH: Name: {name}, ID: {vid}, Category: {cat}")
        print("Done fetching voices.")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    list_voices()
