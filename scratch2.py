import os, sys
sys.path.append(os.path.abspath('.'))
from modules.ai_experts.blog_expert import BlogExpert
expert = BlogExpert()
# Simulate post_type_config
post_type_config = {
    'spice_hometip': True,
    'informational_instructions': '테스트 추가 설명'
}

# Instead of generate_blog_content, let's just trace how _load_settings and active_spices works
ai_settings = expert._load_settings()

if post_type_config:
    for k, v in post_type_config.items():
        if k.startswith('spice_') or k.startswith('blog_') or k in ['is_promotional']:
            ai_settings[k] = v
            print(f"Merged {k}: {v}")

_spice_prompt_map = {
    'spice_hometip': "홈팁 양념",
}
active_spices = [
    _spice_prompt_map[k]
    for k in _spice_prompt_map
    if ai_settings.get(k, False)
]
print("Active spices:", active_spices)

info_instr = post_type_config.get("informational_instructions", "") if post_type_config else ""
print("Info instr:", info_instr)
