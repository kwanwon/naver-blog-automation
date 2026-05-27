import logging
import re
from .base_expert import BaseAIExpert
from config.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class CafeExpert(BaseAIExpert):
    def __init__(self, use_dummy=False):
        super().__init__(use_dummy)

    def _get_gym_identity(self, user_settings):
        """카페 전용 종목 인식 및 정체성 부여 (UI 설정 우선)"""
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
            
        return f"\n\n[당신의 정체성]\n- 당신은 {gym_info}의 관장입니다. 본인이 지도하는 종목({gym_info})의 전문성을 강조하되, 타 종목(예: 태권도 등)과의 차별점을 설명하기 위한 비교 목적으로는 언급이 가능합니다."

    def _cafe_build_weather_hook_message(self, location, is_forecast, target_hour=None, delta_days=0):
        """카페 전용 날씨 훅 (target_hour 지원)"""
        effective_delta = delta_days + 1 if is_forecast else delta_days
        
        # 🟢 [우선순위 1] 백그라운드 로컬 위젯 캐시 조회 (0.00초 극속도 복원)
        from modules.weather_cache_manager import WeatherCacheManager
        refined_location = self._refine_location(location)
        try:
            cached_info = WeatherCacheManager.get_cached_weather(refined_location, delta_days=effective_delta, target_hour=target_hour)
            if cached_info:
                logger.info(f"🎉 [CafeExpert] 로컬 날씨 캐시 히트 성공! 대기시간 0.00초: {cached_info}")
                return f"\n[System: 실시간 날씨 정보]\n- 상세: {cached_info}"
        except Exception as cache_err:
            logger.error(f"[CafeExpert] Weather cache lookup error (skipped): {cache_err}")
            
        weather_info = self._get_kma_weather(location, delta_days=effective_delta, target_hour=target_hour)
        if not weather_info:
            weather_info = self._get_naver_weather(location, delta_days=effective_delta)
        if not weather_info:
            return ""
        return f"\n[System: 실시간 날씨 정보]\n- 상세: {weather_info}"

    def _cafe_readability_filter(self, text: str) -> str:
        """카페 전용 가독성 필터 (AI 나열식 말투 제거 + 23자 모바일 가독성 락 적용)"""
        if not text: return text
        text = re.sub(r'^[ \t]*[1-9]\.[ \t]+', '✅ ', text, flags=re.MULTILINE)
        text = re.sub(r'^[ \t]*(?:첫|두|세|네)\s*번째(?:로|는)?(?:,)?\s*', '✅ ', text, flags=re.MULTILINE)
        text = re.sub(r'^[ \t]*(?:첫|둘|셋|넷)\s*째(?:로|는)?(?:,)?\s*', '✅ ', text, flags=re.MULTILINE)
        
        # 🟢 [가독성 개선] 블로그/밴드와 동일한 문장별 분할 및 23자 자동 줄바꿈 락 적용
        lines = []
        raw_paragraphs = text.split('\n')
        for para in raw_paragraphs:
            if not para.strip():
                lines.append("")
                continue
            
            sentences = re.split(r'\.\s+', para)
            for i, sent in enumerate(sentences):
                sent_str = sent.strip()
                if not sent_str:
                    continue
                if i < len(sentences) - 1 or sent.endswith('.'):
                    if not sent_str.endswith('.'):
                        sent_str += '.'
                
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

    def generate_cafe_content(self, topic, task_type='regular', target_time=None, delta_days=0):
        """카페 게시판 전용 콘텐츠 생성"""
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상 완벽 차단
        self._reload_all_settings()
        
        settings = self._load_settings()
        
        cafe_instr = settings.get('cafe_instructions', "카페 게시판 성격에 맞는 예의 바르고 정보 공유적인 스타일로 작성해주세요.\n- 말투: '~합니다'와 '~해요'를 5:5 비율로 섞어서 사용.\n- [필수]: 나열식 표현 및 AI 상투어 금지.")

        now_dt = datetime.now()
        current_dt_info = f"현재 날짜: {now_dt.strftime('%Y년 %m월 %d일')}"
        
        user_settings = self._load_user_settings()
        identity_rules = self._get_gym_identity(user_settings)
        
        system_message = f"""당신은 아이의 성장을 부모님과 함께 고민하고 공감하는 다정한 [카페 운영자 관장님]입니다.
{identity_rules}

[작성 목적 및 말투 - 감지 제외 교육/건강 유익 정보 공감]
- 감지(드라이브 자동 감지) 포스팅을 제외한 카페 포스팅 시에는 학부모님들이 깊이 공감하고 소통할 수 있는 실질적으로 유익한 전문 교육 정보, 건강 상식(성장, 두뇌 발달, 자신감, 기초 체력 등)을 따뜻하게 공감하는 톤으로 작성하세요.
- 신뢰감을 주는 격식체(~합니다/습니다)와 다정한 구어체(~해요, ~네요)를 [5:5 비율]로 적절히 섞어서 작성하세요.
- "~하세요", "~하십시오" 등 지시/명령조 어미 절대 금지.
- 지침: {cafe_instr}

[절대 엄수 사항 - 사실 기반 작성]
- **사실 정보 지어내기 금지**: 주어진 주제와 관련 없는 특정 장소(예: 전남, 서울 등), 특정 대회 명칭, 특정 인물 이름을 절대 임의로 지어내지 마세요.
- **날씨 수치 인용**: 날씨 정보가 제공된 경우, 기온 수치를 본문에 반드시 정확하게 언급하세요. (예: "오늘 양양 기온은 16도네요")
- **정체성 보호**: 본인이 지도하는 종목 외의 타 무도 종목은 절대 언급하지 마세요.

[공통 시스템 규칙]
{self._get_common_system_rules('cafe')}
"""
        # 예약 시각에서 시간(hour) 추출
        target_hour = None
        if target_time:
            try:
                h_match = re.search(r'(\d+)', str(target_time))
                if h_match:
                    target_hour = int(h_match.group(1))
            except:
                pass
        # 지능형 훅 (날씨)
        is_forecast = self._check_is_forecast(target_time)
        # 지역 정보 동적 추출 (우선순위: UI설정 > 주소 > 태그)
        user_settings = self._load_user_settings()
        weather_loc = settings.get('weather_location', '').strip()
        if not weather_loc:
            # 1. user_settings.txt의 주소(address)에서 추출
            address = user_settings.get('address', '')
            if address:
                addr_parts = address.split()
                weather_loc = addr_parts[1] if len(addr_parts) >= 2 else addr_parts[0]
            
            # 2. 주소도 없는 경우 태그에서 지역명 추출 시도
            if not weather_loc:
                tags = user_settings.get('blog_tags', '')
                if tags:
                    first_tag = tags.split(',')[0].strip()
                    weather_loc = re.sub(r'(합기도|체육관|태권도|유도|검도|스포츠|격투기)', '', first_tag).strip()

        if weather_loc:
            weather_hook = self._cafe_build_weather_hook_message(weather_loc, is_forecast, target_hour=target_hour, delta_days=delta_days)
            if weather_hook: system_message += weather_hook

        # 지능형 훅 (뉴스)
        news_hook = self._build_news_hook_message('cafe')
        if news_hook: system_message += news_hook

        base_prompt = f"""[주제: {topic}]
위 지침에 따라 카페 포스팅 내용을 작성해 주세요.

[출력 형식 및 작성 팁]
- 본문만 작성할 것. (제목 및 태그 제외)
- 분량: 공백 포함 최소 300자 이상 작성 (내용이 빈약하지 않도록 구체적으로 설명)
- 첫 문장 금기: "또한", "그리고", "결론적으로" 등의 접속사로 절대 글을 시작하지 마세요.
- 정서적 교감: 학부모님들과 유대감을 형성할 수 있는 따뜻한 멘트를 포함해 주세요.
"""

        # 모델 순회
        models_to_use = self.selected_models
        for step in range(len(models_to_use)):
            if self.stop_event.is_set():
                return None
            model_idx = (self.current_model_index + step) % len(models_to_use)
            model_name = models_to_use[model_idx]
            
            if not self._check_daily_limit(model_name): continue

            try:
                provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
                if provider == "openai":
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": base_prompt}],
                        temperature=0.7, max_tokens=1000
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_message, base_prompt)
                else: continue

                if content:
                    content = self._apply_stability_filter(content, 'cafe')
                    content = self._cafe_readability_filter(content) # 🟢 밴드/카페 전용 가독성 필터 사용
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)
                    
                    return {
                        "title": f"[카페] {topic}",
                        "content": content,
                        "model": model_name
                    }
            except Exception as e:
                logger.error(f"카페 생성 오류 ({model_name}): {e}")
                continue

        return self._get_dummy_content(topic)
