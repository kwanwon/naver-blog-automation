
import os

file_path = '/Users/gm2hapkido/Desktop/라이온개발자/blog_writer_app.py'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 문제가 발생한 영역(465~600 근처)을 정확히 찾아 교체
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'def _prepare_band_content' in line:
        start_idx = i
        break

if start_idx != -1:
    # 다음 함수 시작 지점까지를 삭제 범위로 지정
    for i in range(start_idx + 1, len(lines)):
        if 'def _clean_intro_overlap' in lines[i]:
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    new_code = """    def _prepare_band_content(self, ai_content: str, ai_tags: list = None, mode: str = 'band') -> str:
        \"\"\"
        [밴드 포스팅 공통 파이프라인]
        모든 밴드 포스팅 모드(탭/스케줄러/감지/수동주제)가 동일한 순서로 처리됩니다.
        \"\"\"
        # 1단계: 태그 병합
        final_tags = self._get_merged_tags(mode, ai_tags or [], ai_content or '')
        
        # 2단계: AI 본문 포맷팅
        formatted = self._format_content_for_blog(ai_content or '', platform='band')
        
        # 3단계: 슬로건 + 태그 결합
        final_content = self._get_formatted_content(mode, formatted, final_tags)
        return final_content

    def _get_formatted_content(self, platform, content, tags):
        \"\"\"본문에 태그를 포함해야 하는 플랫폼(밴드, 카페)용 포맷팅\"\"\"
        if not content:
            return ""
            
        if platform == 'blog':
            # 블로그 슬로건 추가 로직
            blog_slogan = ""
            try:
                user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
                if os.path.exists(user_settings_path):
                    with open(user_settings_path, 'r', encoding='utf-8') as f:
                        import json
                        u_s = json.load(f)
                        blog_slogan = (u_s.get('blog_slogan') or u_s.get('slogan') or "").strip()
            except: pass
            
            if not blog_slogan:
                blog_slogan = self.settings.get('blog_slogan', self.settings.get('slogan', '')).strip()
            
            if blog_slogan:
                slogan_clean = blog_slogan.split('#')[0].strip()
                if slogan_clean and slogan_clean not in content:
                    return f"{content}\\n\\n{blog_slogan}"
            return content
            
        # 1. 슬로건 가져오기 (밴드/카페)
        slogan = ""
        is_group_a = platform in ['drive_auto', 'manual_topic']
        
        try:
            user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
            if os.path.exists(user_settings_path):
                with open(user_settings_path, 'r', encoding='utf-8') as f:
                    import json
                    u_s = json.load(f)
                    if platform == 'band' or is_group_a:
                        slogan = u_s.get('band_slogan', '').strip()
                    elif platform == 'cafe':
                        slogan = u_s.get('cafe_slogan', '').strip()
        except: pass

        if not slogan:
            if platform == 'band' or is_group_a:
                slogan = self.settings.get('band_slogan', '').strip()
            elif platform == 'cafe':
                slogan = self.settings.get('cafe_slogan', '').strip()
            
        # 2. 본문 클리닝 (AI가 넣은 해시태그 제거)
        import re
        final_content = re.sub(r'\\n\\s*(#[\\\\w가-힣]+\\s*)+', '\\n', content).strip()
        final_content = re.sub(r'(#[\\\\w가-힣]+\\s*){3,}', '', final_content).strip()
        
        # 3. 본문에 슬로건 추가 (Group A는 제외)
        if slogan and not is_group_a:
            if platform == 'band':
                slogan = re.sub(r'(\\\\d{2,3}[-\\\\s]\\\\d{3,4}[-\\\\s]\\\\d{4})', '', slogan).strip()
                slogan = re.sub(r'(📞\\\\s*)?문의\\\\s*:\\\\s*', '', slogan).strip()
                slogan = re.sub(r'[\\\\s,]+$', '', slogan).strip()

            slogan_clean = slogan.split('#')[0].strip()
            if slogan_clean and slogan_clean not in final_content:
                final_content = f"{final_content}\\n\\n{slogan}"
        
        # [방어 로직] Group A인데 슬로건이 딸려왔다면 제거
        if is_group_a and slogan:
            slogan_clean = slogan.split('#')[0].strip()
            if slogan_clean and slogan_clean in final_content:
                final_content = final_content.replace(slogan_clean, "").strip()
            
        # 4. 태그 추가
        if not tags:
            return final_content
            
        existing_tags = set(re.findall(r'#(#[\\\\w가-힣]+)', final_content))
        new_tags = [t for t in tags if t not in existing_tags]
        
        if not new_tags:
            return final_content
            
        tag_str = " ".join([f"#{t}" for t in new_tags])
        return f"{final_content}\\n\\n{tag_str}\\n\\n"

"""
    # 합치기
    fixed_lines = lines[:start_idx] + [new_code] + lines[end_idx:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    print("Successfully fixed blog_writer_app.py")
else:
    print(f"Failed to find start/end marks: start={start_idx}, end={end_idx}")
