import os

def fix_blog_expert():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/modules/ai_experts/blog_expert.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find where the dates block starts
    target_start = "        # 날짜/요일/시간 정보"
    start_idx = content.find(target_start)
    if start_idx == -1:
        print("Error: Could not find date start block")
        return

    # Find where the system_message definition starts
    system_msg_start = "        system_message = f\"\"\"당신은 현대인의 건강"
    end_idx = content.find(system_msg_start)
    if end_idx == -1:
        print("Error: Could not find system_message start")
        return

    # New date, past guideline, and outdoor filter logic to replace everything from "date start block" up to "system_message start"
    new_logic = """        # 날짜/요일/시간 정보
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
            except Exception as e:
                logger.error(f"target_time ({target_time}) 파싱 중 오류: {e}")
                target_hour = now_dt.hour
                
        # Calculate actual training date based on delta_days (for past training records)
        training_dt = now_dt + timedelta(days=delta_days)
        
        days_ko = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        time_name = self._get_time_of_day_name(target_hour)
        
        # Construct detailed date context for AI
        current_dt_info = f"발행(현재) 날짜: {now_dt.strftime('%Y년 %m월 %d일')} ({days_ko[now_dt.weekday()]}) / 수련(실제) 날짜: {training_dt.strftime('%Y년 %m월 %d일')} ({days_ko[training_dt.weekday()]}) / 시간대: {time_name}"

        # Past training record tone guideline based on delta_days
        past_guideline = ""
        if delta_days < 0:
            past_guideline = f\"\"\"- [과거 수련일 회상/기록형 톤 엄수 ⭐⭐⭐]:
  * 실제 수련은 오늘이 아닌 과거 {training_dt.strftime('%Y년 %m월 %d일')} ({days_ko[training_dt.weekday()]})에 진행되었습니다.
  * 따라서, "오늘 수련을 방금 마쳤다", "오늘 아침 일찍 수련을 마쳤다"는 식의 시간적 모순을 유발하는 문구는 **절대 금지**합니다.
  * 반드시 "지난 {days_ko[training_dt.weekday()]}에 있었던", "최근 수련 모습", "지난 {training_dt.strftime('%m월 %d일')} 수련 기록"과 같이 과거를 회상하고 기록하는 따뜻한 톤으로 본문을 구성하세요.
  * 문맥 또한 과거 완료/회상 어미(~했습니다, ~했었어요, ~였답니다 등)를 적절히 조화롭게 활용하세요.\"\"\"
        else:
            past_guideline = f\"\"\"- [현재/미래 수련 톤]: 수련이 오늘 진행되거나 보편적인 도장의 일상 수련 모습을 서술하므로, 자연스럽게 시간대를 특정하지 않는 현재 진행형/보편적 묘사를 사용하세요.\"\"\"

        # Intelligent outdoor dojang environment filter based on topic keyword matching
        outdoor_keywords = ['해변', '모래사장', '운동장', '산', '야외', '공원', '캠프', '바다', '해수욕장', '강가', '숲', '야유회', '야외훈련']
        is_outdoor_topic = any(ok in topic for ok in outdoor_keywords)
        
        if is_outdoor_topic:
            outdoor_instruction = f\"\"\"- [야외 훈련 허용]: 오늘의 수련 주제('{topic}')에 야외 환경이나 장소가 명시적으로 언급되어 있습니다. 따라서, 실내 도장이 아닌 활기찬 야외 환경(예: 모래사장, 해변, 운동장 등)의 생생한 분위기 및 그에 따른 특별 훈련 모습을 자연스럽게 묘사하는 것을 허용하며 권장합니다. 억지로 실내 도장으로 제한하지 마세요.\"\"\"
        else:
            outdoor_instruction = \"\"\"- [실내 도장 수련 필수 ⭐⭐⭐]: 오늘의 주제는 보편적인 기술 수련이므로, "해변", "모래사장", "산", "운동장" 등 야외 환경에서 훈련했다는 작위적인 날조를 100% 금지합니다. 무조건 쾌적하고 안전한 **'실내 도장(Dojang)'** 환경만을 바탕으로 수련생들의 훈련과 정겨운 도장 풍경만을 서술하십시오.\"\"\"

        # ─────────────────────────────────────────────────────────────────
        # 🆕 [스마트 하이브리드 프롬프트 자동 조립 엔진]
        # UI에서 선택한 드롭다운/체크박스 값을 강력한 AI 지침으로 번역
        # ─────────────────────────────────────────────────────────────────
        ai_settings = self._load_settings()  # gpt_settings.json 로드
        
        # 🆕 [실시간 UI 및 user_settings.txt 최우선 병합]
        # user_settings.txt에 실시간 자동 저장되는 UI의 모든 양념/설정값들을 ai_settings에 병합하여 예약 발행 시에도 100% 동기화합니다.
        if user_settings:
            for k, v in user_settings.items():
                if k.startswith('spice_') or k.startswith('blog_') or k in ['is_promotional']:
                    ai_settings[k] = v
        
        # 🆕 [실시간 UI 설정값 강제 연동 혁신] 사용자가 UI 대시보드에서 체크한 최신 양념/설정값들을 파일 값 위에 최우선 강제 덮어쓰기 연동함!
        if post_type_config:
            for k, v in post_type_config.items():
                # 스파이스(spice_) 및 스타일 모드, 페르소나 모드 등 UI의 모든 실시간 제어 인자를 안전하게 수용
                if k.startswith('spice_') or k.startswith('blog_') or k in ['is_promotional']:
                    ai_settings[k] = v

        # [① 페르소나 (역할) 번역] - UI 드롭다운 blog_persona_mode 값을 AI 지침 텍스트로 변환
        _persona_prompt_map = {
            'expert_sport':  f"당신은 {user_sports} 분야의 전문 무도 사범입니다. 수련생(현대인, 성인 수련생 및 아이들 모두)의 신체 변화와 기술적 원리를 과학적이고 전문적으로 서술하는 전문가 시점으로 작성하세요.",
            'sabeom':        f"당신은 현장을 직접 지도하는 열정적인 사범님입니다. 오늘 수련실에서 수련생(아이들과 성인 모두)들과 함께한 생생한 현장 분위기와 수련생들의 땀방울, 변화하는 모습을 따뜻하고 생동감 있게 전달하세요.",
            'parent_friend': f"당신은 수련생과 학부모 모두의 고민을 깊이 이해하는 다정한 수련/교육 파트너입니다. 독자의 입장에서 공감하고, 실질적으로 도움이 되는 건강 및 신체 단련 정보를 친근한 이웃처럼 전달하세요.",
        }
        blog_persona_mode = ai_settings.get('blog_persona_mode', 'expert_sport')
        smart_persona_prompt = _persona_prompt_map.get(blog_persona_mode, _persona_prompt_map['expert_sport'])

        # [② 글쓰기 스타일 번역] - UI 드롭다운 blog_style_mode 값을 AI 말투 지침으로 번역
        _style_prompt_map = {
            'haeyo':     "군더더기 없이 깔끔하고 다정다감한 대화체 말투 (~해요, ~에요, ~하죠?)로 독자에게 친근하게 다가가는 어조로 작성하세요. 딱딱한 군대식 말투(~입니다, ~합니다만 반복)는 절대 금지합니다.",
            'imnida':    "전문적이고 신뢰감을 주는 정중한 격식체 말투 (~입니다, ~합니다)를 사용하여 신뢰도가 높고 진중한 칼럼이나 보도자료처럼 격조 있게 작성하세요. 어조가 오락가락하지 않게 유지하세요.",
            'half_half': "친근함과 전문성을 동시에 확보할 수 있도록, 다정한 대화체(~해요, ~네요)와 정중한 격식체(~입니다, ~합니다)를 5:5 비율로 자연스럽게 섞어서 조화롭게 작성하세요. (예: 설명 부분은 ~입니다로 신뢰감 있게 서술하고, 독자의 공감을 이끌어내는 문장이나 마지막 격려 문장은 ~해요로 다정하게 작성)"
        }
        blog_style_mode = ai_settings.get('blog_style_mode', 'haeyo')
        smart_style_prompt = _style_prompt_map.get(blog_style_mode, _style_prompt_map['haeyo'])

        # [③ 본문 강조 테마 (스파이스) 번역] - UI 드롭다운 blog_theme 값을 AI 지침 텍스트로 변환
        _theme_prompt_map = {
            'spice_growth':      "\\n\\n[🔥 성장판 자극 운동 원리 강조 지침]\\n오늘 포스팅 본문에는 우리 아이들의 성장판을 안전하게 자극하는 운동 원리와 뼈/근육 성장 메커니즘을 운동 생리학 관점에서 자연스럽게 녹여내세요. 줄넘기와 점프 운동이 주는 긍정적 자극을 강조하세요.",
            'spice_posture':     "\\n\\n[🔥 자세 교정 & 코어 강화 강조 지침]\\n오늘 포스팅 본문에는 굽은 등, 틀어진 골반 등 현대 어린이와 성인 수련생들이 겪는 자세 문제를 올바른 척추 정렬과 코어 근육 강화를 통해 어떻게 교정할 수 있는지 자연스럽게 녹여내세요.",
            'spice_stamina':     "\\n\\n[🔥 기초 체력 & 면역력 강조 지침]\\n오늘 포스팅 본문에는 기초 체력 증진이 면역 체계 강화와 일상 속 활력에 미치는 긍정적 영향을 생리학적 관점에서 전문적으로 강조하세요.",
            'spice_obesity':     "\\n\\n[🔥 소아비만 예방 강조 지침]\\n오늘 포스팅 본문에는 현대 사회의 소아비만 문제가 단순 체중 감량이 아닌 전신 대사량 증진과 복합 신체 활동을 통해 어떻게 예방되고 해소되는지 서술하세요.",
            'spice_brain':       "\\n\\n[🔥 두뇌 발달 & 좌우뇌 협응 강조 지침]\\n오늘 포스팅 본문에는 좌우 뇌 세포 연결을 활성화하는 교차 협응 운동(예: 좌우대칭 발차기, 양손 교차 줄넘기 등)이 뇌 발달과 인지력 향상에 미치는 영향을 서술하세요.",
            'spice_focus':       "\\n\\n[🔥 집중력 강화 강조 지침]\\n오늘 포스팅 본문에는 수련 중 호흡과 시선 처리, 정밀한 동작 제어가 아이들의 주의집중력을 강화하고 산만한 태도를 차분히 극복하는 데 미치는 영향을 전문적으로 담으세요.",
            'spice_happy':       "\\n\\n[🔥 스트레스 해소 강조 지침]\\n오늘 포스팅 본문에는 활발한 전신 신체 활동이 행복 호르몬(도파민, 엔도르핀) 분비를 촉진하고 학업/일상 스트레스를 건전하게 풀어내어 정서적 안정을 주는 원리를 묘사하세요.",
            'spice_confidence':  "\\n\\n[🔥 자존감 & 자신감 강조 지침]\\n오늘 포스팅 본문에는 작은 성공 체험(어려운 동작 완수, 격파 성공 등)이 아이들의 자아존중감을 높이고 당당한 자신감을 기르는 데 미치는 심리적 효과를 강조하세요.",
            'spice_social':      "\\n\\n[🔥 배려 & 협동 강조 지침]\\n오늘 포스팅 본문에는 짝 수련이나 단체 줄넘기 등 공동의 목표를 달성하는 과정을 통해 아이들이 타인을 배려하고 협동하는 사회성을 어떻게 키워나가는지 묘사하세요.",
            'spice_manners':     "\\n\\n[🔥 바른 인사와 예절 강조 지침]\\n오늘 포스팅 본문에는 도장 내에서 행해지는 바른 인사법과 타인을 존중하는 예절 교육이 일상생활과 인성 형성에 어떤 긍정적 습관으로 자리 잡는지 서술하세요.",
            'spice_safety':      "\\n\\n[🔥 안전 교육 & 위기 대처 강조 지침]\\n오늘 포스팅 본문에는 낙법이나 호신술 수련을 통해 신체 조절 능력을 극대화하여 예기치 못한 낙상 사고나 위험 상황에서 스스로를 보호하는 위기 대처 원리를 담으세요."
        }
        blog_theme = ai_settings.get('blog_theme', 'none')
        smart_spice_prompt = _theme_prompt_map.get(blog_theme, "")

        # [④ 홈케어 팁 독립 체크박스] - 중복 방지 순차 알고리즘 연동 (상태: 적용)
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
                {"name": "버드독 스트레칭 (척추 정렬 및 밸런스)", "desc": "네발기기 자세에서 한쪽 손과 반대쪽 발을 수평으로 뻗어 척추 기립근과 코어 밸런스를 균형 있게 다지는 운동"},
                {"name": "코브라 자세 (굽은 등 및 가슴 신전)", "desc": "엎드린 상태에서 손으로 바닥을 밀며 상체를 들어 올려 굽은 등과 가슴을 시원하게 펴주는 스트레칭"},
                {"name": "이상근 스트레칭 (엉덩이 피로 및 골반 통증 완화)", "desc": "누운 자세에서 한쪽 다리를 숫자 4 모양으로 걸쳐 가슴 쪽으로 당기며 엉덩이 심층 근육을 이완하는 동작"},
                {"name": "아기 자세 (척추 및 어깨 이완)", "desc": "무릎을 꿇고 엎드려 이마를 바닥에 대고 양팔을 뻗어 하루 동안 쌓인 척추와 어깨 긴장을 녹이는 휴식 자세"},
                {"name": "체어 포즈 (의자 자세 코어 강화)", "desc": "가상의 의자에 앉듯이 골반을 낮추고 양손을 하늘로 뻗어 허벅지와 등 근육을 동시에 강화하는 하체 협응 동작"},
                {"name": "슈퍼맨 자세 (등 기립근 및 후면 사슬 강화)", "desc": "엎드린 상태에서 상체와 하체를 동시에 들어 올려 척추 기립근과 둔근 전체를 조여주는 효과적인 등 운동"},
                {"name": "러시안 트위스트 (옆구리 및 외복사근 자극)", "desc": "상체를 비스듬히 눕힌 채 양손을 모아 좌우로 몸통을 회전하며 복부와 허리 라인을 탄탄하게 잡아주는 동작"},
                {"name": "장요근 스트레칭 (골반 앞쪽 및 장요근 이완)", "desc": "한쪽 무릎을 바닥에 대고 런지 자세에서 골반을 앞으로 지긋이 밀어 굽은 자세로 단축된 골반 앞쪽 근육을 늘리는 동작"},
                {"name": "발바닥 족저근막 마사지 (테니스공 롤링)", "desc": "발바닥 아래에 테니스공이나 마사지 볼을 두고 체중을 실어 굴리며 발바닥 전체의 누적 피로와 족막을 이완하는 기법"},
                {"name": "벽 슬라이드 (굽은 등 및 라운드 숄더 교정)", "desc": "벽에 등, 엉덩이, 팔꿈치와 손등을 완전히 밀착하고 위아래로 쓸어올리며 굳어진 날개뼈 가동성을 살리는 운동"},
                {"name": "벽 짚고 종아리 늘리기 (아킬레스건 스트레칭)", "desc": "벽을 짚고 서서 한쪽 다리를 뒤로 길게 뻗고 뒤꿈치를 바닥에 붙여 종아리와 아킬레스건을 곧게 늘려주는 스트레칭"},
                {"name": "와이퍼 자세 (골반 관절 가동성 증진)", "desc": "바닥에 앉아 무릎을 세우고 양 다리를 와이퍼처럼 좌우 바닥 방향으로 번갈아 쓰러뜨리며 골반 가동 범위를 넓히는 자세"},
                {"name": "목 및 승모근 스트레칭 (거북목 증후군 해소)", "desc": "한 손으로 머리 반대쪽을 감싸 귀가 어깨에 닿는 느낌으로 지긋이 당겨주어 목 덜미와 승모근 긴장을 풀어주는 팁"}
            ]
            
            target_day = now_dt.day
            tip_index = (target_day * 3 + int(post_order)) % len(home_tips)
            selected_tip = home_tips[tip_index]
            
            print(f"✨ [BlogExpert] Sequential rotation active: Day {target_day}, Order {post_order} -> Index {tip_index} (Selected tip: {selected_tip['name']})")
            
            smart_spice_prompt += f\"\"\"\\n\\n[🏠 홈 케어 팁 (Home Tip) - 강력 지침 ⭐⭐⭐]
오늘 포스팅 마지막 부분에 부모님이나 수련생이 집에서 함께 1분 안에 실천할 수 있는 [초간단 홈케어 팁]을 1가지 반드시 작성하세요.
- ⚠️ [필수 지정 팁]: 오늘은 무조건 **'{selected_tip['name']}'**({selected_tip['desc']})을(를) 주제로 서술하세요. 다른 홈케어 팁은 절대로 작성하지 마세요.
- 텍스트만 보고도 독자가 따라 할 수 있도록 '준비 자세, 관절 정렬, 움직임, 호흡법'을 전문 사범님처럼 상세하게 적어야 합니다. (분량 최소 150자 할당)
- 다른 뻔한 스트레칭 언급은 배제하고 오직 지정된 **'{selected_tip['name']}'**에만 집중하여 적으세요.\"\"\"

        length_cap_instruction = \"\"\"[분량 엄수 및 홍보 멘트 절대 금지 - 매우 중요 ⭐⭐⭐]
1. [최종 글자 수 목표]: AI가 작성하는 본문은 공백 포함 최소 700자 ~ 최대 900자로 길고 꽉 차게 작성하세요. (내용이 부실하면 안 됩니다.)
2. [블랙리스트 단어 원천 차단]: "최선을 다해 지도하겠습니다", "노력하겠습니다", "사랑으로 지도하겠습니다", "도장으로 오세요" 등 뻔한 다짐이나 홍보성 멘트는 100% 금지합니다. 오직 정보와 현장의 모습만 담백하게 남기세요.
3. [마크다운 규격 준수]: 제목은 반드시 가장 첫 줄에 한 번만 작성하고, 나머지 본문을 자연스럽게 이어가세요.\"\"\"

        smart_ui_prompt = f\"\"\"[✍️ AI 역할 (페르소나)]: {smart_persona_prompt}

[💬 글쓰기 말투 (스타일)]: {smart_style_prompt}{smart_spice_prompt}\"\"\"
        # ─────────────────────────────────────────────────────────────────
"""

    fixed_content = content[:start_idx] + new_logic + content[end_idx:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)
    print("Success: blog_expert.py (Part 1 - logic) has been fixed successfully!")

if __name__ == "__main__":
    fix_blog_expert()
