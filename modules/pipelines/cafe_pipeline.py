import os
import json
import re

class CafePipeline:
    @staticmethod
    def _get_settings(app_data_dir):
        user_settings = {}
        try:
            settings_path = os.path.join(app_data_dir, 'config', 'user_settings.txt')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
        except Exception as e:
            print(f"⚠️ [CafePipeline] 설정 파일 로드 실패: {e}")
        return user_settings

    @staticmethod
    def _clean_intro_overlap(intro, content):
        if not intro or not content:
            return content
            
        greeting_patterns = [
            r'^안녕하세요[,!\.\s]*', 
            r'^반갑습니다[,!\.\s]*', 
            r'^오늘도\s+좋은\s+하루입니다[,!\.\s]*',
            r'^소중한\s+아이들과[,!\.\s]*',
            r'^날씨가\s+[가-힣]+\s+오늘[,!\.\s]*',
            r'^벌써\s+[가-힣]+\s+요즘[,!\.\s]*'
        ]
        
        cleaned_content = content.strip()
        intro_clean = intro.strip()
        
        lines = cleaned_content.split('\n')
        if lines:
            first_line = lines[0].strip()
            is_overlap = any(re.match(p, first_line) for p in greeting_patterns)
            if not is_overlap and len(intro_clean) > 5 and len(first_line) > 5:
                words_intro = set(intro_clean.split())
                words_first = set(first_line.split())
                if words_first and len(words_intro.intersection(words_first)) / len(words_first) > 0.5:
                    is_overlap = True
                    
            if is_overlap:
                cleaned_content = '\n'.join(lines[1:]).strip()
                
        return cleaned_content

    @staticmethod
    def process(content, ai_tags, app_data_dir, fallback_settings=None):
        """
        [카페 전용 파이프라인]
        최대 20개 태그, 카페 전용 인사말/슬로건, 본문 하단 태그 부착.
        """
        if fallback_settings is None: fallback_settings = {}
        user_settings = CafePipeline._get_settings(app_data_dir)
        if not user_settings: user_settings = fallback_settings

        # 1. 초기 클리닝
        content = content.replace('**', '')
        for marker in ['[제목]', '제목:', '**제목:**', '[본문]', '본문:', '**본문:**', '[태그]', '태그:', '**태그:**']:
            content = content.replace(marker, '').strip()

        # 본문 내 AI 해시태그 뭉치 제거
        content = re.sub(r'\n\s*(#[\w가-힣]+\s*)+', '\n', content).strip()
        content = re.sub(r'(#[\w가-힣]+\s*){3,}', '', content).strip()

        # 2. 인사말 결합
        cafe_intro = user_settings.get('cafe_first_sentence', '').strip()
        content = CafePipeline._clean_intro_overlap(cafe_intro, content)
        if cafe_intro:
            content = f"{cafe_intro}\n\n{content}"

        # 3. 슬로건 결합
        cafe_slogan = user_settings.get('cafe_slogan', '').strip()
        if cafe_slogan:
            slogan_clean = cafe_slogan.split('#')[0].strip()
            if slogan_clean and slogan_clean not in content:
                content = f"{content}\n\n{cafe_slogan}"

        # 4. 태그 병합 (최대 20개)
        raw_fixed = user_settings.get('cafe_fixed_tags') or \
                    user_settings.get('fixed_tags') or \
                    user_settings.get('video_tags', [])
                    
        if isinstance(raw_fixed, str):
            fixed_tags = [t.strip() for t in raw_fixed.split(',') if t.strip()]
        else:
            fixed_tags = raw_fixed if isinstance(raw_fixed, list) else []
            
        seen_tags = set()
        final_tags = []

        def clean_tag(t):
            return t.replace('#', '').strip() if t else ""

        for t in (ai_tags or []):
            ct = clean_tag(t)
            if ct and ct not in seen_tags and len(final_tags) < 20:
                final_tags.append(ct)
                seen_tags.add(ct)
                
        for t in fixed_tags:
            ct = clean_tag(t)
            if ct and ct not in seen_tags and len(final_tags) < 20:
                final_tags.append(ct)
                seen_tags.add(ct)
                
        print(f"🏷️ [CAFE Pipeline] 병합 완료 (총 {len(final_tags)}개)")

        # 5. 본문 하단에 태그 부착
        existing_tags = set(re.findall(r'#([\w가-힣]+)', content))
        new_tags = [t for t in final_tags if t not in existing_tags]
        
        if new_tags:
            tag_str = " ".join([f"#{t}" for t in new_tags])
            content = f"{content}\n\n{tag_str}\n\n"

        return content, final_tags
