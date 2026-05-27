# -*- coding: utf-8 -*-

file_path = 'modules/ai_experts/band_expert.py'

print("Reading file...")
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Let's find the correct ending point of the class
# It ends with the fallback dictionary:
#         return {
#             "title": f"[{platform}] {topic}",
#             "content": fallback_body,
#             "tags": "수련,성장,건강,열정,화이팅,합기도,유아체육,어린이운동,실전무술,체육관",
#             "model": "fallback"
#         }
# Followed by the weird garbage text

target_end_marker = """        return {
            "title": f"[{platform}] {topic}",
            "content": fallback_body,
            "tags": "수련,성장,건강,열정,화이팅,합기도,유아체육,어린이운동,실전무술,체육관",
            "model": "fallback"
        }"""

idx = content.find(target_end_marker)
if idx != -1:
    print(f"✅ Found end marker at index {idx}!")
    # Keep content only up to the end of the dictionary
    trimmed_content = content[:idx + len(target_end_marker)] + "\n"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(trimmed_content)
    print("✅ File trimmed successfully.")
else:
    print("❌ End marker not found exactly. Let's try flexible search.")
    # Search for "fallback" dictionary ending pattern
    import re
    # Match the end of dict followed by garbage "명사"
    pattern = r'("model":\s*"fallback"\s*\n\s*\})(?=명사)'
    match = re.search(pattern, content)
    if match:
        print(f"🎯 Pattern match found: {match.group(0)}")
        split_idx = match.end()
        trimmed_content = content[:split_idx] + "\n"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(trimmed_content)
        print("✅ File trimmed successfully via regex pattern.")
    else:
        print("❌ Regex pattern not found either!")
