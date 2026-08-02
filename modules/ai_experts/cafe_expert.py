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
        
        # 🟢 1분 홈케어 팁 (블로그와 동일한 40개 순환 로직 도입)
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
            {"name": "깊은 복식 호흡 (자율신경 안정 및 스트레스 해소)", "desc": "편안히 앉아 코로 숨을 깊게 들이마시며 배를 내밀고 입으로 길게 내뱉으며 자율신경을 안정시키고 마음을 이완하는 호흡법"}
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
        
        # 다음 팁 인덱스 저장 (블로그와 공유)
        try:
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({'tip_index': (tip_index + 1) % len(home_tips)}, f)
        except Exception:
            pass
        
        # 🟢 Task Type에 따른 카페 특화 지시사항 분기
        if task_type == 'detection':
            task_instruction = f"""
[포스팅 성격: 현장 스케치 (드라이브 사진 감지)]
- 아이들이 체육관에서 운동하는 사진/영상을 올리는 현장 스케치용 글입니다.
- 절대 장황한 교육 칼럼이나 정보성 글을 길게 쓰지 마세요! (최대 3~4줄 이내로 짧고 담백하게 작성)
- "오늘도 아이들이 씩씩하게 운동했습니다", "땀 흘리는 모습이 멋집니다" 등 현장의 활기찬 분위기와 칭찬 위주로 가볍게 작성하세요.
"""
        else:
            time_hook = ""
            if task_type == 'morning':
                time_hook = "- [아침 인사]: 활기찬 아침 인사로 시작하며, 부모님들의 오늘 하루를 응원하는 멘트를 꼭 넣어주세요."
            elif task_type == 'closing':
                time_hook = "- [저녁 인사]: 하루를 편안하게 마무리하는 인사로 시작하며, 늦게까지 고생하신 부모님들의 수고를 다독이는 위로의 멘트를 꼭 넣어주세요."
            else:
                time_hook = "- 다정하고 편안한 인사로 글을 자연스럽게 시작해 주세요."
                
            task_instruction = f"""
[작성 목적 및 말투 - 학부모 공감 및 유익 정보]
{time_hook}
- 학부모님들이 깊이 공감할 수 있는 실질적으로 유익한 교육 정보, 건강 상식(성장, 두뇌 발달, 자신감 등)을 따뜻한 톤으로 작성하세요.
- [매번 다르고 창의적인 내용 필수]: "운동이 스트레스 해소에 좋습니다"와 같은 뻔하고 반복적인 말은 피해주세요. 구체적이고 새로운 관점의 이야기를 작성하여 매번 다른 느낌을 주어야 합니다.
- [카페 전용 꿀팁 코너 필수]: 본문 하단에 독자가 집에서 1분 안에 손쉽게 실천할 수 있는 아래의 [1분 팁]을 반드시 이어서 작성하십시오.
  * ⚠️ [필수 지정 팁]: 오늘은 무조건 **'{selected_tip['name']}'**({selected_tip['desc']})을(를) 주제로 서술하십시오. 다른 팁은 절대로 기술하지 마십시오.
  * 본문 칼럼에서 팁으로 부드럽고 다정하게 넘어가며 자연스럽게 이어주는 연결 다리(Bridge) 멘트를 최소 2문장 이상 스스로 작문하여 자연스럽게 연결하십시오. (예: "오늘 함께 알아본 정보를 바탕으로 집에서 아이와 1분만 가볍게 실천해 볼 수 있는 동작을 준비했습니다. 바로 ~입니다.")
  * 인위적인 '[홈케어 팁]' 같은 소제목 머리말을 절대 쓰지 말고, 본문과 한 호흡으로 부드럽게 이어지도록 서술하세요.
- 신뢰감을 주는 격식체(~합니다/습니다)와 다정한 구어체(~해요, ~네요)를 [5:5 비율]로 적절히 섞어서 작성하세요.
- "~하세요", "~하십시오" 등 지시/명령조 어미 절대 금지.
- 지침: {cafe_instr}
"""

        system_message = f"""당신은 아이의 성장을 부모님과 함께 고민하고 공감하는 다정한 [카페 운영자 관장님]입니다.
{identity_rules}

{task_instruction}

[절대 엄수 사항 - 도배성 홍보 문구 금지 ⭐⭐⭐⭐⭐]
- 🚨 **[특정 종목 상투적 홍보 멘트 및 도배성 문구 100% 금지]**: "특히, 합기도와 같은 무도는 단순한 신체 활동을 넘어서 자신감과 집중력을 키우는 데 도움이 됩니다", "자신의 몸을 조절하고 패배를 경험하며 인내와 끈기를 배울 수 있어요" 등 **매 포스팅마다 상투적으로 반복되는 무도/체육관 홍보 문단을 절대로 쓰지 마십시오.**
- 카페 포스팅은 광고성 도배 느낌이 나지 않도록, 오직 주어진 [주제]의 담백하고 유익한 부모님 공감 정보에만 집중하여 작성하세요.
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
- 첫 번째 줄에는 반드시 글의 제목을 작성해주세요. (형식: 제목: 여기에 제목 작성)
- 두 번째 줄부터 본문을 작성해 주세요.
- 분량: 카페 게시판의 특성상 광고성 도배 느낌이 나지 않도록, 전체 길이(1분 팁 포함)를 공백 포함 800자 ~ 1000자 이내로 간결하고 담백하게 작성하세요.
- 첫 문장 금기: "또한", "그리고", "결론적으로" 등의 접속사로 절대 글을 시작하지 마세요.
- 금지 기호: '1.', '2.' 같은 숫자 나열식 글쓰기나 이모티콘 나열을 자제하고 자연스러운 문장 형태로 풀어 쓰세요.
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
                        temperature=0.7, max_tokens=2000
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_message, base_prompt)
                else: continue

                if content:
                    # 제목 분리 처리
                    lines = content.split('\n')
                    generated_title = f"{topic}"
                    body_content = content
                    
                    for i, line in enumerate(lines):
                        if line.startswith("제목:"):
                            generated_title = line.replace("제목:", "").strip()
                            # 샵(#), 따옴표 등 제거
                            generated_title = re.sub(r'[\'\"#]', '', generated_title).strip()
                            # 첫 줄이 제목이면 그 이후가 본문
                            body_content = '\n'.join(lines[i+1:]).strip()
                            break
                    
                    body_content = self._apply_stability_filter(body_content, 'cafe')
                    body_content = self._cafe_readability_filter(body_content) # 🟢 밴드/카페 전용 가독성 필터 사용
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)
                    
                    return {
                        "title": generated_title,
                        "content": body_content,
                        "model": model_name
                    }
            except Exception as e:
                logger.error(f"카페 생성 오류 ({model_name}): {e}")
                continue

        return self._get_dummy_content(topic)
