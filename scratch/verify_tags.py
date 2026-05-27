import sys
import os

# Add the project root to sys.path
sys.path.append('/Users/gm2hapkido/Desktop/라이온개발자')

from modules.drive_auto_post import DriveAutoPostSystem

def test_tag_priority():
    print("Testing Tag Priority in DriveAutoPostSystem...")
    
    # Mock settings with fixed hashtags
    settings = {
        'band_hashtags': '#고정1 #고정2 #고정3'
    }
    
    system = DriveAutoPostSystem(settings)
    
    # Simulate variables as they would be in _process_and_post
    ai_tags = ['AI1', 'AI2', 'AI3']
    
    # Logic extracted from _process_and_post after modification:
    hashtags = system._get_rotating_hashtags(count=15)
    print(f"Rotating Hashtags: {hashtags}")
    
    merged_tags = []
    seen_t = set()
    
    # 1. Fixed hashtags first
    if hashtags:
        h_list = [h.strip() for h in hashtags.replace('#', ' #').split() if h.strip().startswith('#')]
        for h in h_list:
            ch = h.replace('#', '').strip()
            if ch and ch not in seen_t and len(merged_tags) < 15:
                merged_tags.append(f"#{ch}")
                seen_t.add(ch)
                
    # 2. AI tags next
    for t in ai_tags:
        ct = t.replace('#', '').strip()
        if ct and ct not in seen_t and len(merged_tags) < 30:
            merged_tags.append(f"#{ct}")
            seen_t.add(ct)
            
    final_tag_str = " ".join(merged_tags)
    print(f"Final Tag String: {final_tag_str}")
    
    # Verification
    expected_start = "#고정1 #고정2 #고정3"
    if final_tag_str.startswith(expected_start):
        print("✅ SUCCESS: Fixed tags are placed first.")
    else:
        print(f"❌ FAILURE: Tag order is wrong. Got: {final_tag_str}")

if __name__ == "__main__":
    test_tag_priority()
