import json
import os

paths = [
    os.path.expanduser('~/.blog_automation/config/user_settings.txt'),
    '/Users/gm2hapkido/Desktop/라이온개발자/config/user_settings.txt'
]

new_tags = "양양합기도, 한국체대라이온합기도, 양양음악줄넘기, 양양줄넘기, 양양학원, 양양유아체육, 양양어린이운동, 양양태권도, 양양맘, 양양육아, 양양초등학교, 양양방과후, 양양차량운행, 양양키성장, 학교폭력예방"

for path in paths:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['blog_tags'] = new_tags
        # Also update band_hashtags and video_tags if they exist, but maybe just blog_tags is enough.
        # The user specifically mentioned "블로그 태그"
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated {path}")
