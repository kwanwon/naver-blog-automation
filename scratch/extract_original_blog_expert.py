# -*- coding: utf-8 -*-
import io
import json
import sys

def parse_view_file_content(content):
    lines = content.split("\n")
    original_lines = []
    
    # 진짜 코드 라인(숫자: )이 최초로 감지되었을 때부터 기록 시작
    real_code_started = False
    
    for line in lines:
        if "The above content does NOT show" in line or "If you need to view any lines" in line:
            break
            
        parts = line.split(":", 1)
        if len(parts) == 2:
            num_str = parts[0].strip()
            if num_str.isdigit():
                real_code_started = True
                val = parts[1]
                if val.startswith(" "):
                    val = val[1:]
                original_lines.append(val)
            else:
                if real_code_started:
                    original_lines.append(line)
        else:
            if real_code_started:
                original_lines.append(line)
            
    return "\n".join(original_lines).strip()

def main():
    log_path = "/Users/gm2hapkido/.gemini/antigravity-ide/brain/e92c0a6e-fdb2-4149-a55f-b8108a4e4cac/.system_generated/logs/transcript.jsonl"
    
    part1_content = None
    part2_content = None
    
    with io.open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                step = data.get("step_index")
                if step == 721:
                    part1_content = data.get("content", "")
                    print("Found Part 1 at step 721!")
                elif step == 755:
                    part2_content = data.get("content", "")
                    print("Found Part 2 at step 755!")
            except Exception as e:
                continue

    if part1_content is None or part2_content is None:
        print("Error: Could not find part 1 or part 2 of blog_expert.py in transcript.jsonl")
        sys.exit(1)

    part1_code = parse_view_file_content(part1_content)
    part2_code = parse_view_file_content(part2_content)
    
    full_code = part1_code + "\n" + part2_code
    
    output_path = "/Users/gm2hapkido/Desktop/라이온개발자/modules/ai_experts/blog_expert.py"
    with io.open(output_path, "w", encoding="utf-8") as f:
        f.write(full_code)
    
    print(f"Success: Fully restored original blog_expert.py at {output_path}!")

if __name__ == '__main__':
    main()
