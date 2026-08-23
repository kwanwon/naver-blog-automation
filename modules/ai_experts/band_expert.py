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
        """밴드 전용 날씨 훅 (로컬 캐시 데이터 최우선 활용)"""
        from modules.weather_cache_manager import WeatherCacheManager
        
        # 호출하는 측에서 이미 delta_days를 조정해서 보내주므로 그대로 사용합니다.
        effective_delta = delta_days
        
        # 실시간 API 호출을 피하고, 1번째 탭에서 갱신한 로컬 날씨 데이터를 바로 불러옵니다.
        cached_info = WeatherCacheManager.get_cached_weather(location, delta_days=effective_delta, target_hour=target_hour)
        
        if not cached_info:
            # 캐시 미스 또는 만료된 경우 실시간 네이버 스크래핑으로 갱신 후 재시도
            WeatherCacheManager.update_weather_cache_via_naver(location)
            cached_info = WeatherCacheManager.get_cached_weather(location, delta_days=effective_delta, target_hour=target_hour)
            
        if not cached_info:
            return ""
            
        return f"\n[System: 실시간 날씨 상세 정보]\n- 데이터: {cached_info}"

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

    def generate_band_content(self, topic, platform='band', task_type='regular', target_time=None, delta_days=0, **kwargs):
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
                    # 앞부분에서 대괄호 안의 폴더명 추출 시도
                    folder_match = re.search(r'\[(.*?)\]', parts[0])
                    if folder_match:
                        display_category = folder_match.group(1).strip()
                else:
                    # 기타: 주제 자체가 부 타임인 경우
                    folder_match = re.search(r'\[(.*?)\]', topic)
                    if folder_match:
                        display_category = folder_match.group(1).strip()
                        display_topic = topic.replace(f"[{display_category}]", "").strip(" [](),.")
        
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
            # (blog_writer_app.py에서 이미 내일 예약인 경우 delta_days=1로 전달하므로 중복으로 1을 더하지 않습니다)
            effective_delta = delta_days
            try:
                weather_hook = self._band_build_weather_hook_message(weather_loc, is_forecast=is_forecast, target_hour=target_hour, delta_days=effective_delta)
            except Exception as w_err:
                logger.warning(f"날씨 훅 수집 실패 (Fallback 우회 예정): {w_err}")
                weather_hook = ""
                
            if task_type == 'morning':
                topic = f"상쾌한 아침 인사와 오늘 날씨 안내, 그리고 [{topic}]에 대한 유익한 정보 공유 및 공감"
            elif task_type == 'closing':
                # 저녁의 본문은 일반 주제를 무시하고 명언/조언으로만 구성
                topic = "하루의 피로를 위로하고 마음을 다독이는 따뜻하고 깊이 있는 명언이나 조언 (최소 2~3문단 이상 상세히 작성, 짧게 끝내지 말 것)"
                evening_hook = self._build_evening_hook_message()
            else:
                # 오후/일반 포스팅인 경우 뉴스 훅 연동
                news_pool = kwargs.get('news_pool')
                if news_pool:
                    news_hook = f"\n[오늘의 주요 뉴스/이슈 정보]\n{news_pool}\n위 뉴스 정보를 바탕으로 학부모님들과 공감하고 소통하는 따뜻한 글을 작성해주세요."
                    topic = "점심 후 나른한 오후 안부 인사와 힘이 되는 명언, 그리고 오늘의 주요 뉴스를 바탕으로 한 학부모님과의 공감과 소통"
                else:
                    topic = f"점심 후 나른한 오후 안부 인사와 힘이 되는 명언, 그리고 [{topic}]에 대한 유익한 정보 공유 및 공감"

        # ─── 2. 분기별 작성 지침 및 프롬프트 빌드 ─────────────────────────
        max_tokens = 800
        
        identity_rules = self._get_gym_identity(user_settings)
        external_rules = self._get_common_system_rules(platform=platform)
        
        if is_group_a:
            # 📌 [유형 2] 담백하고 훈훈한 2문장형 수련 현장 기록 (스타일 A, 공백 포함 80~120자)
            max_tokens = 300
            
            system_message = f"""당신은 아이들의 수련 현장을 애정 어린 시선으로 지켜보고 학부모님께 보고하는 [다정하고 든든한 지도자]입니다.
{identity_rules}

[작성 목적: 유형 2 - 수련 현장 담백한 2문장 기록 (사진/영상 중심)]
- 포스팅의 핵심이 사진과 동영상이므로, 본문 글이 너무 길거나 가식적이지 않게 **담백하고 훈훈한 딱 2문장(공백 포함 80~120자 내외)**으로 간결하게 작성합니다.
- 거창한 훈계나 사설(인성, 존중, 배려 등 장황한 미사여구) 및 기계적인 상투어를 절대 쓰지 마세요.
- 아이들이 오늘 집중해서 땀 흘린 모습과, 서로 격려하며 끝까지 최선을 다한 대견한 모습을 자연스럽고 다정하게 2문장으로 담아내세요.

[표현 지침 - 스타일 A (담백·훈훈)]
- (문장 1): 오늘 아이들과 함께 기본기를 다지며 활기차게 땀 흘려 수련한 현장 모습 서술.
- (문장 2): 끝까지 집중하며 서로 격려하는 모습이 참 대견하고 멋진 시간이었다는 칭찬 서술.
- 문장 톤: 부모님께 말씀드리듯 편안하고 훈훈한 어조(~했습니다, ~했답니다).
- 작성 예시: "오늘 강원도대표대련선수부 아이들과 함께 기본기를 다지며 땀 흘려 수련했습니다. 끝까지 집중하며 서로 격려하는 모습이 참 대견하고 멋진 시간이었습니다."
- 🚨 스스로를 지칭할 때 '관장', '사범', '선생님' 등 특정 직급이나 호칭을 절대 사용하지 마세요.

[출력 형식 제한]
- **AI는 오직 [본문]의 알맹이 본문 내용(딱 2문장)만 작성합니다.**
- 해시태그, 첫문장(인사말), OO부 수련 완료 멘트, 사진 화질 양해 문구 등은 파이프라인에서 자동으로 조합하므로 **본문 내용에 절대 포함하지 마세요.**
- 🚨 [슬로건/표어 임의 창작 절대 금지 ⭐⭐⭐⭐⭐]: AI가 스스로 체육관이나 단체의 슬로건, 표어를 창작하여 덧붙이는 행위를 100% 엄격히 금지합니다.
- 🚨 [이모지 사용 절대 금지 ⭐⭐⭐⭐⭐]: 본문에는 어떠한 이모지(😊, 🙏 등)도 절대로 넣지 마세요. 오직 깔끔한 텍스트로만 작성하세요.

[공통 시스템 규칙]
{external_rules}
"""
            base_prompt = f"""[주제(수련내용): {display_topic}]
위 수련 내용을 바탕으로 학부모님께 보고하는 담백한 스타일 A (딱 2문장, 80~120자) 본문을 작성하세요.

[필수 작성 지침]
- 장황하거나 가식적인 긴 글은 절대 금지합니다.
- 사진과 영상이 돋보일 수 있도록 **딱 2문장(공백 포함 80~120자 내외)**으로 완성하세요.
- [문장 1: 기본기/수련에 집중해 땀 흘린 모습] + [문장 2: 끝까지 집중하며 서로 격려한 대견한 모습 칭찬]

[출력 형식]
본문: 담백하고 훈훈한 딱 2문장 (공백 포함 80~120자 내외, 완전한 서술형 문장으로 끝맺음).
태그: 본문 내용과 관련된 키워드 5개 (예: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5)
"""

        else:
            # 📌 [유형 1] 정보 지식 공유용 지침 (주제 중심, 날씨 반영, 모바일 가독성)
            max_tokens = 800
            
            # 날씨 정보 연동 및 Fallback 지침 (선택지 C)
            weather_instruction = ""
            if weather_hook:
                if task_type == 'closing':
                    weather_example = '"내일 아침 기온은 18도, 하늘은 맑음, 강수확률은 0%, 미세먼지는 좋음으로 예상됩니다. 맑고 상쾌한 출근길이 될 것 같으니 가벼운 발걸음으로 하루를 시작해 보세요!"'
                    tense_instruction = "이 글은 저녁 늦게 올라가는 마무리 글이므로, 제공된 날씨 데이터는 '내일 아침'의 예보입니다. 반드시 '내일 아침 날씨'를 예보하는 형태(~예상됩니다)로 안부 인사를 작성하세요."
                    weather_position_rule = "3. 날씨 브리핑은 반드시 **1분 홈케어 팁 작성 후(글의 가장 마지막)**에 독립된 단락으로 작성하세요. 절대 첫 줄이나 홈케어 이전에 쓰지 마세요."
                else:
                    weather_example = '"바깥 기온은 15도, 하늘은 흐림, 강수확률은 0%, 미세먼지 보통으로 쾌적한 아침입니다. 상쾌하게 활동을 시작해 보세요!"'
                    tense_instruction = "🚨 [시점 주의]: 이 글은 예약 발행되어 독자가 '그 시간'에 실시간으로 읽는 글입니다. 제공된 날씨 데이터는 바로 '그 예약 시간'의 날씨입니다. 절대 '~예상된다'는 식의 예보(미래형) 표현이나 '내일'이라는 단어를 쓰지 마세요! 무조건 독자가 지금 체감하는 '현재 날씨(~합니다, ~네요)'로 단정 지어 작성하세요.\n🚨 [오전 포스팅 필수 주의]: 이 글은 '오전(아침)' 포스팅입니다. '나른한 오후', '오후 시간', '저녁' 등 오전과 맞지 않는 시간대 표현을 절대로 사용하지 마세요!"
                    weather_position_rule = "3. 첫 도입부는 무조건 날씨 브리핑으로 자연스럽게 시작하며, 절대 글의 중간이나 끝부분에 넣지 마세요."

                # 강제 지침 추가 (상투적 멘트 금지 및 온도 해석 기준)
                weather_instruction = f"""[System: 실시간 기상청 날씨 정보가 제공되었습니다!]
{weather_hook}

{tense_instruction}
🚨 [날씨 브리핑 강제 규칙 - 매우 엄격 ⭐⭐⭐⭐⭐]:
1. **[주관적 감상 100% 원천 금지]**: "다소 더운 편이지만", "활동하기 좋은 날씨네요", "쌀쌀한 기운이 감돌아" 등 AI가 자의적으로 날씨를 해석하거나 주관적인 감상을 더하는 문장을 단 한 줄이라도 작성하는 것을 100% 엄격히 금지합니다.
2. **[건조하고 객관적인 팩트만 전달]**: 오직 제공된 기온, 날씨 특보, 미세먼지 수치를 바탕으로 기온 팩트를 작성하되, **바로 뒤에 이어지는 두 번째 문장에 '날씨 체감(덥다/춥다)과 무관한 다정한 응원 안부'를 딱 1줄 추가하여 부드럽게 본문으로 연결**하세요. 화려한 날씨 수식어는 절대 쓰지 마세요.
   - (작성 예시: "오늘 양양읍은 기온이 25도에 미세먼지는 좋음, 하늘은 흐린 오후네요. 이런 날씨 속에서도 각자의 자리에서 최선을 다하고 계실 부모님들을 응원하며, 오늘은 [주제]에 대해 이야기해 볼까 합니다.")
3. **[불필요한 날씨 훈계 생략]**: "요즘처럼 변화가 많은 날씨에는...", "면역력이 떨어질 수 있으니 건강 유의하세요" 같은 건강 훈계성 사족은 절대 쓰지 마시고, 팩트 1줄과 따뜻한 일상 안부 1줄 전달 후 즉시 본문으로 넘어가세요.
4. **[거짓 수치 날조 금지]**: 제공받은 데이터 외의 기온이나 상태를 지어내지 마세요.
{weather_position_rule}
"""
            else:
                weather_instruction = """- 현재 상세 날씨 데이터가 없거나 일시적 통신 지연 상태입니다. 
- 절대 거짓 기온이나 엉뚱한 날씨 멘트("상쾌한 바람", "맑고 쾌청한 공기")를 지어내어 쓰지 마세요(환각 방지). 날씨 언급 없이 계절에 걸맞은 정겹고 다정한 일반 안부 인사로 첫머리를 자연스럽게 시작하세요.
"""

            # 📌 홈케어 팁 40개 순환 로직 적용 (저녁 전용)
            home_care_instruction = ""
            home_care_output_instruction = ""
            home_care_output_append = ""
            if task_type == 'closing':
                home_tips = [
                    {"name": "데드버그 훈련 (협응 및 코어 강화)", "desc": "누워서 양손과 양발을 교차하여 움직이며 복부 코어와 신체 협응력을 기르는 효과적인 동작"},
                    {"name": "플랭크 버티기 (코어 및 전신 안정성)", "desc": "팔꿈치와 발끝으로 버티며 척추 주변 근육과 코어 전반을 단단히 세우는 기초 전신 운동"},
                    {"name": "스쿼트 버티기 (하체 및 엉덩이 근육)", "desc": "허벅지가 지면과 수평이 될 때까지 내려가 버티며 하체의 강인한 버팀력을 기르는 근력 동작"},
                    {"name": "다운독 요가 자세 (전신 스트레칭 및 피로 해소)", "desc": "엎드린 개 자세로 척추와 다리 후면 근육을 길게 늘려주어 전신 피로와 긴장을 푸는 요가 자세"},
                    {"name": "나비 자세 (골반 정렬 및 내전근 유연성)", "desc": "발바닥을 마주 대고 무릎을 바닥 쪽으로 지긋이 눌러주며 틀어진 골반을 정렬하는 골반 이완 운동"},
                    {"name": "고양이 자세 (척추 유연성 및 등 스트레칭)", "desc": "네발기기 자세에서 척추를 위아래로 둥글게 움직이며 등과 허리 긴장을 푸는 척추 가동성 강화 기법"},
                    {"name": "브릿지 자세 (둔근 강화 및 척추 안정화)", "desc": "누운 상태에서 골반을 높이 들어 올려 엉덩이와 뒤태 코어 라인을 탄탄하게 다지는 강화 운동"},
                    {"name": "버드독 스트레칭 (척추 정렬 및 밸런스)", "desc": "네발기기 자세에서 한쪽 손 and 반대쪽 발을 수평으로 뻗어 척추 기립근 and 코어 밸런스를 균형 있게 다지는 운동"},
                    {"name": "코브라 자세 (굽은 등 및 가슴 신전)", "desc": "엎드린 상태에서 손으로 바닥을 밀며 상체를 들어 올려 굽은 등과 가슴을 시원하게 펴주는 스트레칭"},
                    {"name": "이상근 스트레칭 (엉덩이 피로 및 골반 통증 완화)", "desc": "누운 자세에서 한쪽 다리를 숫자 4 모양으로 걸쳐 가슴 쪽으로 당기며 엉덩이 심층 근육을 이완하는 동작"},
                    {"name": "아기 자세 (척추 및 어깨 이완)", "desc": "무릎을 꿇고 엎드려 이마를 바닥에 대고 양팔을 뻗어 하루 동안 쌓인 척추와 어깨 긴장을 녹이는 휴식 자세"},
                    {"name": "체어 포즈 (의자 자세 코어 강화)", "desc": "가상의 의자에 앉듯이 골반을 낮추고 양손을 하늘로 뻗어 허벅지와 등 근육을 동시에 강화하는 하체 협응 동작"},
                    {"name": "슈퍼맨 자세 (등 기립근 및 후면 사슬 강화)", "desc": "엎드린 상태에서 상체와 하체를 동시에 들어 올려 척추 기립근 and 둔근 전체를 조여주는 효과적인 등 운동"},
                    {"name": "러시안 트위스트 (옆구리 및 외복사근 자극)", "desc": "상체를 비스듬히 눕힌 채 양손을 모아 좌우로 몸통을 회전하며 복부와 허리 라인을 탄탄하게 잡아주는 동작"},
                    {"name": "장요근 스트레칭 (골반 앞쪽 및 장요근 이완)", "desc": "한쪽 무릎을 바닥에 대고 런지 자세에서 골반을 앞으로 지긋이 밀어 굽은 자세로 단축된 골반 앞쪽 근육을 늘리는 동작"},
                    {"name": "발바닥 족저근막 마사지 (테니스공 롤링)", "desc": "발바닥 아래에 테니스공이나 마사지 볼을 두고 체중을 실어 굴리며 발바닥 전체의 누적 피로와 족막을 이완하는 기법"},
                    {"name": "벽 슬라이드 (굽은 등 및 라운드 숄더 교정)", "desc": "벽에 등, 엉덩이, 팔꿈치와 손등을 완전히 밀착하고 위아래로 쓸어올리며 굳어진 날개뼈 가동성을 살리는 운동"},
                    {"name": "벽 짚고 종아리 늘리기 (아킬레스건 스트레칭)", "desc": "벽을 짚고 서서 한쪽 다리를 뒤로 길게 뻗고 뒤꿈치를 바닥에 붙여 종아리와 아킬레스건을 곧게 늘려주는 스트레칭"},
                    {"name": "와이퍼 자세 (골반 관절 가동성 증진)", "desc": "바닥에 앉아 무릎을 세우고 양 다리를 와이퍼처럼 좌우 바닥 방향으로 번갈아 쓰러뜨리며 골반 가동 범위를 넓히는 자세"},
                    {"name": "목 및 승모근 스트레칭 (거북목 증후군 해소)", "desc": "한 손으로 머리 반대쪽을 감싸 귀가 어깨에 닿는 느낌으로 지긋이 당겨주어 목 덜미와 승모근 긴장을 풀어주는 팁"},
                    {"name": "수건 목 스트레칭 (일자목 완화)", "desc": "목 뒤에 수건을 걸고 양손으로 가볍게 앞으로 당기며 고개를 뒤로 젖혀 굳은 일자목 커브를 회복하는 스트레칭"},
                    {"name": "벽 스쿼트 버티기 (무릎 보호 및 하체 코어)", "desc": "벽에 등을 대고 무릎을 직각으로 굽힌 채 앉은 자세를 유지하며 무릎 관절에 무리 없이 허벅지를 강화하는 동작"},
                    {"name": "L자 다리 올리기 (하체 부종 및 혈액 순환)", "desc": "바닥에 누워 양다리를 벽에 직각으로 기대어 올린 뒤 유지하여 하체에 쌓인 피로 물질과 부종을 빼주는 휴식 자세"},
                    {"name": "손목 굴곡근 스트레칭 (스마트폰 증후군 예방)", "desc": "팔을 앞으로 쭉 뻗고 반대쪽 손으로 손끝을 몸 쪽으로 당겨주어 마우스와 스마트폰 사용으로 지친 손목을 풀어주는 동작"},
                    {"name": "개구리 자세 (고관절 유연성 및 순환)", "desc": "엎드린 상태에서 양 무릎을 개구리처럼 넓게 벌리고 골반을 바닥으로 지긋이 눌러 굳어있는 고관절을 열어주는 스트레칭"},
                    {"name": "암 워킹 (전신 예열 및 코어 협응력)", "desc": "선 자세에서 상체를 숙여 손으로 바닥을 짚고 앞으로 걸어 나갔다가 돌아오며 전신 근육을 고르게 깨우는 전신 운동"},
                    {"name": "T자 밸런스 버티기 (발목 안정성 및 전신 균형)", "desc": "한 발로 서서 상체를 숙이고 반대쪽 다리를 뒤로 뻗어 몸을 T자로 만들어 버티며 신체 균형 감각과 코어를 기르는 동작"},
                    {"name": "뒤꿈치 들기 일명 카프 레이즈 (혈액 펌핑)", "desc": "바르게 서서 발뒤꿈치를 끝까지 들어 올렸다가 천천히 내리며 '제2의 심장'이라 불리는 종아리 근육을 펌핑하는 운동"},
                    {"name": "사이드 런지 스트레칭 (내전근 이완)", "desc": "다리를 넓게 벌리고 서서 한쪽 무릎만 굽히며 체중을 실어 반대쪽 허벅지 안쪽 근육을 시원하게 늘려주는 동작"},
                    {"name": "무릎 가슴으로 당기기 (허리 하부 및 골반 이완)", "desc": "편안히 누운 상태에서 양 무릎을 가슴 쪽으로 끌어안고 좌우로 가볍게 구르며 허리 하부와 골반 긴장을 푸는 스트레칭"},
                    {"name": "의자 앉아 상체 비틀기 (척추 가동성 증진)", "desc": "의자에 앉은 상태로 상체를 뒤로 돌려 등받이를 잡고 지긋이 비틀어주며 굳은 척추의 회전 가동 범위를 살려주는 동작"},
                    {"name": "견갑골 조이기 (만성 승모근 피로 완화)", "desc": "양어깨를 뒤로 활짝 펴고 날개뼈(견갑골)가 서로 맞닿는 느낌으로 등 근육을 조여 라운드 숄더를 교정하는 팁"},
                    {"name": "발목 포인/플렉스 (발목 관절 가동성 확대)", "desc": "다리를 뻗고 앉아 발끝을 몸 쪽으로 최대한 당겼다가 앞을 향해 길게 밀어내며 발목 주변 인대와 근육을 푸는 동작"},
                    {"name": "두통 완화 뒷목 지압 (두통 완화 및 혈류 개선)", "desc": "양손 엄지손가락으로 뒷목과 머리뼈가 만나는 쏙 들어간 부위(풍지혈)를 지긋이 눌러주어 피로와 두통을 가라앉히는 지압법"},
                    {"name": "수건 이용한 어깨 회전 (오십견 예방 및 유연성)", "desc": "수건의 양끝을 팽팽하게 잡고 팔을 편 채로 머리 위를 지나 등 뒤로 넘겼다 돌아오며 굳은 어깨 관절을 부드럽게 푸는 동작"},
                    {"name": "사이드 벤드 측면 늘리기 (갈비뼈 및 옆구리 이완)", "desc": "서 있는 자세에서 한 팔을 머리 위로 뻗고 몸통을 반대쪽으로 부드럽게 기울여 옆구리와 갈비뼈 사이 근육을 이완하는 동작"},
                    {"name": "폼롤러 등허리 롤링 (근막 이완)", "desc": "폼롤러를 등 뒤에 대고 누워 무릎을 세운 뒤 위아래로 가볍게 굴려주며 등허리 주변의 뭉친 근막을 시원하게 풀어주는 기법"},
                    {"name": "골반 걷기 (골반 교정 및 복부 자극)", "desc": "두 다리를 뻗고 앉은 상태에서 엉덩이를 들썩이며 앞으로 나아갔다가 뒤로 돌아오며 틀어진 골반을 교정하는 훈련"},
                    {"name": "눈 8자 굴리기 (시각 피로도 완화)", "desc": "눈을 감고 안구를 상하좌우 및 8자 모양으로 천천히 굴려주며 스마트기기 사용으로 지친 안구 주변 근육의 긴장을 푸는 팁"},
                    {"name": "깊은 복식 호흡 (자율신경 안정 및 스트레스 해소)", "desc": "편안히 앉아 코로 숨을 깊게 들이마시며 배를 내밀고 입으로 길게 내뱉으며 자율신경 안정시키고 마음을 이완하는 호흡법"}
                ]
                import os, json
                from utils.path_utils import get_config_dir
                state_file = os.path.join(get_config_dir(), 'home_care_state.json')
                tip_index = 0
                try:
                    if os.path.exists(state_file):
                        with open(state_file, 'r', encoding='utf-8') as f:
                            state = json.load(f)
                            tip_index = state.get('tip_index', 0)
                except Exception:
                    pass
                selected_tip = home_tips[tip_index % len(home_tips)]
                try:
                    os.makedirs(os.path.dirname(state_file), exist_ok=True)
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump({'tip_index': (tip_index + 1) % len(home_tips)}, f)
                except Exception:
                    pass
                
                home_care_instruction = f"""[1분 홈케어 팁 작성 필수 ⭐⭐⭐]
- **반드시 본문 작성이 끝난 후**, 날씨 브리핑 이전에 빈 줄을 하나 띄우고 독자가 집에서 1분 안에 손쉽게 실천할 수 있는 [1분 홈케어 팁]을 무조건 작성하세요.
- ⚠️ [필수 지정 팁]: 오늘은 무조건 **'{selected_tip['name']}'**({selected_tip['desc']})을(를) 주제로 서술하십시오.
- 주의: '[1분 홈케어 팁]' 등의 인위적인 머리말이나 대괄호 타이틀은 절대 달지 마세요.
- 본문 내용과 자연스럽게 이어지는 연결 다리(Bridge) 멘트를 넣어 홈케어로 넘어가세요.
- 🚨 [말투 및 도입부 주의사항]:
  1. 기계적이고 반복적인 도입부("오늘 하루도 수고한 우리 아이들을 위해 집에서 간단히 할 수 있는 스트레칭을 함께 해보는 것도 좋겠어요" 등)는 절대로 사용하지 마세요.
  2. 도입부와 권유형 어미를 항상 새롭고 자연스럽게 변형하세요. (예: "해보는 것은 어떨까요?", "함께 1분만 투자해 보세요", "해보는 것도 좋겠네요", "가족이 함께 해보세요" 등 탄력적으로 작성)"""
                home_care_output_instruction = " + 1분 홈케어 팁"
                home_care_output_append = ", 마지막에 자연스럽게 이어지는 1분 홈케어 팁"

            # 📌 시간대별 본문 글자수 및 어투 조정
            if task_type == 'closing':
                content_length_instruction = "공백 포함 200~300자 내외 (3~4문단 정도로 적당히 풍성하게 작성)"
            else:
                content_length_instruction = "공백 포함 300~500자 내외 (3~4문단으로 풍성하게 작성)"

            if task_type == 'closing':
                layout_instruction = f"- **AI는 오직 [본문] -> [1분 홈케어 팁] -> [날씨 브리핑] 순서로만 작성합니다. (별도의 마커 없이 '본문:' 안에 모두 자연스럽게 이어서 작성하세요)**"
            else:
                layout_instruction = f"- **AI는 오직 [날씨 브리핑]으로 시작하는 [본문]만 작성합니다. (별도의 마커 없이 '본문:' 안에 모두 자연스럽게 이어서 작성하세요)**"

            system_message = f"""당신은 아이의 성장을 함께 고민하는 다정하고 유익한 [교육 전문가(지도자)]입니다.
{identity_rules}

[작성 목적: 유형 1 - 정보 공유 및 공감 소통]
- 학부모님께 실질적으로 유익한 교육 정보, 건강 상식(성장, 두뇌 발달, 자신감, 기초 체력 등)을 다정하게 설명하거나, 명언/조언을 통해 위로를 전하는 포스팅입니다.
- **[중요] 밴드 공간의 특성상 이미 등록된 학부모님들이 보는 곳이므로 자기 종목에 대한 자랑, 홍보, 어필은 일절 포함하지 마세요.**
- 순수하게 학부모님들이 보았을 때 유익하고 마음이 따뜻해지는 정보 전달과 공감에만 집중하세요.

[강력한 공감 및 어투 제약 규칙 - 매우 중요 ⭐⭐⭐⭐⭐]
- 밴드 글은 지시나 명령, 강압적으로 시키는 느낌("~하세요", "~해야 합니다", "~하십시오")이면 절대로 안 됩니다.
- 학부모님들께 유용한 정보를 나누고 함께 공감하는 아주 다정한 대화체("~하면 좋다고 하네요", "~해보는 것은 어떨까요?", "~라는 점이 참 좋지요")로 부드럽게 서술하여 거부감을 원천 차단하세요.
- 🚨 아이들의 운동을 언급할 때 '합기도나 다른 운동', '합기도 등 다른 종목'과 같이 불필요하게 '다른 운동'이나 '종목'이라는 표현을 덧붙이지 마세요. 오직 '합기도' 또는 '운동', '수련' 이라는 단어만 깔끔하게 사용하세요.
- 🚨 스스로를 지칭할 때 '관장', '사범', '선생님' 등 특정 직급이나 호칭을 절대 사용하지 마세요. 대신 '지도자'라고 표현하거나, 호칭 없이 "항상 노력하겠습니다" 등으로 자연스럽게 문장을 맺으세요.

[날씨 및 안부 반영 지침]
{weather_instruction}

[뉴스 및 이슈 반영 지침]
{news_hook}

{home_care_instruction}

[출력 형식 제한]
{layout_instruction}
- 본문의 순수 알맹이(날씨 브리핑과 홈케어를 제외한 핵심 본문) 길이를 {content_length_instruction}로 맞춰서 풍성하게 작성하세요. 내용이 부실하면 안 됩니다.
- 최상단에 자동으로 붙는 [체육관 소개 슬로건(예: 운동, 교육...)]과 하단의 [해시태그]는 시스템이 자동 조립하므로 **절대 글에 쓰지 마세요.** 
- 🚨 (주의: 당신이 작성하는 글의 끝에 임의로 "한체대 라이온입니다", "체육관에서 뵙겠습니다" 같은 맺음말이나 슬로건을 지어내서 덧붙이지 마세요! 슬로건과 맺음말은 시스템이 외부에서 붙여줍니다.)
- 🚨 [슬로건/표어 임의 창작 절대 금지 ⭐⭐⭐⭐⭐]: AI가 스스로 체육관이나 단체의 슬로건, 표어(예: "몸은 튼튼하게 마음은 바르게" 등)를 창작하여 덧붙이는 행위를 100% 엄격히 금지합니다.
- 🚨 [이모지 사용 절대 금지 ⭐⭐⭐⭐⭐]: 글을 작성할 때 어떠한 이모지(이모티콘, 😊, 🙏 등)도 절대로 사용하지 마세요. 오직 텍스트로만 진중하고 다정하게 작성하세요.
- 제목 마커나 불필요한 번호 지칭('첫째', '둘째' 등)은 쓰지 마세요.

[말투 및 종결어미]
- 다정한 구어체(~해요, ~네요, ~이지요)를 적극 사용하여 딱딱함을 없애고 친근하게 다가가세요. 격식체(~합니다)는 최소화하세요.

[공통 시스템 규칙]
{external_rules}
"""
            if task_type == 'closing':
                output_structure = f"본문: 유익한 정보와 공감 중심의 본문 내용 (길이 {content_length_instruction})\n\n(자연스럽게 이어지는 1분 홈케어 팁)\n\n(마지막을 장식하는 내일 아침 날씨 안부)\n※ 반드시 위 순서 [본문 -> 홈케어 -> 날씨] 를 엄격히 지키고, '홈케어:', '날씨:' 같은 소제목 마커를 달지 마세요."
            else:
                output_structure = f"본문: (자연스러운 현재 날씨 안부로 시작) 유익한 정보와 공감으로 이어지는 모바일 최적화 본문 (길이 {content_length_instruction})\n※ '날씨:' 같은 소제목 마커를 쓰지 말고 본문 안에 자연스럽게 녹여내세요."

            base_prompt = f"""[주제: {topic}]
위 주제를 바탕으로 학부모님과의 공감과 다정한 소통{home_care_output_append}이 자연스럽게 결합된 본문을 정성껏 작성해 주세요.

[출력 형식]
{output_structure}
태그: 본문 내용과 관련된 생성 키워드 5개 (예: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5)
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
