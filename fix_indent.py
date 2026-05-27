import re

with open('naver_band_auto.py', 'r') as f:
    lines = f.readlines()

# _enter_content 함수 추출 (228~252번 라인)
enter_content_lines = lines[228:253]

# post_to_band 함수의 끝 찾기
end_idx = len(lines)
for i in range(253, len(lines)):
    if lines[i].startswith('    def '):
        end_idx = i
        break

# 253번 라인부터 post_to_band 끝까지 4칸 들여쓰기 제거
dedented_lines = []
for line in lines[253:end_idx]:
    if line.startswith('    '):
        dedented_lines.append(line[4:])
    else:
        dedented_lines.append(line)

# 파일 재구성 (_enter_content를 post_to_band 뒤로 이동)
new_lines = lines[:228] + dedented_lines + enter_content_lines + lines[end_idx:]

with open('naver_band_auto.py', 'w') as f:
    f.writelines(new_lines)

print("✅ 들여쓰기 및 함수 구조 복구 완료!")
