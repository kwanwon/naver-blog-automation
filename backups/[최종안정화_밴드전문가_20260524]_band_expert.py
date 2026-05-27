# -*- coding: utf-8 -*-
import logging
import re
from .base_expert import BaseAIExpert
from config.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class BandExpert(BaseAIExpert):
    """
    네이버 밴드 전용 AI 전문가.
    
    [포스팅 그룹 분류]
    - 그룹A (짧고 간결, 사진/영상 목적): platform='drive_auto', 'manual_topic'
    - 그룹B (C안 5:5 톤, 수련 내용 중심): platform='band'
    """

    def __init__(self, use_dummy=False):
        super().__init__(use_dummy)

    def _get_gym_identity(self, user_settings):
        """밴드 전용 종목 인식 및 정체성 부여 (UI 설정 우선)"""
        # 1. 사용자가 UI에서 설정한 종목이 있는지 먼저 확인 (최우선)
        gym_sport = user_settings.get('gym_sport', '').strip()
        
        if not gym_sport:
            # 2. 설정이 없는 경우 기존 로직(태그/슬로건 기반 유추) 수행
            search_text = f"{user_settings.get('video_tags', '')} {user_settings.get('cafe_first_sentence', '')} {user_settings.get('blog_slogan', '')}"
            sports_keywords = ['합기도', '태권도', '유도', '검도', '주짓수', '복싱', '킥복싱', '필라테스', '요가', '음악줄넘기', '줄넘기', '크로스핏', '헬스']
            found_sports = [s for s in sports_keywords if s in search_text]
            
            if found_sports:
                gym_info = " 및 ".join(list(dict.fromkeys(found_sports))[:2]) + " 전문 교육관"
            else:
                gym_info = "체육 전문 교육관"
        else:
            gym_info = f"{gym_sport} 전문 교육관"
            
        return f"\n\n[당신의 정체성]\n- 당신은 {gym_info}의 관장입니다. 본인이 지도하는 종목({gym_info})의 전문성을 최우선으로 하되, 타 종목(예: 태권도 등)과의 비교가 필요한 경우 본 종목의 장점을 부각하기 위한 대조 목적으로는 언급이 가능합니다."

    def _band_build_weather_hook_message(self, location, is_forecast, target_hour=None, delta_days=0):
        """밴드 전용 날씨 훅 (KMA 상세 정보 + 네이버 미세먼지 결합)"""
        # is_forecast가 True(내일 예보)인 경우, 날짜 차이를 1일 더해줍니다.
        effective_delta = delta_days + 1 if is_forecast else delta_days
        
        kma_info = self._get_kma_weather(location, delta_days=effective_delta, target_hour=target_hour)
        naver_info = self._get_naver_weather(location, delta_days=effective_delta)
        
        # 미세먼지 정보만 추출 (네이버 데이터에서)
        dust_info = ""
        if naver_info and "미세먼지" in naver_info:
            match = re.search(r'미세먼지:\s*([^,)]+)', naver_info)
            if match:
                dust_info = f", 미세먼지: {match.group(1)}"
        
        combined_info = kma_info if kma_info else naver_info
        if combined_info and dust_info and "미세먼지" not in combined_info:
            combined_info += dust_info
            
        if not combined_info:
            return ""
        return f"\n[System: 실시간 날씨 상세 정보]\n- 데이터: {combined_info}"

    def _band_readability_filter(self, text):
        """
        밴드 전용 가독성 필터.
        - 온점(.)을 기준으로 한 줄바꿈을 적용합니다.
        - 23자 단어잘림방지 모바일 최적화 한 줄바꿈을 전 구간에 적용합니다.
        """
        if not text:
            return ""
        
        # 1. 먼저 문장 단위로 온점(.)을 기준으로 분할
        lines = []
        raw_paragraphs = text.split('\n')
        for para in raw_paragraphs:
            if not para.strip():
                lines.append("")
                continue
            
            # 온점(.) 뒤에 줄바꿈이 일어날 수 있도록 분할
            sentences = re.split(r'\.\s+', para)
            for i, sent in enumerate(sentences):
                sent_str = sent.strip()
                if not sent_str:
                    continue
                # 온점이 잘려 나갔으므로 마지막 문장이 아니거나 원래 온점이 있었다면 온점 복구
                if i < len(sentences) - 1 or sent.endswith('.'):
                    if not sent_str.endswith('.'):
                        sent_str += '.'
                
                # 2. 23자 기준으로 단어가 짤리지 않게 줄바꿈 처리
                words = sent_str.split()
                current_line = []
                current_len = 0
                wrapped_sentences = []
                
                for word in words:
                    word_len = len(word)
                    if current_len + word_len + (1 if current_line else 0) <= 23:
                        current_line.append(word)
                        current_len += word_len + (1 if current_line else 0)
                    else:
                        if current_line:
                            wrapped_sentences.append(" ".join(current_line))
                        current_line = [word]
                        current_len = word_len
                if current_line:
                    wrapped_sentences.append(" ".join(current_line))
                
                lines.append("\n".join(wrapped_sentences))
                
        return "\n".join(lines)

    def generate_band_content(self, topic, platform='band', task_type='regular', target_time=None, delta_days=0):
        """
        네이버 밴드 포스팅 본문 생성 (유형 1 & 유형 2 이원화 적용)
        
        - 유형 1 (platform='band'): 정보 지식 공유 (글자수 적용, 실시간/예보 날씨 적극 연동, 모바일 가독성)
        - 유형 2 (platform='drive_auto' or 'manual_topic'): 간결한 수련 현장 기록 (100~130자, 현실적 관찰자 톤, 과장 전면 배제)
        """
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상 원천 차단
        self._reload_all_settings()
        
        # ─── 0. 주제 및 카테고리 파싱 (수동/자동 모드 대응) ────────────────
        display_category = ""
        display_topic = topic
        
        is_group_a = platform in ('drive_auto', 'manual_topic')
        
        if is_group_a:
            # 패턴 1: [3시부] 주제 (수동 주제 포스팅)
            match = re.match(r'^\[(.*?)\]\s*(.*)$', topic)
            if match:
                display_category = match.group(1).strip()
                display_topic = match.group(2).strip()
            else:
                # 패턴 2: 드라이브 자동 감지용 긴 주제
                # 예: "한국체대 라이온짐 4시부 수련\n수련내용: 낙법"
                if "수련내용:" in topic:
                    parts = topic.split("수련내용:")
                    display_topic = parts[1].strip()
                    # 앞부분에서 부 타임 추출
                    folder_match = re.search(r'(\d+시부|선수부|시범단|행사|합숙)', parts[0])
                    if folder_match:
                        display_category = folder_match.group(1)
                else:
                    # 기타: 주제 자체가 부 타임인 경우
                    folder_match = re.search(r'(\d+시부|선수부|시범단|행사|합숙)', topic)
                    if folder_match:
                        display_category = folder_match.group(1)
                        display_topic = topic.replace(display_category, "").strip(" [](),.")
        
        # 파싱 결과가 없으면 기본값 유지
        if not display_category: display_category = "수련"
        if not display_topic: display_topic = "오늘의 수련"

        # ─── 1. 기본 설정 및 훅 준비 ─────────────────────────────────────
        settings = self._load_settings()
        user_settings = self._load_user_settings()

        # 지역 정보 동적 추출 (우선순위: UI설정 > 주소 > 태그)
        weather_loc = settings.get('weather_location', '').strip()
        
        if not weather_loc:
            address = user_settings.get('address', '')
            if address:
                addr_parts = address.split()
                weather_loc = addr_parts[1] if len(addr_parts) >= 2 else addr_parts[0]
            
            if not weather_loc:
                tags = user_settings.get('blog_tags', '')
                if tags:
                    first_tag = tags.split(',')[0].strip()
                    weather_loc = re.sub(r'(합기도|체육관|태권도|유도|검도|스포츠|격투기)', '', first_tag).strip()
        
        if not weather_loc:
            weather_loc = '우리 동네'
            
        # 7단계 시간대 및 날짜 정보 구성
        now_dt = datetime.now()
        days_ko = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        time_name = self._get_time_of_day_name(now_dt.hour)

        # 예약 시각에서 시간(hour) 추출
        target_hour = None
        if target_time:
            try:
                h_match = re.search(r'(\d+)', str(target_time))
                if h_match:
                    target_hour = int(h_match.group(1))
                    time_name = self._get_time_of_day_name(target_hour)
            except:
                pass
        
        is_forecast = self._check_is_forecast(target_time)

        # 🟢 날씨 및 뉴스 훅 정보 수집 (유형 1 전용)
        weather_hook = ""
        news_hook = ""
        evening_hook = ""
        
        if not is_group_a:
            # 1번 유형은 실시간 및 예보 날씨를 적극적으로 수집
            effective_delta = delta_days + 1 if is_forecast else delta_days
            try:
                weather_hook = self._band_build_weather_hook_message(weather_loc, is_forecast=is_forecast, target_hour=target_hour, delta_days=effective_delta)
            except Exception as w_err:
                logger.warning(f"날씨 훅 수집 실패 (Fallback 우회 예정): {w_err}")
                weather_hook = ""
                
            if task_type == 'morning':
                topic = "상쾌한 아침 인사와 희망찬 명언, 그리고 오늘 날씨 안내"
            elif task_type == 'closing':
                topic = "하루 마감 인사와 명언, 그리고 내일의 상세한 날씨 예보"
                evening_hook = self._build_evening_hook_message()
            else:
                # 오후/일반 포스팅인 경우 뉴스 훅 연동
                try:
                    news_hook = self._build_news_hook_message(platform=platform)
                except:
                    pass

        # ─── 2. 분기별 작성 지침 및 프롬프트 빌드 ─────────────────────────
        max_tokens = 600
        
        identity_rules = self._get_gym_identity(user_settings)
        external_rules = self._get_common_system_rules(platform=platform)
        
        if is_group_a:
            # 📌 [유형 2] 간결한 현장 기록용 지침 (극단적 초간결, AI 냄새 완전 배제, 현실적 관찰자 톤)
            max_tokens = 400
            
            system_message = f"""당신은 아이의 수련 과정을 묵묵히 관찰하고 보고하는 [성숙한 교육관의 동반자 관장님]입니다.
{identity_rules}

[작성 목적: 유형 2 - 수련 현장 기록]
- 오직 오늘 진행된 수련내용을 부모님께 간단하고 사실 중심으로 보고하는 컴팩트한 기록 글입니다.
- AI 특유의 장황함이나 홍보성 멘트, 유치한 가상 칭찬은 전면 차단합니다.
- 모바일 밴드 폰 화면에서 가독성이 좋도록 **한 개 문단(공백 포함 100~130자 내외)**으로 아주 컴팩트하게 작성하세요.

[절대 엄수 사항 - 과장적인 언어 전면 금지 🚫]
- **감탄 및 미화어 절대 금지**: "굉장했어요", "대단해요", "정말 대단합니다", "송골송골", "땀방울", "웃음꽃", "감동을 주었네요", "대견하다", "자랑스럽다", "기특하다", "대단하다", "열기가 대단하네요" 등 유치하거나 인위적인 수식어는 절대 쓰지 마세요.
- **현실적이고 담백한 관찰**: "차분하게 연습했습니다", "서로 격려하며 안전하게 마쳤습니다", "끝까지 최선을 다하는 모습이 보기 좋았습니다", "기분 좋게 미소 지으며 귀가했습니다" 등 실제 관장님이 옆에서 묵묵히 지켜보고 쓴 현실적이고 자연스러운 멘트를 작성하세요.

[출력 형식 제한]
- **AI는 오직 [본문]의 알맹이 본문 내용만 작성합니다.**
- 해시태그, 첫문장(인사말), OO부 수련 완료 멘트, 사진 화질 양해 문구 등은 파이프라인에서 자동으로 조합하므로 **본문 내용에 절대 포함하지 마세요.**
- 카테고리(부 타임) 머리글이나 제목 마커도 절대 사용하지 마세요.

[공통 시스템 규칙]
{external_rules}
"""
            base_prompt = f"""[주제(수련내용): {display_topic}]
위 수련 내용을 활용하여, 학부모님께 사실 그대로 담백하게 보고하는 유형 2 본문을 작성하세요.

[출력 형식]
본문: 수련내용을 자연스럽게 엮은 한 개 문단 (공백 포함 100~130자 이내). 과장된 표현 없이 극단적으로 깔끔하고 정제된 관찰 일기 형태로 작성하세요.
태그: 본문 내용과 관련된 키워드 5개 (예: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5)
"""

        else:
            # 📌 [유형 1] 정보 지식 공유용 지침 (주제 중심, 날씨 반영, 모바일 가독성)
            max_tokens = 800
            
            # 날씨 정보 연동 및 Fallback 지침 (선택지 C)
            weather_instruction = ""
            if weather_hook:
                weather_instruction = f"""- [System: 실시간/예보 날씨 정보]: {weather_hook}
- 위 기상 수치(기온, 미세먼지 등)를 본문 도입부에 정확히 반영하여 자연스러운 날씨 안부 인사를 건네세요.
"""
            else:
                weather_instruction = """- 현재 상세 날씨 데이터가 없거나 일시적 통신 지연 상태입니다. 
- 절대 거짓 기온이나 날씨를 지어내어 쓰지 마세요(환각 방지). 대신 "아이들과 땀 흘려 운동하기 참 기분 좋은 계절이네요" 등 계절과 절기에 걸맞은 정겹고 다정한 일반 안부 인사로 첫머리를 자연스럽게 시작하세요. (선택지 C 완벽 반영)
"""

            system_message = f"""당신은 아이의 성장을 함께 고민하는 전문 교육관의 [다정하고 유익한 관장님]입니다.
{identity_rules}

[작성 목적: 유형 1 - 정보 지식 공유]
- 학부모님께 실질적으로 유익한 교육 정보, 건강 상식(성장, 두뇌 발달, 자신감, 기초 체력 등)을 다정하고 품격 있게 설명하는 포스팅입니다.
- 가르치려는 태도 대신 관장님의 따뜻한 교육 철학을 나누는 성숙한 어조를 유지하세요.
- **모바일 스마트폰 화면에서 스크롤하며 읽기 좋게 가독성을 극대화하세요.**
  - 3~4문장을 묶어 하나의 단락을 만들고, 단락과 단락 사이에는 빈 줄(더블 엔터)을 두어 시각적 여백을 확보하세요.
  - 한 문장이 너무 장황하게 늘어지지 않고 모바일 화면에서 한눈에 들어오도록 깔끔하게 서술하세요.

[날씨 및 안부 반영 지침 - 선택지 C]
{weather_instruction}

[출력 형식 제한]
- **AI는 오직 [본문] (날씨인사 + 지식공유 본문) 내용만 작성합니다.**
- 최상단 고정 첫문장(인사말)과 하단의 체육관 슬로건 및 해시태그는 파이프라인에서 칼같이 자동 조립되므로 **절대 글에 포함하지 마세요.**
- 제목 마커나 불필요한 번호 지칭('첫째', '둘째' 등)은 쓰지 마세요.

[말투 및 종결어미]
- 다정한 구어체(~해요, ~네요, ~이지요)와 신뢰감을 주는 격식체(~합니다, ~습니다)를 [5:5 비율]로 균형 있게 섞어서 사용하세요.

[공통 시스템 규칙]
{external_rules}
"""
            base_prompt = f"""[주제: {topic}]
위 주제를 바탕으로 유익한 교육 정보와 날씨 안부 인사가 결합된 유형 1 본문을 정성껏 작성해 주세요.

[출력 형식]
본문: 도입부 날씨/계절 인사로 시작하여 유익한 지식을 전하는 모바일 최적화 본문 (단락 구분 적용, 공백 포함 200~250자 내외).
태그: 주제와 관련된 생성 키워드 5개 (예: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5)
"""

        logger.info(f"[BandExpert] 유형={'유형 2' if is_group_a else '유형 1'}, platform={platform}, 주제={topic}")

        # ─── 3. 모델 순회 및 생성 ──────────────────────────────────────
        models_to_use = self.selected_models
        for step in range(len(models_to_use)):
            if self.stop_event.is_set(): return None
            model_idx = (self.current_model_index + step) % len(models_to_use)
            model_name = models_to_use[model_idx]

            if not self._check_daily_limit(model_name): continue

            try:
                provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
                if provider == "openai":
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": base_prompt}],
                        temperature=0.7, max_tokens=max_tokens
                    )
                    raw_content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    raw_content = self._generate_with_gemini(model_name, system_message, base_prompt)
                else: continue

                if raw_content:
                    # [파싱] 본문과 태그 분리
                    title, body, tags = self._parse_content(raw_content)
                    
                    if not body and title:
                        logger.info(f"ℹ️ [BandExpert] 마커 없는 본문 감지 -> 제목을 본문으로 사용")
                        body = title
                        title = f"[{platform}] {display_topic}"
                    
                    if not body or len(body.strip()) < 10 or re.match(r'^[\s,./]+$', body):
                        logger.warning(f"⚠️ [BandExpert] ({model_name}) 비정상 본문 감지 -> 다음 모델 시도")
                        continue
                    
                    # [후처리 안정성 필터]
                    body = self._apply_stability_filter(body, platform)
                    
                    # 수동/실시간 감지(유형 2) 정제
                    if is_group_a:
                        # 대괄호 패턴 제거: [선수부], [[선수부]] 등
                        body = re.sub(r'^\[+.*?\]+\s*', '', body).strip()
                        body = re.sub(r'^(?:본문|수련내용|내용|주제|카테고리|폴더명)[:\s]*', '', body, flags=re.IGNORECASE)
                        body = re.sub(rf'^{re.escape(display_category)}\s*입니다\.\s*', '', body)
                        body = body.replace("수련내용:", "").replace("수련내용 :", "").strip()
                        
                        # 유형 2에 맞추어 과장 단어 재차 확실하게 검열(보안 필터)
                        exaggerations = ["굉장", "대단", "송골송골", "땀방울", "웃음꽃", "기특", "대견", "자랑", "감동"]
                        for word in exaggerations:
                            body = body.replace(f"정말 {word}", "차분히")
                            body = body.replace(f"너무 {word}", "안전하게")
                    else:
                        # 유형 1 가독성 정돈 필터
                        body = self._band_readability_filter(body)
                    
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)

                    return {
                        "title": f"[{platform}] {topic}",
                        "content": body,
                        "tags": tags,
                        "model": model_name
                    }
            except Exception as e:
                logger.error(f"밴드 생성 오류 ({model_name}): {e}")
                continue

        # 모든 모델 실패 시의 Fallback 알맹이 구성
        if is_group_a:
            fallback_body = f"오늘 {display_topic} 동작을 차분하게 수련해 보았습니다. 진지하게 최선을 다하는 눈빛이 보기 좋았습니다. 건강하게 성장할 아이들을 응원합니다."
        else:
            fallback_body = f"건강한 신체에 건강한 정신이 깃든다는 말처럼, 우리 아이들은 매일 땀 흘리며 마음의 근육을 키워가고 있습니다. 성장을 향한 소중한 여정에 따뜻한 격려를 보내주세요."

        return {
            "title": f"[{platform}] {topic}",
            "content": fallback_body,
            "tags": "수련,성장,건강,열정,화이팅,합기도,유아체육,어린이운동,실전무술,체육관",
            "model": "fallback"
        }
