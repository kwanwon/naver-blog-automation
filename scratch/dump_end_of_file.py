# -*- coding: utf-8 -*-
with open('modules/ai_experts/base_expert.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

for idx in range(1150, len(lines)):
    print(f"{idx+1:4d}: {lines[idx]}", end="")
