import sys
import os
import json

# Add the project root to sys.path
sys.path.append('/Users/gm2hapkido/Desktop/라이온개발자')

from blog_writer_app import BlogWriterApp

def test_user_settings_loading():
    print("Testing Tag Loading from user_settings.txt...")
    
    app = BlogWriterApp()
    
    # Mock some AI tags
    ai_tags = ['AI추천1', 'AI추천2']
    content = "오늘의 수련 내용입니다. 칭찬 스티커를 활용했어요."
    
    # Execute the actual method
    final_tags = app._get_merged_tags('blog', ai_tags, content)
    
    print(f"Final Tags: {final_tags}")
    
    # Check if '양양합기도' (from user_settings.txt) is in the tags
    if '양양합기도' in final_tags:
        print("✅ SUCCESS: '양양합기도' found in merged tags!")
    else:
        print("❌ FAILURE: Fixed tags from user_settings.txt are missing.")
        
    # Check order
    if final_tags[0] == '양양합기도':
         print("✅ SUCCESS: Fixed tags are FIRST.")
    else:
         print(f"❌ FAILURE: First tag is {final_tags[0]}, expected '양양합기도'.")

if __name__ == "__main__":
    test_user_settings_loading()
