import os
import json
import re

class BandPipeline:
    @staticmethod
    def _get_settings(app_data_dir):
        user_settings = {}
        try:
            # 1. Flet UI의 주요 설정 파일인 app_settings.json 로드 시도
            app_settings_path = os.path.join(app_data_dir, 'config', 'app_settings.json')
            if os.path.exists(app_settings_path):
                with open(app_settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    print(f"📖 [BandPipeline] app_settings.json 로드 성공 (키 수: {len(user_settings)})")
            
            # 2. 레거시 user_settings.txt 가 있다면 누락된 설정 병합
            txt_path = os.path.join(app_data_dir, 'config', 'user_settings.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    txt_settings = json.load(f)
                    for k, v in txt_settings.items():
                        if k not in user_settings:
                            user_settings[k] = v
        except Exception as e:
            print(f"⚠️ [BandPipeline] 설정 파일 로드 실패: {e}")
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
    def process(content, ai_tags, app_data_dir, mode='band', fallback_settings=None, folder_name=None):
        """
        [밴드 전용 파이프라인]
        1번 유형(지식)과 2번 유형(현장 기록)에 따라 지정된 포스팅 순서대로 칼같이 조립합니다.
        가독성을 극대화하여 폰 화면에서도 단락이 뭉치지 않고 여백이 정돈되어 보이게 처리합니다.
        
        - 유형 1 (mode='band'): [첫문장] ➡️ [AI 본문(날씨안부+지식)] ➡️ [마지막 슬로건] ➡️ [해시태그]
        - 유형 2 (mode!='band'): [첫문장] ➡️ "오늘 {folder_name} 수련을 마쳤습니다." ➡️ [팩트 본문(100자)] ➡️ [양해문구] ➡️ [해시태그]
        """
        # 0. ai_tags가 문자열(str)로 넘어온 경우 글자 쪼개짐 방지를 위해 안전하게 파싱
        if isinstance(ai_tags, str):
            ai_tags = [t.strip() for t in re.split(r'[#,\s]+', ai_tags) if t.strip()]
        elif not isinstance(ai_tags, list):
            ai_tags = []

        if fallback_settings is None: fallback_settings = {}
        user_settings = BandPipeline._get_settings(app_data_dir)
        if not user_settings: user_settings = fallback_settings

        # 1. 초기 텍스트 정제 (AI 마커 및 볼드 기호 제거)
        content = content.replace('**', '')
        for marker in ['[제목]', '제목:', '**제목:**', '[본문]', '본문:', '**본문:**', '[태그]', '태그:', '**태그:**']:
            content = content.replace(marker, '').strip()

        # 본문 내 AI 해시태그 뭉치 잔재 제거
        content = re.sub(r'\n\s*(#[\w가-힣]+\s*)+', '\n', content).strip()
        content = re.sub(r'(#[\w가-힣]+\s*){3,}', '', content).strip()

        # 2. 첫문장(인사말) 가져오기
        band_intro = user_settings.get('band_first_sentence', '').strip()
        content = BandPipeline._clean_intro_overlap(band_intro, content)

        # 3. 유형별 포스팅 최종 물리적 조립
        assembled_content = ""
        is_type_1 = (mode == 'band')

        if is_type_1:
            # 📌 [유형 1] 정보 지식 공유형 포스팅
            # 순서: 첫문장 -> AI 본문 -> 마지막 슬로건
            assembled_content = ""
            if band_intro:
                assembled_content += f"{band_intro}\n\n"
                
            # AI 본문 삽입 (문장 단위로 쪼개어 모바일 가독성 확보)
            sentences = [s.strip() for s in re.split(r'(?<=\.)\s+', content.strip()) if s.strip()]
            content_formatted = "\n\n".join(sentences)
            assembled_content += f"{content_formatted}"
            
            # 마지막 슬로건 처리 및 조립
            band_slogan = user_settings.get('band_slogan', '').strip()
            if band_slogan:
                # 밴드용 슬로건에서 연락처 및 문의 문구 제거
                slogan_clean = re.sub(r'(\d{2,3}[-\s]\d{3,4}[-\s]\d{4})', '', band_slogan).strip()
                slogan_clean = re.sub(r'(📞\s*)?문의\s*:\s*', '', slogan_clean).strip()
                if slogan_clean:
                    # 모바일 가독성을 위한 안전한 단락 여백 확보
                    assembled_content = assembled_content.rstrip() + f"\n\n{slogan_clean}"
        else:
            # 📌 [유형 2] 간결한 현장 기록형 포스팅
            # 순서: 첫문장 -> 오늘 OO부 수련을 마쳤습니다 -> 팩트 본문 -> 양해문구
            assembled_content = ""
            if band_intro:
                assembled_content += f"{band_intro}\n\n"
                
            # OO부 안내 멘트 조립
            display_folder = folder_name or "수련"
            # 만약 폴더명 끝에 '부'가 안 붙어있고 '시'나 '반' 등으로 끝난다면 그대로 씀
            if not display_folder.endswith(('부', '반', '팀', '단', '학습', '합숙', '행사')):
                # 숫자로 끝나는 경우(예: '3시')에만 '부'를 붙여줌
                if re.search(r'\d+$', display_folder) or display_folder.endswith('시'):
                    display_folder = f"{display_folder}부"
            
            assembled_content += f"오늘 {display_folder} 수련을 마쳤습니다.\n\n"
            
            # 팩트 본문 삽입 (과장 배제 초간결 + 23자 기준 단어 잘림 방지 1줄바꿈 + 온점(.) 1줄바꿈 필터 적용)
            import textwrap
            paragraphs = [p.strip() for p in re.split(r'(?<=\.)\s+', content.strip()) if p.strip()]
            
            wrapped_lines = []
            for para in paragraphs:
                # 23자 단위로 단어가 잘리지 않게 워드랩 수행
                wrapped = textwrap.wrap(para, width=23, break_long_words=False)
                wrapped_lines.extend(wrapped)
                
            content_formatted = "\n".join(wrapped_lines)
            assembled_content += f"{content_formatted}"
            
            # 양해문구(band_footer_notice) 조립 (사용자 설정 하단 안내문 - 1번 스샷 대응)
            band_footer = user_settings.get('band_footer_notice', '').strip()
            if band_footer:
                # 모바일 가독성을 위한 여백 적용
                assembled_content = assembled_content.rstrip() + f"\n\n{band_footer}"

        # 4. 태그 5:5 믹스 병합 처리 (고정 5개 + AI 5개 = 총 10개 완벽 구현)
        raw_hashtags = user_settings.get('band_hashtags') or \
                       user_settings.get('blog_tags') or \
                       user_settings.get('video_tags', '')
                       
        if isinstance(raw_hashtags, str):
            all_fixed_tags = [t.strip() for t in re.split(r'[#,\s]+', raw_hashtags) if t.strip()]
        else:
            all_fixed_tags = raw_hashtags if isinstance(raw_hashtags, list) else []

        from datetime import datetime
        day_seed = datetime.now().timetuple().tm_yday
        fixed_pool = []
        if all_fixed_tags:
            tag_count = len(all_fixed_tags)
            start_idx = (day_seed * 3) % tag_count
            for i in range(min(tag_count, 12)):
                fixed_pool.append(all_fixed_tags[(start_idx + i) % tag_count])
            
        seen_tags = set()
        ai_tags_selected = []
        fixed_tags_selected = []

        def clean_tag(t):
            if not t: return ""
            clean = re.sub(r'[#\s:：,，\.!@$%^&*()]', '', t)
            return clean.strip()

        # 1) AI 생성 태그에서 최대 5개 선택
        for t in ai_tags:
            ct = clean_tag(t)
            if ct and ct not in seen_tags and len(ai_tags_selected) < 5:
                ai_tags_selected.append(ct)
                seen_tags.add(ct)
        
        # 2) 고정 태그에서 최대 5개 선택
        for t in fixed_pool:
            ct = clean_tag(t)
            if ct and ct not in seen_tags and len(fixed_tags_selected) < 5:
                fixed_tags_selected.append(ct)
                seen_tags.add(ct)
                
        # 3) 고정 5개 + AI 5개 병합하여 최종 리스트 구성
        final_tags = ai_tags_selected + fixed_tags_selected
                
        # 4) 만약 중복 배제로 인해 합이 10개에 부족할 경우, 고정 전체 태그 풀에서 추가 보충하여 10개 충족
        if len(final_tags) < 10:
            for t in all_fixed_tags:
                ct = clean_tag(t)
                if ct and ct not in seen_tags and len(final_tags) < 10:
                    final_tags.append(ct)
                    seen_tags.add(ct)
                
        print(f"🏷️ [BAND Pipeline] 태그 5:5 믹스 완료 (최종 {len(final_tags)}개: AI {len(ai_tags_selected)}개 + 고정 {len(final_tags) - len(ai_tags_selected)}개)")

        # 5. 본문 하단에 해시태그 부착
        tag_line = " ".join([f"#{t}" for t in final_tags])
        
        if tag_line:
            # 모바일 폰에서도 해시태그가 깔끔하게 분리되어 노출되도록 넉넉한 2라인 여백 부여
            assembled_content = assembled_content.rstrip() + "\n\n" + tag_line
            print(f"✅ [BAND Pipeline] 조립 및 해시태그 부착 완료")

        return assembled_content.strip() + "\n\n", final_tags
