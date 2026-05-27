# -*- coding: utf-8 -*-
import re

file_path = 'modules/ai_experts/band_expert.py'

print("Reading file...")
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

target = 'return f"\\n[System: 실시간 날씨 상세 정보]\\n- 데    def generate_band_content(self, topic, platform=\'band\', task_type=\'regular\', target_time=None, delta_days=0):'
replacement = 'return f"\\n[System: 실시간 날씨 상세 정보]\\n- 데이터: {combined_info}"\n\n    def generate_band_content(self, topic, platform=\'band\', task_type=\'regular\', target_time=None, delta_days=0):'

if target in content:
    content = content.replace(target, replacement)
    print("✅ Found target and replaced successfully.")
else:
    # Regular expression fallback if target mismatch due to weird characters
    pattern = r'return f"\\n\[System: 실시간 날씨 상세 정보\]\\n- 데.*?def generate_band_content'
    match = re.search(pattern, content)
    if match:
        print(f"🎯 Pattern match found: {match.group(0)}")
        content = re.sub(pattern, 'return f"\\n[System: 실시간 날씨 상세 정보]\\n- 데이터: {combined_info}"\n\n    def generate_band_content', content)
        print("✅ Replaced pattern successfully.")
    else:
        print("❌ Target/Pattern not found in file!")
        # Let's inspect around the word "generate_band_content"
        idx = content.find("def generate_band_content")
        if idx != -1:
            print("Inspection around generate_band_content:\n", content[idx-100:idx+200])

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated successfully.")
