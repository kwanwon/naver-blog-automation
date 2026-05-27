import json
from pathlib import Path
import re

# Load analysis
analysis_path = Path('graphify-out/.graphify_analysis.json')
analysis = json.loads(analysis_path.read_text())
communities = {int(k): v for k, v in analysis['communities'].items()}

# Mapping dictionary for communities
labels = {}

# We define standard semantic mappings for well-known prefixes in our codebase
def get_label_for_community(cid, nodes):
    # If the community has specific prominent nodes, name accordingly
    all_text = " ".join(nodes).lower()
    
    # 0. Build & Deploy
    if any(k in all_text for k in ['deploy', 'pyinstaller', 'scripts_build', 'cross_platform']):
        return "Build and Deployment Pipeline"
    
    # 1. Naver Blog core
    if any(k in all_text for k in ['blog_auto', 'post_finisher', 'insert_image']):
        return "Naver Blog Automated Posting"
    
    # 2. Schedule Parser & Training
    if any(k in all_text for k in ['schedule_parser', 'planner_engine', 'calendar_writer']):
        return "Curriculum & Training Scheduler"
        
    # 3. Serial validation
    if any(k in all_text for k in ['serial_validator', 'serial_client', 'serialmanager', 'blogserialauth']):
        return "Licensing & Serial Authentication"
        
    # 4. Manual login / session helper
    if any(k in all_text for k in ['manual_login', 'manual_session', 'session_helper']):
        return "Chrome Manual Login & Sessions"
        
    # 5. UI Dashboard / Flet application
    if any(k in all_text for k in ['blog_writer_app', 'blogtab', 'flet_ui']):
        return "Flet Core UI & Dashboard"
        
    # 6. Idle activity / reply crawler
    if any(k in all_text for k in ['idle_activity', 'reply_crawler', 'comment_reply']):
        if 'band' in all_text:
            return "Naver Band Automated Replies"
        if 'cafe' in all_text:
            return "Naver Cafe Automated Replies"
        return "Social Automated Interactions"
        
    # 7. Auto updater
    if any(k in all_text for k in ['auto_updater', 'release_updater', 'update_monitor']):
        return "Software Auto Update System"
        
    # 8. Chrome manager & webdriver
    if any(k in all_text for k in ['chrome_manager', 'chromedriver', 'wdm']):
        return "Chrome Driver & WebDriver Settings"
        
    # 9. AI handlers
    if any(k in all_text for k in ['ai_handler', 'gpt_handler', 'base_expert', 'blog_expert', 'cafe_expert', 'social_expert', 'band_expert']):
        return "AI Handlers & Gemini Experts"

    # Default fallback: Extract common keywords or representative node stem
    # Filter out common terms like 'file_', 'concept_', 'rationale_'
    stems = []
    for node in nodes:
        cleaned = re.sub(r'^(file_|concept_|scripts_|tests_)', '', node)
        cleaned = re.sub(r'(_py|_json|_txt|_md)$', '', cleaned)
        cleaned = re.sub(r'_\d+$', '', cleaned)  # remove line numbers or trailing numbers
        cleaned = cleaned.replace('_', ' ')
        stems.append(cleaned.title())
        
    # Find most common word or representative node name
    if stems:
        # Sort by length, take the longest descriptive one
        longest = max(stems, key=len)
        words = longest.split()
        if len(words) > 4:
            return " ".join(words[:4])
        return longest
    
    return f"Submodule Group {cid}"

# Process all 159 communities
for cid, nodes in communities.items():
    label = get_label_for_community(cid, nodes)
    # Ensure it's not too long and is between 2-5 words
    words = label.split()
    if len(words) < 2:
        label = label + " Module"
    labels[cid] = label

# Save the labels dictionary as JSON
labels_out = {str(k): v for k, v in labels.items()}
Path('graphify-out/.graphify_labels.json').write_text(json.dumps(labels_out, indent=2))
print(f"Generated {len(labels)} community labels.")
