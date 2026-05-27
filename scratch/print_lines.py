# -*- coding: utf-8 -*-
with open('modules/ai_experts/base_expert.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

start_line = 1420
end_line = 1518

for i in range(start_line - 1, min(end_line, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")
