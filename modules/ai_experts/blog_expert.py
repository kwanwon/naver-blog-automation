# -*- coding: utf-8 -*-
# ==============================================================================
# 🌟 [GOLDEN BACKUP PRESERVATION / 최종 완벽 완성본 보존 가이드] 🌟
# ==============================================================================
# - 작성일자: 2026년 5월 23일 19:30 (최종 품질 검증 완료)
# - 상태: 블로그 칼럼용 내부 지침 범용화 및 안정화 100% 완료
# - 목적: 어떠한 주제(운동, 웰니스, 시사, 핫이슈 등)에서도 거부감 없이 유익한 정보를
#         생성해내는 완벽한 블로그 전용 전문가(BlogExpert) 버전입니다.
# - ⚠️ 중요 알림: 다른 플랫폼(밴드, 카페) 기능을 수정하더라도 이 파일(blog_expert.py)은
#   완벽히 독립되어 있어 일절 수정되거나 영향받지 않습니다.
# ==============================================================================
import logging
import re
import json
import urllib.request
import urllib.parse
import ssl
import threading
from .base_expert import BaseAIExpert
from config.config import Config
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class BlogExpert(BaseAIExpert):
    def __init__(self, use_dummy=False):
        super().__init__(use_dummy)

    def generate_blog_content(self, topic, post_order=1, post_type_config=None, task_type='regular', target_time=None, delta_days=0):
        """블로그 전용 콘텐츠 생성 (최적화 및 안정화 버전)"""
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상(타 플랫폼 설정 오염) 완벽 차단
        self._reload_all_settings()
        
        settings = self._load_settings()
        ai_settings = settings
        user_settings = self._load_user_settings()
        
        # [블로그 전용 설정 로드] base_expert를 오염시키지 않고 블로그 엔진 내에서만 단독으로 로드
        try:
            import json, os
            from utils.path_utils import get_app_settings_path
            app_settings_path = get_app_settings_path()
            if os.path.exists(app_settings_path):
                with open(app_settings_path, 'r', encoding='utf-8') as f:
                    app_settings = json.load(f)
                    for k in ['blog_persona_mode', 'blog_persona_mode_custom', 'blog_style_mode', 'blog_theme', 'blog_hometip']:
                        if k in app_settings:
                            ai_settings[k] = app_settings[k]
        except Exception as e:
            logger.error(f"블로그 전용 설정 로드 중 오류: {e}")
        
        # 🟢 사용자 맞춤형 페르소나 및 종목 컨텍스트 주입 (범용화 완료)
        dojang_name = user_settings.get('dojang_name', user_settings.get('gym_name', '센터'))
        user_sports = user_settings.get('gym_sport', '운동')
        
        # 호칭 결정 로직 - 기본적으로 거부감 없는 보편적 전문가/지도자 호칭 부여
        teacher_title = "전문가"

        # 날짜/요일/시간 정보
        now_dt = datetime.now()
        target_hour = now_dt.hour
        
        # 만약 예약 시각(target_time, 예: "17:00")이 지정되어 있다면 해당 시각을 기준으로 요일 및 시간대 판별
        if target_time:
            try:
                t_hour, t_min = map(int, target_time.split(':'))
                target_hour = t_hour
                
                # 예약 시간이 현재 시각보다 이전이면(오늘 이미 지나갔으면) 내일 예약으로 판별하여 날짜 조정
                target_dt = now_dt.replace(hour=t_hour, minute=t_min, second=0, microsecond=0)
                if target_dt < now_dt:
                    now_dt = now_dt + timedelta(days=1)
                    delta_days += 1  # 날씨 조회 시 내일 날씨를 가져오도록 delta_days 증가
            except Exception as e:
                logger.error(f"target_time ({target_time}) 파싱 중 오류: {e}")
                target_hour = now_dt.hour
                
        # Calculate actual training date based on delta_days
        training_dt = now_dt + timedelta(days=delta_days)
        
        days_ko = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        time_name = self._get_time_of_day_name(target_hour)
        
        # Construct detailed date context for AI
        current_dt_info = f"발행(현재) 날짜: {now_dt.strftime('%Y년 %m월 %d일')} ({days_ko[now_dt.weekday()]}) / 활동(실제) 날짜: {training_dt.strftime('%Y년 %m월 %d일')} ({days_ko[training_dt.weekday()]}) / 시간대: {time_name}"

        # Past training record tone guideline based on delta_days
        past_guideline = ""
        if delta_days < 0:
            past_guideline = f"""- [과거 활동 회상/기록형 톤 엄수 ⭐⭐⭐]:
  * 실제 활동은 오늘이 아닌 과거 {training_dt.strftime('%Y년 %m월 %d일')} ({days_ko[training_dt.weekday()]})에 진행되었습니다.
  * 따라서, "오늘 운동을 방금 마쳤다", "오늘 아침 일찍 운동을 마쳤다"는 식의 시간적 모순을 유발하는 문구는 **절대 금지**합니다.
  * 반드시 "지난 {days_ko[training_dt.weekday()]}에 있었던", "최근 활동 모습", "지난 {training_dt.strftime('%m월 %d일')} 기록"과 같이 과거를 회상하고 기록하는 따뜻한 톤으로 본문을 구성하세요.
  * 문맥 또한 과거 완료/회상 어미(~했습니다, ~했었어요, ~였답니다 등)를 적절히 조화롭게 활용하세요."""
        else:
            past_guideline = f"""- [현재/미래 활동 톤]: 시간대를 특정하지 않는 현재 진행형/보편적 묘사를 사용하세요."""

        # 주제 키워드 매칭 기반 야외 활동 필터
        outdoor_keywords = ['해변', '모래사장', '운동장', '산', '야외', '공원', '캠프', '바다', '해수욕장', '강가', '숲', '야유회', '야외훈련']
        is_outdoor = any(keyword in topic for keyword in outdoor_keywords)
        if is_outdoor:
            outdoor_instruction = """- [야외/아웃도어 특별 지침 ⭐⭐⭐]:
  * 오늘 다루는 활동은 실내가 아닌 탁 트인 야외 공간에서 활기차게 이루어졌습니다.
  * 따라서, "매트 위에서", "도장 안에서", "실내 체육관에서" 라는 식의 실내 묘사 문구는 **절대 금지**합니다.
  * 바람, 햇살, 흙, 모래, 자연 환경의 상쾌함을 적극적으로 묘사하여 생동감 넘치는 아웃도어 칼럼 톤을 풍부하게 살려 서술하십시오."""
        else:
            outdoor_instruction = ""

         # [① 페르소나 (역할) 번역] - 다각화 및 커스텀 처리 완벽 지원
        _persona_prompt_map = {
            'expert_sport':  "당신은 주어진 주제에 깊은 통찰과 전문성을 가진 유익한 정보 칼럼니스트이자 연구원입니다. 독자(초보자 및 일반 대중 포함)에게 과학적 원리와 유용한 효과를 신뢰감 있게 설명하는 시점으로 작성하세요.",
            'sabeom':        "당신은 건강한 라이프스타일과 긍정적인 에너지를 전파하는 다정한 웰니스 에디터입니다. 주제에 관련된 활기찬 분위기와 긍정적인 일상의 가치를 생생하고 따뜻하게 전달해 주세요.",
            'parent_friend': "당신은 일상적인 건강과 웰니스 고민에 깊이 공감하고 함께 호흡하는 친근한 정보 큐레이터입니다. 독자의 시선에서 쉽게 이해할 수 있도록 실질적으로 유용한 상식과 팁을 다정하게 전달해 주세요.",
            'sports_coach':  "당신은 에너지 넘치고 활기찬 신체 단련 피트니스 코치입니다. 독자에게 강렬한 동기부여와 활력을 선사하고 신체를 활기차게 수련하는 가치를 경쾌하게 전달해 주세요.",
            'mental_mentor': "당신은 깊은 마음공부와 정서적 안정에 통찰이 깊은 마음 웰니스 멘토입니다. 현대인과 아이들이 겪는 만성 스트레스, 심리적 불안을 전인격적 정서 케어와 따뜻한 마음의 안정 가치로 잔잔하게 보듬어 주세요.",
            'rehab_expert':  "당신은 해부학적 전문 지식을 가진 스포츠 재활 트레이너이자 물리치료 관점의 해부 지도자입니다. 관절과 척추 주변의 정렬, 생리학적 안전 밸런스를 매우 과학적이고 체계적인 관점으로 설명하세요."
        }
        
        blog_persona_mode = ai_settings.get('blog_persona_mode', 'expert_sport')
        
        if blog_persona_mode == 'custom':
            custom_persona = ai_settings.get('blog_persona_mode_custom', '').strip()
            if custom_persona:
                smart_persona_prompt = f"당신은 사용자가 정의한 아래의 정체성과 가이드에 따라 글을 작성하는 전문가입니다:\n{custom_persona}"
            else:
                smart_persona_prompt = _persona_prompt_map['expert_sport']
        else:
            smart_persona_prompt = _persona_prompt_map.get(blog_persona_mode, _persona_prompt_map['expert_sport'])

        # [② 글쓰기 스타일 번역]
        _style_prompt_map = {
            'haeyo':     "군더더기 없이 깔끔하고 다정다감한 대화체 말투 (~해요, ~에요, ~하죠?)로 독자에게 친근하게 다가가는 어조로 작성하세요. 딱딱한 말투(~입니다, ~합니다만 반복)는 절대 금지합니다.",
            'imnida':    "전문적이고 신뢰감을 주는 정중한 격식체 말투 (~입니다, ~합니다)를 사용하여 신뢰도가 높고 진중한 칼럼나 보도자료처럼 격조 있게 작성하세요. 어조가 오락가락하지 않게 유지하세요.",
            'half_half': "친근함과 전문성을 동시에 확보할 수 있도록, 다정한 대화체(~해요, ~네요)와 정중한 격식체(~입니다, ~합니다)를 5:5 비율로 자연스럽게 섞어서 조화롭게 작성하세요. (예: 설명 부분은 ~입니다로 신뢰감 있게 서술하고, 독자의 공감을 이끌어내는 문장이나 마지막 격려 문장은 ~해요로 다정하게 작성)"
        }
        blog_style_mode = ai_settings.get('blog_style_mode', 'haeyo')
        smart_style_prompt = _style_prompt_map.get(blog_style_mode, _style_prompt_map['haeyo'])

        # [③ 본문 강조 테마 (양념) 3대 대분류 지능형 롤링 매칭]
        blog_theme = ai_settings.get('blog_theme', 'none')
        smart_spice_prompt = ""
        
        if blog_theme != 'none':
            theme_detail_map = {
                'style_growth': {
                    'desc': '성장기 발달 및 자세 교정 스타일',
                    'items': [
                        '성장판 자극 및 성장기 어린이들의 강인하고 곧은 키성장 발달 원리',
                        '현대인과 아이들이 흔히 겪는 구부정한 체형/잘못된 자세 교정 및 척추 기립근/코어 근육 정렬 메커니즘',
                        '소아비만 및 소아대사 질환을 체계적인 신체 활동과 대사율 보존을 통해 건강하게 조절하는 가치',
                        '좌우 뇌 신경망을 균형 있게 자극하여 인지 기능, 집중력 및 두뇌 기억력을 활성화하는 원리',
                        '신체적 도전과 극복 과정을 통해 자아존중감을 높이고 당당한 자신감을 기르는 심리적 가치',
                        '전신 뼈와 근육의 고른 쓰임을 통한 균형 잡힌 신체 밸런스 및 골밀도 향상 원리',
                        '대근육과 소근육을 세밀하게 자극하여 신체의 전반적인 운동 조정 능력과 뇌 협응력 발달',
                        '수련 과정을 통한 바른 보행 자세(걸음걸이) 확립 및 발바닥 아치(족저부)에 가해지는 압력 분산 효과',
                        '목 척추(거북목)와 골반 틀어짐을 예방하기 위한 일상 속 자가 신체 정렬 가이드',
                        '성장기 전신의 림프 순환 및 혈류 개선을 통한 피로 물질 배출 및 신진대사 촉진 효과'
                    ]
                },
                'style_wellness': {
                    'desc': '기초 체력 및 웰니스 스트레스 케어 스타일',
                    'items': [
                        '기초 체력 증진이 생리적 대사율 향상과 면역력 증강에 미치는 다채로운 유익함',
                        '주의 집중과 정교한 마인드 컨트롤이 일상 스트레스를 줄이고 공부나 업무 효율을 배가하는 원리',
                        '활기찬 전신 신체 활동을 통해 마음의 불안을 관리하고 정서적 스트레스를 해소하는 효과(도파민/세로토닌 분비 촉진)',
                        '단순 굶는 다이어트가 아닌 전신 근력 형성을 통한 탄탄한 체지방 및 대사 밸런스 관리',
                        '규칙적인 심폐 기능 자극 및 호흡 수련을 통한 산소 섭취량 증가 및 뇌 산소 공급 활성화',
                        '깊은 수면(숙면)을 유도하고 성장 호르몬 방출을 촉진하는 밤 시간대 신체 이완 메커니즘',
                        '일상 속 피로를 견디는 근지구력 향상과 관절 주변 근육 수축을 통한 관절 보호 효과',
                        '자율 신경계(교감/부교감 신경)의 밸런스를 맞추어 화와 불안을 조절하는 심신 안정 효과',
                        '땀 배출과 노폐물 배출을 유도하여 맑은 피부와 신체 디톡스를 이끄는 순환 활력',
                        '기초 대사량 보존을 통해 요요 현상 없이 평생 건강한 신체 기틀을 닦는 웰니스 설계'
                    ]
                },
                'style_social': {
                    'desc': '인성 교육 및 소통 에티켓 스타일',
                    'items': [
                        '동료와의 조화로운 파트너쉽과 신뢰를 통한 소통 및 사회성 발달 효과',
                        '일상 속 상호 배려와 매너, 성숙한 예의와 타인 존중이 인성 배양에 주는 밑거름',
                        '돌발 상황에서도 반사 신경을 극대화하여 스스로를 유연하게 보호하는 안전 조절력 및 안전 밸런스',
                        '수련 시 요구되는 높은 인내심과 감정 조절력이 충동적인 마음을 다스려 주는 인성 교육적 효과',
                        '약속과 규칙을 철저히 준수하는 준법정신 및 바른생활 습관 형성',
                        '동료의 실수를 보듬어주고 상호 격려하며 연대감과 건강한 우정을 다지는 과정',
                        '공동체 속에서의 리더십과 팔로워십의 균형, 양보의 아름다움을 배우는 사회성 실천',
                        '감사의 마음(부모님, 스승, 동료에 대한 감사)을 행동으로 표현하여 성숙한 인격을 닦는 예절 교육',
                        '끝까지 포기하지 않고 해내는 회복 탄력성과 불굴의 용기를 길러내는 정신 건강 증진',
                        '경청하는 자세를 통해 상대방의 입장을 이해하고 배려하는 참된 대화 예절 및 소통력'
                    ]
                }
            }
            
            style_cfg = theme_detail_map.get(blog_theme)
            if style_cfg:
                theme_desc = style_cfg['desc']
                theme_items_list = "\n".join([f"- {item}" for item in style_cfg['items']])
                
                smart_spice_prompt = f"""\n\n[🔥 본문 세부 강조 테마 (지능형 하이브리드 양념) 지침 ⭐⭐⭐]
오늘의 포스팅 본문에는 사용자가 선택한 [대분류 스타일: {theme_desc}] 기반의 내용이 자연스럽게 가미되어야 합니다.
- ⚠️ [지능형 롤링 매칭 규칙]: 아래의 강조 후보 항목 리스트 중에서, 오직 오늘 다루는 [주제: {topic}]와 가장 긴밀하고 자연스럽게 어울리는 항목을 **AI인 당신이 직접 스스로 1~2가지** 골라내어 본문 내용 속에 물 흐르듯 유기적으로 녹여내 서술하십시오.
- 매번 똑같은 교과서적 강조 멘트를 똑같이 쓰지 말고, 오늘의 주제와 가장 높은 시너지를 낼 수 있도록 결합하십시오.
- [강조 후보 항목 리스트]:
{theme_items_list}"""

        # [④ 홈케어 팁 독립 체크박스 및 자연스러운 브릿지]
        is_hometip_enabled = ai_settings.get('blog_hometip', False)
        if is_hometip_enabled:
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
            
            # 홈케어 팁 순환 상태 관리 (파일 기반 글로벌 인덱스)
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
            
            # 다음 팁 인덱스 저장
            try:
                os.makedirs(os.path.dirname(state_file), exist_ok=True)
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump({'tip_index': (tip_index + 1) % len(home_tips)}, f)
            except Exception:
                pass
            
            print(f"✨ [BlogExpert] Sequential rotation active: Global Index {tip_index} (Selected tip: {selected_tip['name']})")
            
            smart_spice_prompt += f"""\n\n[🏠 1분 홈 케어 팁 (Home Tip) - 다정한 연결 다리(Bridge) 및 팁 지침 ⭐⭐⭐⭐⭐]
오늘 포스팅의 본문 마지막 마무리 문단 뒤에 독자가 집에서 1분 안에 손쉽게 실천할 수 있는 [1분 홈케어 팁]을 반드시 이어서 작성하십시오.
- ⚠️ [필수 지정 팁]: 오늘은 무조건 **'{selected_tip['name']}'**({selected_tip['desc']})을(를) 주제로 서술하십시오. 다른 홈케어 팁은 절대로 기술하지 마십시오.
- 🚨 [자연스러운 연결(Bridge) 강력 강제 규칙]: 
  본문 서사에서 갑자기 "오늘의 홈케어 팁입니다" 하고 뜬금없이 단락을 끊고 튀어나오는 인위적인 전개를 **100% 엄격히 금지**합니다. 
  반드시 앞의 본문 칼럼 내용(주제 관련 가치와 결론)을 다정하게 마무리하는 흐름 속에서, 
  "오늘 함께 알아본 이 유익한 정보와 효과를 일상 속에서 작은 습관으로 쉽게 시작해 보실 수 있도록, 오늘 밤 집에서 1분만 가볍게 실천해 볼 수 있는 아주 간단한 동작을 준비했습니다. 바로 '{selected_tip['name']}'입니다." 와 같이 **본문 칼럼에서 홈케어 팁으로 부드럽고 다정하게 넘어가며 자연스럽게 이어주는 연결 다리(Bridge) 멘트를 최소 2문장 이상 스스로 작문하여 자연스럽게 자연 연결**하십시오.
- 텍스트만 보고도 독자가 따라 할 수 있도록 '준비 자세, 관절 정렬, 움직임, 호흡법'을 상세하게 적어야 합니다. (분량 최소 150자 할당)
- 다른 뻔한 스트레칭 언급은 배제하고 오직 지정된 **'{selected_tip['name']}'**에만 집중하여 적으세요."""



        length_cap_instruction = """[분량 엄수 및 홍보 멘트 절대 금지 - 매우 중요 ⭐⭐⭐]
1. [최종 글자 수 목표]: AI가 작성하는 본문은 공백 포함 최소 700자 ~ 최대 900자로 길고 꽉 차게 작성하세요. (내용이 부실하면 안 됩니다.)
2. [블랙리스트 단어 원천 차단]: "최선을 다하겠습니다", "노력하겠습니다", "센터로 오세요" 등 뻔한 다짐이나 홍보성 멘트는 100% 금지합니다. 오직 가치 있는 정보와 유익한 조언만을 담백하게 남기세요.
3. [마크다운 규격 준수]: 제목은 반드시 가장 첫 줄에 한 번만 작성하고, 나머지 본문을 자연스럽게 이어가세요."""

        general_instructions = ai_settings.get('instructions', '')
        smart_ui_prompt = f"""[✍️ AI 역할 (페르소나)]: {smart_persona_prompt}
 
[💬 글쓰기 말투 (스타일)]: {smart_style_prompt}{smart_spice_prompt}

[📝 기본 글쓰기 공통 지침]: {general_instructions}"""
        # ─────────────────────────────────────────────────────────────────

        # 🟢 플랫폼 공통 및 블로그 전용 규칙 로드 (런타임 NameError 방지)
        external_rules = self._get_common_system_rules('blog')
        sport_instruction = ""  # 런타임 NameError 방지를 위해 안전하게 정의
        
        # 🟢 [홍보성 vs 정보성 스마트 지침 분기 처리]
        is_promotional = False
        if post_type_config and "is_promotional" in post_type_config:
            is_promotional = post_type_config.get("is_promotional")
        else:
            is_promotional = ai_settings.get('is_promotional', False)
            
        type_instructions = ""
        if is_promotional:
            promotional_instr = post_type_config.get('promotional_instructions', '') if post_type_config else ""
            if not promotional_instr:
                promotional_instr = user_settings.get('promotional_instructions', '')
            type_instructions = f"[홍보성 포스팅 강력 지침 ⭐⭐⭐]\n오늘의 글은 홍보성 포스팅입니다. 아래의 특별 홍보 지침을 100% 반영하여 학원/센터의 브랜드 강점과 가치 문맥을 조화롭게 작성하세요:\n{promotional_instr}"
        else:
            informational_instr = post_type_config.get('informational_instructions', '') if post_type_config else ""
            if not informational_instr:
                informational_instr = user_settings.get('informational_instructions', '')
            type_instructions = f"[정보성 포스팅 지침]\n오늘의 글은 순수 정보성 포스팅입니다. 아래의 유익한 정보 제공 및 신뢰감 형성을 돕는 지침을 반영하세요:\n{informational_instr}"

        # 🟢 [날씨 데이터 수집 및 위치 사전 정제 - 런타임 순서 모순 치유 ⭐⭐⭐]
        is_forecast = self._check_is_forecast(target_time)
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
        
        refined_location = self._refine_location(weather_loc) if weather_loc else "우리 동네"
            
        system_message = f"""당신은 주어진 주제에 관해 깊이 있는 통찰과 유용한 정보를 독자에게 전달하는 전문 칼럼니스트이자 신뢰감 있는 정보 큐레이터입니다.
[필독: 오늘 정보] {current_dt_info} (⚠️ 반드시 이 날짜, 요일, 시간대를 기준으로 작성하세요.)

{past_guideline}

{outdoor_instruction}

- [페르소나: 다정하고 전문적인 고품격 정보 칼럼니스트 및 분야별 전문가]
- 말투: 군더더기 없이 깔끔하고 담백한 말투 (~해요, ~네요, ~하죠?)
- [호칭 원칙]: 본문 내에서 운영자나 지도 주체를 지칭해야 하는 경우, 어색한 호칭 대신 '전문 지도자', '전문가' 등 자연스러운 범용 칭호를 사용하십시오. (⚠️ '에디터', '큐레이터' 등 낯선 외래 직함은 사용 금지)
- [주제 우선 원칙]: 오직 주어진 [주제: {topic}]에 가장 충실하게 글을 풀어내십시오. 주제가 핫이슈나 일반 지식인 경우 무리하게 건강이나 운동 이야기로 연결하지 마세요.
{sport_instruction}

- [종목/분야 자연스러운 언급]: 주제가 건강/피트니스와 관련된 경우에만 사용자가 명시한 종목('{user_sports}')을 자연스럽게 반영하고, 그 외의 일반 지식/시사 주제일 경우 억지로 운동 종목이나 신체 활동을 끼워넣지 마십시오.
- [특정 상호 언급 절대 금지]: 본문 내에는 특정 상호, 브랜드, 체육관 이름을 절대로 언급하지 마세요. (첫 문장과 마지막 슬로건에 이미 들어갈 수 있으므로 본문에서는 완전히 배제합니다.)
- [홍보 멘트 절대 금지 ⭐⭐⭐]: "방문해 보세요", "상담받으러 오세요", "최선을 다해 안내하겠습니다" 등 상업적인 유도 멘트나 뻔한 다짐 문구는 100% 금지합니다. 오직 가치 있고 유익한 정보로만 지면을 꽉 채우십시오.

- [글쓰기 스타일]: **객관적이고 신뢰감 넘치는 담백한 칼럼 서술**. 작위적이고 과장된 감탄사나 칭찬은 지양하고, 주제의 유익한 원리와 팁을 신뢰도 높게 전달하는 시선을 유지하세요.
- [체류시간 최적화]: 억지로 가상의 개인 사례를 지어내지 말고, 오늘 다루는 주제의 핵심 개념, 생리학적/사회적 원리, 혹은 실질적인 꿀팁과 장점을 독자가 확실히 이해하고 체감할 수 있도록 논리적이고 깊이 있게 서술하세요.
- [제목 규칙 및 복제 절대 금지 ⭐⭐⭐]: **강력한 클릭 유발형 제목** (20~35자 내외). 교과서적이고 뻔하거나 심심한 제목(예: '~~가 필요한 이유', '~~의 중요성')은 **전면 금지**합니다. 독자가 보자마자 정보로서의 깊은 전문성과 호기심을 느끼게 만드는 강렬한 카피라이팅 기법을 적용하세요.
    * ⚠️ [경고: 예제 복사 금지]: 아래 예시 제목은 구조적 '참고용' 템플릿일 뿐입니다. 예시 문장 그대로를 단 한 글자도 바꾸지 않고 똑같이 출력하는 행위는 **100% 철저히 금지**합니다. 반드시 오늘의 [주제: {topic}]를 응용하여 독창적인 제목을 직접 지으세요!
    * 추천 제목 공식 예시 (반드시 오늘 주제인 {topic}에 맞추어 변형할 것):
      - "하루 10분 [주제]로 일상의 밸런스를 지키는 3가지 법칙"
      - "[주제]를 통해 알아보는 핵심 원리와 긍정적 효과"
      - "바쁜 일상 속, 현대인을 위한 [주제] 관련 유익한 솔루션" 등
- [완전 금지 및 가상 사례 창작 절대 금지 ⭐⭐⭐]: "예를 들어", "예를 들면", "결과적으로", "결론적으로", "요약하자면", "놀라운 변화", "기적 같은", "주목할 만해요" 등 AI 접속사/번역투 표현을 완전히 금지합니다. 또한, 가상의 개인 성공 미담을 지어내어 서술하는 것을 100% 금지합니다. 이는 독자에게 매우 어색하고 작위적인 느낌(거짓 글)을 줍니다.
    * ⚠️ [가상 특별 이벤트 날조 100% 절대 금지 ⭐⭐⭐⭐⭐]: 오늘의 주제({topic})가 특정 행사나 대회가 아님에도 불구하고, "다가올 대회 준비에 집중한다", "이번 주에 있을 심사를 준비한다", "특별 수업이 열렸다" 등 주제에 명시되지 않은 **가상의 어떠한 특별 활동, 대회, 심사, 캠프, 행사 서사도 지어내어 쓰는 것을 100% 엄격히 금지**합니다. (가짜 스토리는 포스팅 신뢰도를 완전히 파괴합니다.) 주제가 일반 이론/기술/이슈 내용이면 100% 오직 보편적인 일상의 사실과 원리만을 사실적으로 담아내어야 합니다.
    * 그 대신, 해당 주제를 처음 접하거나 실천할 때 겪게 되는 일반적인 상황과, 이를 지혜롭게 극복하여 유익함을 얻어가는 보편적인 일상의 흐름을 차분하고 담백하게 서술하세요.

[절대 엄수 사항 - 첫 인사 및 날씨 안부 구성]
🚨 [포스팅 출력 레이아웃 강제 규칙 - 매우 엄격 ⭐⭐⭐⭐⭐]
- 당신이 출력하는 전체 포스팅 텍스트는 반드시 다음의 **[제목]**과 **[본문]** 마커 형식을 100% 준수해야 하며, 절대로 다른 곳에 글이나 텍스트를 배치해서는 안 됩니다:
  
  [제목]
  오늘의 주제와 관련된 클릭 유발형 제목 1줄 작성 (⚠️ 날씨나 안부는 절대로 제목에 적지 마십시오. 100% 원천 전면 금지)
  
  [본문]
  오늘 {refined_location}은 기온이 [기온]도에 하늘이 [날씨상태]인 {time_name}이네요. (⚠️ 날씨 안부는 오직 여기에만, 본문 첫 문단 딱 1문장으로 작성되어야 합니다.)
  
  (여기에 빈 줄을 두고 두 번째 문단부터 독립적인 주제 시작...)

1. **초간단 기상 팩트 안부 (도입부 - 매우 엄격 ⭐⭐⭐⭐⭐)**:
   - 🚨 **[주관적 감상 100% 원천 금지]**: "더운 편이지만", "활동하기 좋은 날씨네요", "쌀쌀한 기운이 감돌아" 등 AI가 자의적으로 날씨를 해석하거나 감상을 더하는 문장을 단 한 줄이라도 작성하는 것을 100% 엄격히 금지합니다.
   - 날씨 인사는 화려한 수식어 없이 오직 제공된 날씨 데이터(기온, 하늘 상태, 미세먼지 등)를 기반으로 건조하게 팩트만 1문장 작성하되, **바로 뒤에 이어지는 두 번째 문장에 '날씨 체감(덥다/춥다)과 무관한 다정한 응원 안부'를 딱 1줄 추가하여 부드럽게 본문으로 연결**하세요.
   - (작성 예시: "오늘 양양읍은 기온이 25도에 미세먼지는 좋음, 하늘은 흐린 오후네요. 이런 날씨 속에서도 각자의 자리에서 최선을 다하고 계실 부모님들을 응원하며, 오늘은 [주제]에 대해 이야기해 볼까 합니다.")
   - 🚨 [날씨 인사의 본문 강제 종속 락(Lock)]: 날씨 인사는 무조건 **`[본문]` 마커 바로 아래 첫 줄**에만 배치되어야 하며, `[제목]` 마커 안이나 제목보다 먼저(글의 맨 첫머리에) 작성되는 행위를 **100% 절대 원천 금지**합니다. (날씨 팩트가 제목이 되는 즉시 블로그 품질이 심각하게 훼손됩니다.)
   - 🚨 [가짜 수치 날조 절대 금지 ⭐⭐⭐⭐⭐]: 날씨 문장을 작성할 때 임의의 기온 수치나 하늘 상태를 **절대로 스스로 지어내지 마십시오**. 날씨 안부는 반드시 [System: 날씨 정보]로 제공된 실제 데이터 속 수치만을 그대로 사용해야 합니다. 
   - ⚠️ [상투적인 AI 날씨 서사 및 건강/업종 훈화 권유 100% 금지]: "수련하기 딱 좋은 날씨네요", "땀 흘리러 오세요" 등 날씨를 구실 삼아 특정 업종을 엮거나 행동을 권유하는 멘트를 **100% 원천 금지**합니다. 오직 날씨 정보 중심의 첫 인사 1문장으로 마침표를 찍고 첫 문단을 완전히 끝내십시오.
2. **독립적 구성 및 날씨 격리 원칙 (매우 중요 ⭐⭐⭐⭐⭐)**: 날씨 인사는 오직 날씨와 안부에만 집중하여 1문장의 **독립된 첫 번째 문단**으로 반드시 완벽하게 마침표와 함께 종결해야 합니다. 날씨 인사와 본문 주제를 억지로 엮어 연결하지 마세요.
   - 🚨 [날씨-본문 및 특정 업종 결합 원천 금지 ⭐⭐⭐⭐⭐]: 날씨 인사 문단 내에서 혹은 날씨 인사 직후에 '도장', '체육관', '학원', '센터', '매장', '가게', '수련' 등의 특정 업종 명칭이나 활동 공간을 날씨 상황과 엮는 서사를 작성하는 행위를 **100% 절대 금지**합니다. 날씨 인사는 100% 오직 순수한 계절의 흐름, 당일의 날씨 상태, 이웃과의 정다운 안부 문구로만 단독 구성하십시오.
3. **인과관계 결합 및 연결어/지시어 절대 금지 (매우 중요 ⭐⭐⭐⭐⭐)**: 날씨 인사를 마친 뒤 새로운 문단(본문)이 시작될 때, 이전의 날씨 인사와 엮으려는 어떠한 기온, 날씨, 시간 관련 연결어나 지시어(예: "이런 기온 속에서~", "선선한 날씨 속에~", "이런 날씨이지만~", "쌀쌀한 기온에도~", "운동하기 딱 좋은 날씨에~" 등)를 본문 첫 문장에 쓰는 행위를 100% 원천 금지합니다. 날씨 문단을 종결한 후, 두 번째 문단(본문)은 완전히 독립된 오늘의 주제로 직접적이고 과감하게 새출발하십시오.
4. **[본문 첫 줄 시작 단어 제약 락(Lock) ⭐⭐⭐⭐⭐]**: 날씨 인사가 끝나면 다음 문단(본문)이 시작될 때, 본문 첫 번째 문단의 첫 단어(첫머리)로 특정 업종 공간 명칭이나 시간대 명칭을 단어로 사용해 문장을 시작하는 것을 **100% 원천 전면 금지**합니다. 본문은 오직 오늘의 주제나 이론, 보편적 지식 정보에 관한 일반론적이고 유익한 내용(예: "현대인의 삶의 질을 높이는...", "올바른 밸런스를 잡는 기법은...")으로 새롭고 객관적이게 문단을 열어야 합니다.
5. **[발행 예약 시간대 현장 결합 모순 차단 락(Lock) ⭐⭐⭐⭐⭐]**: 예약/스케줄러 포스팅의 발행 시간대 정보(예: "점심시간", "이른 아침", "새벽", "늦은 밤" 등)를 실제 현장 활동/수련 묘사와 엮는 것을 **100% 전면 차단**합니다. 발행 시간대 명칭은 첫 도입부의 "날씨 인사"에서만 오직 다정한 안부의 일부로 한정해 사용하고, 본문 묘사에서는 시간대 단어를 결합하지 않고 보편적인 일상 서사로만 작성하세요.
6. **자연스러운 주제 전환**: 날씨 인사가 끝나면 강제로 전환 문구를 쓰지 말고, 본문 주제로 완전히 독립적으로 자연스럽게 흘러가도록 하세요. 본문의 첫 문장은 오직 오늘의 주제(개념, 가치, 기술 원리 등)에 관한 순수하고 독자적인 이야기로만 새롭게 문단을 열어야 합니다. **⚠️ "오늘은 ~에 대해", "오늘의 ○○" 형식의 시점 특정 전환 표현은 절대 사용하지 마세요.**
    - ⚠️ [발행 시간과 활동 시점의 모순 절대 금지 (시간적 가상 모순 방지 - 매우 엄격 ⭐⭐⭐⭐⭐)]: 포스팅 예약 발행 시간(예: 아침 7시, 새벽, 밤 등)에 맞추어 실제 활동 현실과 맞지 않는 시간적 가상 모순 묘사를 **100% 절대 엄격히 금지**합니다. 아침이나 새벽에 발행되는 글이라도, 본문 내 묘사는 발행 시간대를 활동 시점과 결합하지 않는 현재 진행형/보편적 묘사를 하거나, "최근의 활동", "일반적인 상황" 같이 시간적으로 격리하십시오. 시간 모순 표현을 쓴 즉시 글 전체의 신뢰도가 무너집니다.
    - ⚠️ [필수 - 데이터 부재 시 지침]: 만약 날씨 데이터가 제공되지 않았거나 비어있다면, 아는 척하며 가공의 수치를 절대 적지 마시고 날씨 인사를 통째로 생략한 뒤 호칭 없이 자연스럽고 다정하게 시작하십시오.
7. **[호칭 언급 절대 금지 - AI 말투 전면 배제 ⭐⭐⭐]**: 첫 도입부 및 인사말에서 직접적으로 독자를 호칭하는 대화형 표현을 **100% 금지**합니다. 호칭을 완전히 생략하고 반갑고 신선한 인간적인 말투로만 작문하여 첫 문단을 시작하세요.
8. **포스팅 구조 및 행갈이 강제화 (매우 엄격 ⭐⭐⭐)**:
    - 모바일 가독성을 극대화하기 위해, **모든 문단은 반드시 2~3문장 단위로 구성**해야 합니다. 
    - 4문장 이상 길게 이어진 문단은 가독성을 망치므로 **절대 금지**하며, 문단 내부에서는 줄바꿈(\n) 없이 문장들이 한 칸 공백으로 자연스럽게 이어지도록 완성해야 합니다.
    - 모든 잘게 쪼갠 문단 사이에는 **반드시 명확하게 빈 줄(엔터 두 번, `\n\n`)을 비워** 눈이 편안한 시각적 여백을 100% 확보하세요. 이 규칙은 타협 불가한 필수 의무 사항입니다.

[작성 규칙 및 금지 사항]
{external_rules}

[🚨 사용자 지정 지침 (UI CUSTOM INSTRUCTIONS - 최우선 순위)]
아래의 지침은 사용자가 UI에서 직접 설정한 최신 지침이며, 이전의 모든 백그라운드 규칙보다 최우선하여 100% 적용되어야 합니다.
이 지침과 이전 지침이 충돌할 경우, 반드시 아래 지침을 따르세요:

{smart_ui_prompt}

[추가 사용자 지침 (텍스트 직접 입력)]:
{type_instructions}


{length_cap_instruction}
"""
        # [🚨 실시간 구글 시트 감지 모드 전용 2단계 글쓰기 강력 지침]
        if task_type == 'detection':
            detection_instructions = f"""\n\n[🚨 실시간 구글 시트 감지 모드 전용 2단계 글쓰기 강력 지침 ⭐⭐⭐⭐⭐]
사용자가 구글 시트에 작성한 실제 주제/상황('{topic}')을 바탕으로 글을 작성하고 있습니다. 아래 2단계 프로세스를 엄수하세요:
1. **1단계 [제목 우선 설계 및 완전 확정]**:
   - 사용자가 구글 시트에 작성한 실제 상황/내용({topic})을 정밀 분석하여, 교과서적이지 않고 호기심과 큰 가치를 유발하는 독창적이고 매력적인 [제목]을 1차적으로 먼저 설계하고 마음속으로 완벽하게 확정하십시오.
2. **2단계 [제목 + 주제 유기적 동시 참조 본문 전개]**:
   - 본문 글을 작성할 때는 원래 구글 시트의 [주제: {topic}]와 1단계에서 확정한 [제목]을 동시에 정밀 참조하여 서사적 일관성을 확보하세요.
   - 제목에서 강조한 핵심 톤앤매너와 키워드가 본문 내용 속에 어색함 없이 깊이 있고 유기적으로 스며들도록 구성하여, 제목과 본문이 100% 동기화되게 하십시오. 겉도는 가짜 내용 작성을 전면 금지합니다."""
            system_message += detection_instructions
        # 실시간 정보 주입
        search_results = self._search_brave(topic)
        if search_results:
            system_message += f"\n\n[System: 실시간 검색 결과]\n{search_results}"

        # 지능형 훅 (위에서 사전 빌드 완료)
        if weather_loc:
            weather_hook = self._build_weather_hook_message(weather_loc, is_forecast, 'blog', target_time=target_time, delta_days=delta_days)
            if weather_hook: system_message += weather_hook

        # [마무리 인사 차별화] - task_type별로 완전 분리 처리
        if task_type == 'detection':
            # detection 타입: 고정 문구를 AI가 그대로 출력하도록 강제
            _detection_closing_text = "오늘의 생생한 분위기를 사진으로 담았습니다. 현장 안내 및 정보 수집에 좀 더 집중하다 보니 사진 초점이나 흔들림이 다소 매끄럽지 않은 부분 너른 양해를 부탁드립니다."
            closing_instruction = f"""[글의 핵심 맺음말 문구 강제 규격]:
⚠️ [중요]: 홈케어 팁과 본문 설명이 도중에 잘리지 않도록 끝까지 다정하게 작성하여 글을 완전히 끝맺음하십시오.
그렇게 모든 글 작성이 자연스럽게 완료된 후, 가장 마지막 줄에 아래의 안내 멘트를 **절대 임의 수정 없이 있는 그대로 덧붙이며 마무리**하십시오.
"{_detection_closing_text}"
"""
        else:
            # 일반/예약 타입: AI에게 작성 지침만 전달 (고정 문구 없음 → 지침 텍스트 출력 버그 원천 차단)
            closing_instruction = """[고품격 정보제공형 맺음말 작성 지침 ⭐⭐⭐]:
단순히 정보를 나열하며 툭 끊어지는 어색한 마무리(예: '도움이 되었길 바랍니다.', '마치겠습니다.')는 **절대 금지**합니다.
오늘 다룬 유익한 정보와 팁이 독자 스스로의 일상에 어떤 실질적인 변화를 줄 수 있는지, 따뜻하고 신뢰감 있는 어조로 2~3문장을 자연스럽게 직접 작성하십시오.
🚨 [맺음말 자기 지칭 완전 금지]: "전문가는", "전문 지도자는", "에디터는", "저희는" 등 필자 자신을 주어로 내세워 마무리하는 문장은 **100% 원천 금지**합니다. 맺음말의 주어는 반드시 독자("여러분", "일상", "오늘의 정보" 등)여야 합니다.
(단, 광고 멘트·상업적 연락처·방문 유도 표현은 완전 배제하세요.)
🚨 [슬로건/표어 임의 창작 절대 금지 ⭐⭐⭐⭐⭐]: AI가 스스로 체육관이나 단체의 슬로건, 표어(예: "몸은 튼튼하게 마음은 바르게" 등)를 창작하여 덧붙이는 행위를 100% 엄격히 금지합니다.
"""

        # 사용자 프롬프트 (홈케어 팁 다이렉트 주입 엔진 탑재)
        hometip_user_instruction = ""
        if is_hometip_enabled:
            hometip_user_instruction = f"""
  * ⚠️ [필수: 🏠 1분 홈 케어 팁 자연스러운 녹여내기 요구 ⭐⭐⭐⭐⭐]:
    - 앞서 작성한 본문 칼럼의 풍성한 전문 정보 분량(700~900자)과 기상 날씨 팩트 인사 등의 품질을 100% 철저히 유지하십시오. 다른 부분이 부실해지거나 요약되는 현상을 엄격히 금지합니다.
    - **[중요: 인위적인 머리말/제목 금지 락(Lock)]**: 본문 끝에 홈케어 팁을 작성할 때 '[홈케어 팁]', '[1분 홈케어]', '홈케어 팁:' 등 **인위적인 대괄호 타이틀이나 소제목 머리말을 절대로 쓰지 마십시오**. 
    - 본문 칼럼의 결론 문단에서 "오늘 함께 알아본 이 유익한 정보와 효과를 일상 속에서 작은 습관으로 쉽게 시작해 보실 수 있도록, 오늘 밤 집에서 1분만 가볍게 실천해 볼 수 있는 아주 간단한 동작을 준비했습니다. 바로 '{selected_tip['name']}'입니다." 와 같이 자연스럽게 이어주는 다정한 연결 다리(Bridge) 멘트를 최소 2문장 이상 작성하여 **마지막 문단에 완전히 한 몸으로 자연스럽게 녹여내십시오.**
    - 이어서 독자가 텍스트만 보고도 따라 할 수 있도록 '{selected_tip['name']}'의 '준비 자세, 관절 정렬, 움직임, 호흡법'을 상세하게 적어(150자 이상) 글 전체를 따뜻하게 완결하십시오. (기계적인 문단 분할 없이 하나의 다정한 마무리 이야기 흐름으로 풀어내야 합니다.)"""

        base_prompt = f"""주제: {topic}
형식: [제목], [본문], [태그] 섹션으로 구분하여 작성하세요.
- [제목]: 독자의 깊은 공감과 유익한 가치를 제공하는 독창적이고 매력적인 제목
  (구조 참고용 예시: "하루 10분 주제상황 속 내 몸을 지키는 3가지 기본 법칙", "틀어진 골반을 바로잡는 운동법의 척추 정렬 효과", "오늘 주제 운동의 진짜 신체 변화와 건강 효과의 생리학적 의미" 등)
- [본문]: 주제('{topic}')를 운동생리학적/생활건강학적으로 다정하고 신뢰감 있게 풀어내며 공감을 일으키는 본문 칼럼 내용{hometip_user_instruction}
- [태그]: 글과 유기적으로 긴밀히 매칭되는 태그 정확히 15개 (예: 주제 관련 단어, 운동 명칭, 건강 정보 등)
  ※ 매우 중요: 본문 작성이 끝난 후, 반드시 맨 마지막 줄에 '[태그]' 글자를 쓰고, 그 아래에 해시태그 형식으로 태그 15개를 출력하세요. (예: #태그1 #태그2)

{closing_instruction}
"""

        # 🔄 사용자가 설정창에서 체크(선택)한 모델 리스트 동적 로드 (관장님 최종 피드백 반영 ⭐⭐⭐)
        selected_model_ids = []
        if post_type_config and post_type_config.get("selected_models"):
            selected_model_ids = post_type_config.get("selected_models")
            
        if not selected_model_ids:
            selected_model_ids = ai_settings.get('selected_models', [])
            
        # 만약 사용자가 아무것도 선택하지 않았다면, 오리지널 기본 모델 리스트로 폴백
        if not selected_model_ids:
            selected_model_ids = ["gemini-2.5-pro", "gemini-2.5-flash", "gpt-4o", "gpt-4o-mini"]
            
        models_to_use = []
        for mid in selected_model_ids:
            # Config.AI_MODELS에서 provider 정보 동적 탐색 (기본값 openai)
            provider = Config.AI_MODELS.get(mid, {}).get("provider", "openai")
            models_to_use.append({"provider": provider, "model": mid})

        start_model_index = self.current_model_index
        for i in range(len(models_to_use)):
            model_idx = (start_model_index + i) % len(models_to_use)
            model_cfg = models_to_use[model_idx]
            provider = model_cfg["provider"]
            model_name = model_cfg["model"]

            if provider == "openai" and not self.api_key:
                continue
                
            gemini_key = self.gemini_api_key
            if post_type_config and post_type_config.get("gemini_api_key"):
                gemini_key = post_type_config.get("gemini_api_key")
            
            if provider == "gemini" and not gemini_key:
                continue

            try:
                logger.info(f"🔄 [BlogExpert] Generating content using backup loop model: {model_name} (Index: {model_idx})")
                
                if provider == "openai":
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": base_prompt}],
                        temperature=0.7, max_tokens=2000
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_message, base_prompt, api_key=gemini_key)
                else: continue

                if self._validate_content(content):
                    title, body, tags = self._parse_content(content)
                    
                    if len(title) > 50:
                        title = title[:47] + "..."
                        
                    body = self._apply_stability_filter(body, 'blog')
                    body = self._apply_blog_readability_filter(body)
                    
                    # ⚠️ [지침 유출 방지 락(Lock)] 지침 대괄호 텍스트 및 맺음말 타이틀 노출 잔재 완전 제거
                    body = re.sub(r'\[\s*(?:고품격|고풀겨|정보제공형|맺음말|작성지침|지침)[^\]]*\]\s*:?', '', body)
                    body = re.sub(r'^\s*(?:고품격|고풀겨|정보제공형|맺음말|작성지침|지침)\s*:\s*', '', body, flags=re.MULTILINE)
                    body = body.strip()
                    
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)
                    
                    cleaned_tags = [t.strip().replace('#', '') for t in tags if t.strip()]
                    
                    return {
                        "title": title,
                        "content": body,
                        "tags": cleaned_tags,
                        "model": model_name
                    }
            except Exception as e:
                logger.error(f"블로그 생성 오류 ({model_name}): {e}")
                continue

        return self._get_dummy_content(topic)

    def _apply_blog_readability_filter(self, text: str) -> str:
        """네이버 블로그 전용 가독성 필터: 마침표마다 무조건 줄바꿈 두 번(엔터 2번) 적용하여 모바일 가독성 극대화"""
        if not text: return text
        
        # 1. 기존 줄바꿈을 공백으로 임시 치환 (문장별 재조립을 위해)
        text = text.replace('\n', ' ')
        
        # 2. 마침표(.), 느낌표(!), 물음표(?) 등을 기준으로 확실하게 쪼개기
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        processed_sentences = []
        for s in sentences:
            s_strip = s.strip()
            if not s_strip: continue
            processed_sentences.append(s_strip)
            
        # 3. 모든 문장 사이에 무조건 2번의 줄바꿈(\n\n) 적용
        final_text = '\n\n'.join(processed_sentences).strip()
        
        # 4. [본문] 마커 등 기타 마커 사이의 불필요한 공백 정리
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        
        # [홈 케어 팁]과 같은 특정 섹션 앞에는 명확히 띄워주기
        final_text = re.sub(r'([^\n])\s*(\[(?:홈\s*케어(?:\s*팁)?|홈케어)\])', r'\1\n\n\2', final_text)
        
        return final_text
