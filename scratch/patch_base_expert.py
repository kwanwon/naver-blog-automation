# -*- coding: utf-8 -*-
import re

with open('modules/ai_experts/base_expert.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# _get_weather_advice 가 처음으로 나타나는 위치 찾기
# 1160라인 부근의 def _get_weather_advice
start_keyword = "    def _get_weather_advice"
start_idx = content.find(start_keyword)

# _search_brave 가 나타나는 위치 찾기
end_keyword = "    def _search_brave"
end_idx = content.find(end_keyword)

if start_idx == -1 or end_idx == -1:
    print(f"Error: Keywords not found. start_idx={start_idx}, end_idx={end_idx}")
    exit(1)

# 교체할 새로운 코드 정의
replacement_code = """    def _refine_location(self, location):
        \"\"\"주소를 읍/면/동/구/시/군 단위로 단순화하여 날씨 조회 성공률 극대화\"\"\"
        if not location:
            return "서울"
        location = re.sub(r'\\(.*?\\)', '', location).strip()
        parts = location.split()
        for p in reversed(parts):
            p_clean = p.strip()
            if p_clean.endswith(('읍', '면', '동', '구', '시', '군')):
                return p_clean
        return parts[-1] if parts else "서울"

    def _get_weather_advice(self, temp_val, wsd_val=None, rain_alert="", weather_desc=""):
        \"\"\"온도에 따른 심플하고 다정한 체감 기상 묘사\"\"\"
        try:
            temp = float(temp_val)
            if temp < 5:
                return "매우 쌀쌀하고 추운 날씨"
            elif temp < 12:
                return "쌀쌀함이 느껴지는 날씨"
            elif temp < 18:
                return "선선한 바람이 부는 날씨"
            elif temp < 25:
                return "포근하고 활동하기 좋은 날씨"
            else:
                return "조금 더운 기운이 느껴지는 날씨"
        except:
            return "편안하고 기분 좋은 날씨"

    def _get_time_of_day_name(self, hour):
        \"\"\"시간대에 따른 자연스러운 한국어 명칭 반환\"\"\"
        if hour < 6: return "새벽"
        elif hour < 11: return "오전"
        elif hour < 14: return "점심 시간"
        elif hour < 17: return "오후"
        elif hour < 21: return "저녁"
        else: return "밤"

    def _get_naver_weather(self, location, delta_days=0):
        \"\"\"네이버 검색을 통해 실시간/예보 기상 정보 파싱 추출\"\"\"
        import urllib.request
        import urllib.parse
        
        refined = self._refine_location(location)
        query = f"{refined} 날씨"
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?query={encoded_query}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='replace')
            
            # 날씨 전용 블록 추출
            weather_block = html
            if delta_days == 0:
                m_block = re.search(r'class="blind">오늘의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)
            elif delta_days == 1:
                m_block = re.search(r'class="blind">내일의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)
            elif delta_days == 2:
                m_block = re.search(r'class="blind">모레의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)

            # 온도 추출
            temp = "?"
            if delta_days in [1, 2]:
                am_temp = None
                pm_temp = None
                m_am = re.search(r'오전.*?class="temperature_text">.*?예측 온도</span>\\s*(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)', weather_block, re.DOTALL)
                if m_am:
                    am_temp = m_am.group(1).strip()
                else:
                    m_am_alt = re.search(r'오전.*?class="temperature_text">.*?(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)', weather_block, re.DOTALL)
                    if m_am_alt:
                        am_temp = m_am_alt.group(1).strip()
                        
                m_pm = re.search(r'오후.*?class="temperature_text">.*?예측 온도</span>\\s*(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)', weather_block, re.DOTALL)
                if m_pm:
                    pm_temp = m_pm.group(1).strip()
                else:
                    m_pm_alt = re.search(r'오후.*?class="temperature_text">.*?(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)', weather_block, re.DOTALL)
                    if m_pm_alt:
                        pm_temp = m_pm_alt.group(1).strip()
                
                if am_temp:
                    temp = am_temp
                elif pm_temp:
                    temp = pm_temp
            else:
                patterns = [
                    r'class="temperature_text">.*?현재 온도</span>\\s*(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)',
                    r'class="temperature_text">.*?(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)',
                    r'class="todaytemp">(-?\\d+(?:\\.\\d+)?)',
                    r'class="current">(-?\\d+(?:\\.\\d+)?)(?:\\xb0|<span)'
                ]
                for p in patterns:
                    m = re.search(p, weather_block, re.DOTALL)
                    if m:
                        temp = m.group(1).strip()
                        break

            # 미세먼지 정보 추출
            dust_info = ""
            if delta_days == 0:
                dust_patterns = [
                    r'미세먼지</span>\\s*<span class="txt">(.*?)</span>',
                    r'미세먼지.*?<span class="txt">(.*?)</span>',
                    r'<dt class="term">미세먼지</dt>\\s*<dd class="desc">(.*?)</dd>'
                ]
                for p in dust_patterns:
                    dust_match = re.search(p, html, re.DOTALL)
                    if dust_match:
                        val = dust_match.group(1).strip()
                        if val and len(val) < 10:
                            dust_info = f", 미세먼지: {val}"
                            break

            # 날씨 상태 추출
            weather_desc = ""
            desc_patterns = [
                r'class="weather before_slash">(.*?)</span>',
                r'class="weather">(.*?)</span>',
                r'<p class="summary">.*?<span class="weather[^>]*">(.*?)</span>'
            ]
            for p in desc_patterns:
                desc_match = re.search(p, weather_block, re.DOTALL)
                if desc_match:
                    val = desc_match.group(1).strip()
                    if val and len(val) < 15:
                        weather_desc = val
                        break

            if temp == "?": return None
            
            advice = self._get_weather_advice(temp, weather_desc=weather_desc)
            label_map = {0: "현재", 1: "내일 예보", 2: "모레 예보"}
            time_label = label_map.get(delta_days, "예보")
            return f"[{refined} {time_label}] 기온: {temp}도{dust_info}. ({advice})"
        except Exception as e:
            print(f"네이버 날씨 스크래핑 실패: {e}")
            return None

    def _build_weather_hook_message(self, location, is_forecast, platform='blog', target_time=None, delta_days=0):
        \"\"\"AI에게 전달할 날씨 훅 메시지 생성 (특정 시간 날씨 인사 생략 락 & 1~2문장 극단적 초간단 팩트 락)\"\"\"
        from datetime import datetime, timedelta
        import logging
        logger = logging.getLogger("BaseExpert")
        
        now = datetime.now()
        target_hour = now.hour
        
        # 1. 예약 시간이 유효하게 있는지 파악
        has_reservation = False
        if target_time:
            try:
                target_hour = int(target_time.split(':')[0])
                has_reservation = True
            except Exception as e:
                logger.error(f"_build_weather_hook_message target_time ({target_time}) 파싱 중 오류: {e}")
                target_hour = now.hour
        
        # 2. [날씨 인사 여부 결정 락 (Lock) 적용]
        # - 예약 시간이 아예 없는 경우 (실시간 포스팅)
        # - 예약 시간이 있고, 아침 8시 이전(예: 07시) 또는 오전 10시 초과 오후 16시 미만(예: 13시)인 경우
        # ⚠️ 위 경우에는 날씨 수집 성공 여부와 무관하게 날씨 인사를 100% 생략(Skip)하며 날씨 없이 시작합니다.
        should_skip_weather = True
        if has_reservation:
            # 오전 8시 ~ 10시 (오전형) 또는 오후 16시 ~ 21시 (오후/저녁형)에만 날씨 안부를 허용함
            if (8 <= target_hour <= 10) or (16 <= target_hour <= 21):
                should_skip_weather = False
                
        # 3. 주소 단순화 전처리 적용
        refined_location = self._refine_location(location)
        
        # 4. 날씨가 필요한 시간대이고 날씨 수집을 진행해야 하는 경우
        weather_info = None
        if not should_skip_weather:
            # (1) 기상청 API 시도
            for attempt in range(1, 3):
                try:
                    weather_info = self._get_kma_weather(refined_location, delta_days=delta_days, target_hour=target_hour)
                    if weather_info:
                        break
                except Exception as kma_err:
                    logger.warning(f"KMA Weather attempt {attempt} failed: {kma_err}")
            
            # (2) 기상청 API 실패 시 네이버 스크래핑 시도
            if not weather_info:
                try:
                    weather_info = self._get_naver_weather(refined_location, delta_days=delta_days)
                except Exception as scrap_err:
                    logger.error(f"Naver Weather Scraping failed: {scrap_err}")

        # 5. 날씨 인사를 건너뛰어야 하거나, 기상 수집 정보가 없을 때: "날씨 없이 시작" 지침 강제 주입
        if should_skip_weather or not weather_info:
            return \"\"\"
[System: 날씨 정보 미제공 - 날씨 인사 생략 지침 ⭐⭐⭐⭐⭐]
⚠️ 중요: 기상 정보가 제공되지 않았거나, 현재 포스팅 시간대(예: 예약 없음, 13시, 07시 등)의 정책에 따라 도입부 날씨 인사를 완전히 생략해야 하는 상황입니다.
1. **[도입부 날씨 언급 절대 금지]**: 첫 도입부에서 기온(도수), 미세먼지, 하늘 상태(구름, 맑음, 비 등), 혹은 날씨나 안부와 관련된 어떠한 표현(예: "비가 오네요", "쌀쌀하네요", "선선하네요", "따뜻하네요" 등)도 **100% 절대 쓰지 마십시오**.
2. **[고정된 단 한 문장의 깔끔한 인사말]**: 포스팅의 맨 첫 도입부는 반드시 오직 다음의 정확히 지정된 다정한 한 문장으로만 시작하고 마침표를 찍으세요.
   👉 \\"안녕하세요! 오늘도 기분 좋은 하루 보내고 계신가요?\\"
3. **[첫 문단 단독 구성 및 전환]**: 위의 한 문장으로 첫 도입부 문단을 깔끔하게 마치고, 즉시 줄바꿈(엔터)을 하여 새로운 문단에서 오늘의 본문 지식/정보 콘텐츠를 신선하게 열어가십시오.
4. **[체육관/수련 억지 전개 완전 금지]**: 실내 도장 안에서의 수련, 아이들의 땀방울, 활기찬 움직임 등 도입부와 엮어서 작성하는 AI 말투의 어색한 결합 문장을 첫머리에 **100% 쓰지 마십시오**.
\"\"\"

        # 6. 날씨가 필요한 시간대이고 기상 수집에 완벽히 성공했을 때: "초간단 날씨 인사말" 지침 주입
        target_date_str = (now + timedelta(days=delta_days)).strftime("%m월 %d일")
        time_of_day = self._get_time_of_day_name(target_hour)
        
        return f\"\"\"
[System: 독자 시점의 당일({{target_date_str}}) 날씨 및 시간 정보]
- 지역명(위치): {{refined_location}}
- 시간대: {{time_of_day}}
- 상세 데이터: {{weather_info}}
 
⚠️ [초간단 날씨 인사말 강제 가이드라인 - 매우 엄격 ⭐⭐⭐⭐⭐]
1. **[첫 문단 - 초간단 날씨 안부 1~2문장 완성]**: 제공된 날씨 데이터 속의 실제 기온과 하늘상태 정보만을 있는 그대로 정직하게 활용하여, 첫 도입부에 오직 딱 1~2문장으로만 깔끔하고 다정한 날씨 안부 인사를 작성하고 마침표와 함께 첫 문단을 즉시 종결하십시오.
   - 작성 예시: "오늘 {{refined_location}}은 기온이 [상세 데이터 속 기온]도에 하늘이 [상세 데이터 속 날씨 상태]인 {{time_of_day}}이네요. 가벼운 안부를 나누며 기분 좋은 하루 보내시길 바랍니다."
   - 🚨 [가짜 수치 날조 금지]: 예시의 괄호 부분은 반드시 상세 데이터에 제공된 실제 사실 수치(예: {{weather_info}} 에 적힌 수치)로 치환해야 하며, 임의의 가짜 수치(예: 15도, 19도 등)를 지어내어 날조하는 행위를 100% 절대 금지합니다.
2. **[어색한 전개 및 억지 결합 원천 배제]**: 날씨 문단 내에서 혹은 본문 첫머리에서 실내 도장 묘사, 체육관, 학원, 건강 멘트, 혹은 점퍼를 챙기라는 등의 상투적이고 인위적인 교육 멘트를 작성하여 본문과 엮는 행위를 **100% 원천 전면 금지**합니다. (예: "실내 도장 안에서는 언제나...", "수련생들이 땀방울을..." 같은 문장을 날씨 문단에 절대 쓰지 마세요.) 날씨 인사는 순수한 팩트 날씨 묘사로만 짧게 문단을 끝내야 합니다.
3. **[날씨-본문 완벽 분리 및 연결 단어 전면 금지]**: 날씨 인사가 끝난 뒤 새로운 문단(본문)이 시작될 때, 이전의 날씨 인사와 엮으려는 어떠한 기온, 날씨 관련 연결어(예: "이런 날씨 속에서", "선선한 날씨 속에", "이런 기온에도" 등)를 본문 첫 문장에 쓰는 행위를 100% 원천 금지합니다. 본문 첫 문장은 오직 오늘의 독립된 지식/정보 주제로 새롭게 시작하십시오.
4. **[호칭 언급 절대 금지]**: 첫 도입부에서 '부모님,' 또는 '학부모님,' 등의 호칭을 불러 대화하듯 독자를 지칭하는 자동화 AI 말투를 100% 원천 금지합니다. 호칭을 완전히 생략하고 반갑고 신선한 인간적인 말투로만 작성하세요.
\"\"\"
"""

# 파일 내용 교체
patched_content = content[:start_idx] + replacement_code + content[end_idx:]

with open('modules/ai_experts/base_expert.py', 'w', encoding='utf-8') as f:
    f.write(patched_content)

print("Patching completed successfully!")
