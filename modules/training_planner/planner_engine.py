# -*- coding: utf-8 -*-
"""
planner_engine.py
AI(GPT-4o)에게 체육관 프로필, 커리큘럼 데이터, 연령 프로필을 전달하고
전문 지도자 수준의 월간 수련계획표를 JSON으로 생성받습니다.

[완전 독립 모듈 - 기존 자동화 시스템에 영향 없음]
"""

import os
import json
import re
import random
from datetime import datetime, date
import calendar as cal_module


# ─────────────────────────────────────────────────────────
# 공휴일 데이터 연동 (modules.schedule_parser 표준 사용)
# ─────────────────────────────────────────────────────────
from modules.schedule_parser import get_holidays_for_month


def get_weekdays_in_month(year: int, month: int) -> list:
    """해당 월의 모든 날짜와 요일 정보를 반환합니다."""
    cal_module.setfirstweekday(cal_module.SUNDAY)
    _, days_in_month = cal_module.monthrange(year, month)
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    result = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        # Python weekday(): 0=월, 6=일
        wd = d.weekday()
        result.append({
            "date": d.strftime("%Y-%m-%d"),
            "day": day,
            "weekday": weekday_names[wd],
            "is_weekend": wd >= 5  # 토(5), 일(6)
        })
    return result


# ─────────────────────────────────────────────────────────
# 프롬프트 빌더
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """당신은 20년 이상의 경력을 가진 전문 무도 체육 지도자이자 수련 계획 전문가입니다.
사용자가 제공한 샘플처럼 **'불필요한 설명이 전혀 없는, 핵심 키워드 위주의 똑똑한 수련 계획표'**를 작성합니다.

[수련 계획 대원칙: 스마트 루틴]
1. 질서 있는 흐름: 각 날짜의 내용은 사용자가 지정한 4단계 루틴 카테고리 순서를 엄격히 따릅니다.
2. 매일 색다른 내용: 같은 카테고리라도 매일 똑같은 내용을 적지 말고 전문적인 용어를 사용하여 변주하세요. 
3. 주간 단위 테마 적용: 주차별로 기초 -> 숙련 -> 실전 -> 평가의 흐름을 유지하세요.

[출력 내용 및 형식 지침 - 필독!]
1. **극도의 간결함 (Zero Filler)**:
   - "오늘은 ~를 합니다", "~을 통해 건강해집니다" 같은 문장형 설명을 **절대 금지**합니다.
   - 오직 **단어 또는 짧은 구문**만 사용하세요. (예: "성장스트레칭", "에니몰드릴", "방족술 및 미션스파링")
   - "시작", "마무리", "1단계", "수련내용" 같은 머리말(Header)을 **절대** 붙이지 마세요.

2. 가독성 및 형식:
   - 각 단계는 **줄바꿈(\\n)**으로만 구분하세요.
   - 마크다운 기호(-, *, #)를 사용하지 마세요.
   - 특수문자나 이모지를 사용하지 마세요.

3. 금지 사항:
   - 시스템 식별자(@[Terminal...])를 포함하지 마세요.
   - 주말(토/일)에 이미 행사가 지정된 경우 해당 일자는 건너뛰거나 주말 행사 내용을 참고하여 작성하세요.

[출력 형식 - 반드시 준수]
반드시 아래 JSON 배열 형식만 출력하세요. 다른 설명은 절대 금지합니다.
[
  {
    "date": "2026-06-01",
    "title": "성장스트레칭\\n에니몰드릴\\n호신술 기본기\\n순발력 미션 피구"
  },
  ...
]
"""


def build_user_prompt(
    year: int,
    month: int,
    gym_profile: dict,
    age_category: dict,
    curriculum_md: str,
    special_note: str = "",
    existing_events: list = None
) -> str:
    """AI에게 보낼 사용자 프롬프트를 조립합니다."""

    holidays = get_holidays_for_month(year, month)
    weekdays = get_weekdays_in_month(year, month)

    # 이미 채워진 날짜와 제목 매핑
    occupied_map = {e["date"]: e["title"] for e in existing_events} if existing_events else {}

    # 날짜 목록 생성
    date_list_lines = []
    for wd in weekdays:
        tags = []
        is_occupied = False
        
        if wd["date"] in holidays:
            tags.append(f"🚫 공휴일({holidays[wd['date']]})")
            is_occupied = True
        
        if wd["date"] in occupied_map:
            title = occupied_map[wd["date"]]
            tags.append(f"✅ 배정됨: {title}")
            is_occupied = True
            
        if wd["is_weekend"]:
            tags.append("주말")
            # 토요일이고 비어있으면 행사 계획 가능으로 표시
            if wd["weekday"] == "토" and not is_occupied:
                status = "(빈칸 - 주말 행사 계획 가능)"
            else:
                status = " ".join(tags)
        else:
            status = "(빈칸 - 계획 필요)" if not is_occupied else " ".join(tags)
            
        date_list_lines.append(f"- {wd['date']} ({wd['weekday']}): {status}")

    gym_name = gym_profile.get("gym_name", "체육관")
    sport = gym_profile.get("sport", "무도")
    concept = gym_profile.get("concept", "")
    
    # 4단계 루틴 구성
    r1 = gym_profile.get("routine_1", "몸풀기, 스트레칭")
    r2 = gym_profile.get("routine_2", "체력강화, 보강훈련")
    r3 = gym_profile.get("routine_3", "메인 기술")
    r4 = gym_profile.get("routine_4", "마무리, 게임")
    training_routine = f"""
    1단계: {r1} (준비/몸풀기)
    2단계: {r2} (체력/강화)
    3단계: {r3} (메인 기술/수련)
    4단계: {r4} (마무리/게임)
    """

    age_name = age_category.get("name", "일반")
    age_desc = age_category.get("description", "")
    training_style = age_category.get("training_style", "")

    curriculum_section = ""
    if curriculum_md.strip():
        trimmed = curriculum_md[:4000] + ("..." if len(curriculum_md) > 4000 else "")
        curriculum_section = f"\n[체육관 커리큘럼 자료 (참고)]\n{trimmed}\n"

    # 주말 이벤트 패턴
    weekend_pattern = gym_profile.get("weekend_pattern", "없음")

    prompt = f"""[체육관 정보]
- 체육관명: {gym_name}
- 종목: {sport}
- 컨셉: {concept}
- 고정 수련 루틴: {training_routine}
- **주말 행사 목표 패턴**: {weekend_pattern}

[대상 연령]
- 카테고리: {age_name} ({age_desc})
- 수련 스타일: {training_style}

{curriculum_section}

[{year}년 {month}월 날짜 목록 및 예약 상황]
{chr(10).join(date_list_lines)}

[AI 미션 - 반드시 준수]
1. **내용 구성 우선순위**: 
   - **1순위 (최우선)**: 위 [고정 수련 루틴]에 적힌 내용을 바탕으로 계획을 세우세요. 관장님이 UI에 직접 입력한 내용이므로 가장 중요합니다.
   - **2순위 (참고)**: [체육관 커리큘럼 자료]는 1순위 내용이 비어있거나, 기술적인 전문 용어가 필요할 때만 보조적으로 참고하세요.
   - **주의**: 커리큘럼 자료에 적힌 특정 날짜나 대회명(예: 인천시 대회 등)은 실제 일정과 무관하므로 **절대 인용하지 마세요.**

2. **평일 계획**: '(빈칸 - 계획 필요)'로 표시된 모든 날짜를 4단계 루틴에 맞춰 빈틈없이 채우세요.

3. **연령별 맞춤화**:
   - **유치부/저학년**: 아주 간결하게 단어 위주로 작성하세요. (각 단계당 1~2단어)
   - **중고등/성인**: 전문 용어를 사용하여 구체적으로 작성하세요.

4. **주말 계획**: '(빈칸 - 주말 행사 계획 가능)'으로 표시된 토요일에 [주말 행사 목표 패턴]만큼 행사를 배정하세요.

5. **형식**: 오직 JSON 배열 형식만 출력하세요.
"""
    return prompt


# ─────────────────────────────────────────────────────────
# AI 호출 (기존 ai_handler 활용)
# ─────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────
# AI-하이브리드 알고리즘 (AI 패턴 설계 + 알고리즘 강제 배분)
# ─────────────────────────────────────────────────────────

def generate_plan_with_ai(
    ai_handler,
    year: int,
    month: int,
    gym_profile: dict,
    age_category: dict,
    curriculum_md: str,
    special_note: str = "",
    existing_events: list = None
) -> list:
    """
    [하이브리드 모드]
    1. AI에게 해당 월에 사용할 '수련 내용 조합(Pool)' 25~30개를 요청합니다.
    2. 알고리즘이 달력을 스캔하여 모든 빈칸(평일)에 해당 조합을 순차적으로 100% 채웁니다.
    """
    age_name = age_category.get("name", "일반")
    print(f"[Step 1] [하이브리드] {month}월 {age_name} 수련 풀 생성 시작 (상태: 시도)")

    # 1. AI에게 수련 풀(Pool) 요청 (공휴일 정보 포함하여 AI가 흐름을 인지하게 함)
    holidays = get_holidays_for_month(year, month)
    holiday_info = ", ".join([f"{d.split('-')[-1]}일({name})" for d, name in holidays.items()]) if holidays else "없음"
    
    pool = _generate_training_pool(ai_handler, month, gym_profile, age_category, curriculum_md, special_note, holiday_info)
    if not pool:
        print(f"[Step 1] [하이브리드] {month}월 수련 풀 생성 치명적 실패 - 빈 계획표 생성")
        pool = {}

    # [Step 2] [planner_engine] 수련계획 풀 후처리 및 고정 루틴 강제 보정 시작 (상태: 시도)
    print(f"[Step 2] [planner_engine] 수련계획 풀 후처리 및 고정 루틴 강제 보정 시작 (상태: 시도)")
    try:
        pool = _post_process_training_pool(pool, gym_profile)
        print(f"[Step 2] [planner_engine] 수련계획 풀 후처리 및 고정 루틴 강제 보정 완료 (상태: 성공)")
    except Exception as e:
        print(f"[Step 2] [planner_engine] 수련계획 풀 후처리 중 에러 발생 (상태: 실패) - {e}")

    # 3. 알고리즘으로 달력에 강제 배분
    final_entries = _assign_pool_to_calendar(year, month, pool, gym_profile, special_note, existing_events)
    
    print(f"[Step 3] [하이브리드] {month}월 계획 확정 (상태: 성공) - {len(final_entries)}개 날짜 채움")
    return final_entries


def _post_process_training_pool(pool: dict, gym_profile: dict) -> dict:
    """
    Post-processes the AI-generated training pool to guarantee user-defined routines
    are kept 100% exactly at their respective stage index, and sequentially routes
    empty stages using base routines in a round-robin fashion to avoid duplicate items.
    """
    weekly_routine = gym_profile.get("weekly_routine", {})
    
    # Parse base routine items for round-robin assignment
    base_routines = {}
    for i in range(1, 5):
        raw_routine = gym_profile.get(f"routine_{i}", "")
        items = [x.strip() for x in raw_routine.split(",") if x.strip()]
        if not items:
            items = [f"{i}단계 기본수련"]
        base_routines[i] = items

    # Global round-robin index per stage to maintain sequence across all sets
    rr_index = {i: 0 for i in range(1, 5)}

    processed_pool = {}
    
    for wd in ["월", "화", "수", "목", "금"]:
        processed_pool[wd] = []
        custom_routine = weekly_routine.get(wd, ["", "", "", ""])
        
        # Guarantee weekly routine length is exactly 4
        while len(custom_routine) < 4:
            custom_routine.append("")
        custom_routine = custom_routine[:4]
        
        day_pool = pool.get(wd, [])
        # Default fallback to 5 empty sets if AI returned empty pool
        while len(day_pool) < 5:
            day_pool.append("\n\n\n")
            
        for item_str in day_pool[:5]:
            # Split AI generated string by newline
            lines = [line.strip() for line in item_str.split("\n")]
            while len(lines) < 4:
                lines.append("")
            lines = lines[:4]
            
            final_lines = []
            used_today = set()
            
            for step_idx in range(4):
                stage_num = step_idx + 1
                custom_val = custom_routine[step_idx].strip()
                
                selected_val = ""
                
                if custom_val:
                    # 1. Custom input from user exists -> Keep exactly as typed
                    selected_val = custom_val
                else:
                    # 2. Empty stage -> AI's hallucination causes mixing of stages (e.g. Stage 2 item in Stage 1).
                    # Rule Enforcement: Always pick strictly from this stage's routine_pool using Round-Robin.
                    routine_pool = base_routines[stage_num]
                    
                    attempts = 0
                    max_attempts = len(routine_pool)
                    rr_val = ""
                    while attempts < max_attempts:
                        candidate = routine_pool[rr_index[stage_num] % len(routine_pool)]
                        rr_index[stage_num] += 1
                        if candidate not in used_today:
                            rr_val = candidate
                            break
                        attempts += 1
                        
                    # 관장님 규칙: 해당 단계의 풀을 오늘 다 썼더라도 절대 다른 단계에서 가져오면 안 됨!
                    # 중복이 발생하더라도 무조건 '해당 단계' 안에서만 순환하도록 강제 적용.
                    if not rr_val:
                        rr_val = routine_pool[rr_index[stage_num] % len(routine_pool)]
                        rr_index[stage_num] += 1

                    selected_val = rr_val
                        
                final_lines.append(selected_val)
                used_today.add(selected_val)
            
            if wd == "금":
                print(f"[DEBUG 금요일] custom_routine: {custom_routine}")
                print(f"[DEBUG 금요일] lines from AI: {lines}")
                print(f"[DEBUG 금요일] final_lines: {final_lines}")
                
            processed_pool[wd].append("\n".join(final_lines))
            
    return processed_pool


def _generate_training_pool(ai_handler, month: int, gym_profile: dict, age_category: dict, curriculum_md: str, special_note: str = "", holiday_info: str = "없음") -> dict:
    """AI에게 월~금 요일별로 특화된 수련 내용 조합을 5개씩 생성하도록 요청합니다."""
    
    r1 = gym_profile.get("routine_1", "준비운동")
    r2 = gym_profile.get("routine_2", "체력단련")
    r3 = gym_profile.get("routine_3", "메인수련")
    r4 = gym_profile.get("routine_4", "마무리게임")
    
    age_name = age_category.get("name", "일반")
    age_desc = age_category.get("description", "")

    system_prompt = f"""당신은 20년 경력의 무도 수련 설계 전문가입니다.
[중요 규칙]
1. 각 날짜는 반드시 4줄로 구성되어야 합니다 (1단계~4단계).
2. 관장님이 지정한 요일별 고정 루틴 내용이 있다면, 해당 요일의 5개 세트에 모두 포함시키되 나머지 비어있는 단계는 가장 잘 어울리게(변주를 주어) 채우세요.
3. [유기적 조합]: 1단계, 2단계, 3단계는 서로 뜬금없는 종목이 아니라, "오늘의 수련 테마"가 부드럽게 이어지도록 연관성 있는 종목끼리 묶어주세요.
4. [전체 항목 사용]: 관장님이 기본 설정한 쉼표로 구분된 모든 항목은 전체 요일 풀에 골고루 최소 1번 이상 사용되어야 합니다.
5. 출력 형식은 반드시 "월", "화", "수", "목", "금"을 Key로 하고, Value로 각각 5개의 조합(문자열)을 갖는 JSON 객체(Object)여야 합니다.
"""

    weekly_routine = gym_profile.get("weekly_routine", {})
    weekly_routine_text = ""
    for wd in ["월", "화", "수", "목", "금"]:
        vals = weekly_routine.get(wd, ["", "", "", ""])
        filled_vals = []
        for i, v in enumerate(vals):
            if v.strip(): filled_vals.append(f"{i+1}단계:{v.strip()}")
        if filled_vals:
            weekly_routine_text += f"- {wd}요일 고정: " + ", ".join(filled_vals) + "\\n"
    if not weekly_routine_text:
        weekly_routine_text = "지정된 요일별 고정 루틴 없음 (자유롭게 구성하세요)"

    user_prompt = f"""
[체육관 기본 설정]
- 1단계(몸풀기): {r1}
- 2단계(기본기): {r2}
- 3단계(기술): {r3}
- 4단계(회복): {r4}
- 대상: {age_name} ({age_desc})
- 특별 지침: {special_note}

[관장님의 요일별 고정 루틴 지시사항]
{weekly_routine_text}

[요청]
관장님의 요일별 지시사항을 최우선으로 반영하여, 각 요일마다 사용할 수련 조합 5개씩을 생성해주세요.
지시사항에 비어있는 요일이나 단계는 [체육관 기본 설정]의 항목들을 조합하여 자유롭게 4단계로 채워주세요.
반드시 아래의 JSON 객체 형식(월~금)으로 출력해야 합니다.

[반드시 지켜야 할 출력 형식 예시]
{{
  "월": [
    "가벼운 런닝\\n기초체력\\n앞차기 연습\\n피구",
    "왕복 셔틀런\\n제자리 뛰기\\n뒤차기\\n명상",
    ... (총 5개)
  ],
  "화": [ ... ],
  "수": [ ... ],
  "목": [ ... ],
  "금": [ ... ]
}}
"""
    # 사용자가 체크한 모델 목록 가져오기 (없으면 기본값)
    models_to_use = ai_handler.selected_models if hasattr(ai_handler, 'selected_models') and ai_handler.selected_models else ["gpt-4o-mini"]
    
    # 선택된 모델들을 순회하며 재시도 (최대 모델 수 x 3회 반복)
    max_attempts = len(models_to_use) * 3
    for attempt in range(max_attempts):
        model_name = models_to_use[attempt % len(models_to_use)]
        print(f"[AI 호출 시도 {attempt+1}/{max_attempts}] {month}월 수련계획 짜는 중... (사용 모델: {model_name})")
        
        try:
            response = ai_handler.ask(user_prompt=user_prompt, system_prompt=system_prompt, max_tokens=3000, selected_models=[model_name])
            
            # AI가 거부하거나 실패 시 반환하는 엉뚱한 문자열 필터링
            if not response or "감사합니다!" in response or "중단됨" in response:
                continue 
                
            # 마크다운 찌꺼기 완벽 제거
            clean_resp = re.sub(r'```json\s*', '', response)
            clean_resp = re.sub(r'```\s*', '', clean_resp)
            
            json_match = re.search(r'\{[\s\S]*\}', clean_resp)
            if json_match:
                pool = json.loads(json_match.group())
                if isinstance(pool, dict) and "월" in pool and "금" in pool:
                    print(f"✅ AI 수련계획 생성 성공! (완료 모델: {model_name})")
                    return pool
        except Exception as e:
            print(f"⚠️ AI 파싱 오류 ({model_name}): {e}")
            continue

    print(f"🚨 모든 AI 호출({max_attempts}회) 실패! 안전장치(자동 랜덤 뽑기)를 작동합니다.")
    
    # AI가 뻗었을 때를 대비한 1개씩 뽑기 자동화 안전장치
    def pick_one(text, default):
        if not text: return default
        items = [x.strip() for x in text.split(',') if x.strip()]
        return random.choice(items) if items else default

    fallback_pool = {}
    for wd in ["월", "화", "수", "목", "금"]:
        fallback_pool[wd] = []
        for _ in range(5):
            fallback_pool[wd].append(f"{pick_one(r1, '준비운동')}\n{pick_one(r2, '체력단련')}\n{pick_one(r3, '메인수련')}\n{pick_one(r4, '마무리게임')}")
        
    return fallback_pool


def _assign_pool_to_calendar(year: int, month: int, pool: dict, gym_profile: dict, special_note: str = "", existing_events: list = None) -> list:
    """알고리즘을 사용하여 수련 풀의 내용을 달력의 모든 빈칸에 100% 채웁니다."""
    holidays = get_holidays_for_month(year, month)
    weekdays = get_weekdays_in_month(year, month)
    occupied_map = {e["date"]: e["title"] for e in existing_events} if existing_events else {}
    
    occupied_map = {e["date"]: e["title"] for e in existing_events} if existing_events else {}

    
    # ─────────────────────────────────────────────────────────
    # 주말 행사 지능형 배분 (연간계획 1순위 > 체육관 정기행사 2순위)
    # ─────────────────────────────────────────────────────────
    weekend_events_config = gym_profile.get("weekend_events", [])
    assigned_weekends = {} # {date: name}

    # 토요일 리스트 추출 (연간 일정이 없는 '빈 토요일'만 가용 대상)
    available_saturdays = [wd for wd in weekdays if wd["weekday"] == "토" and wd["date"] not in holidays and wd["date"] not in occupied_map]
    
    if weekend_events_config and available_saturdays:
        for ev in weekend_events_config:
            name = ev.get("name", "").strip()
            cycle = int(ev.get("cycle", 1))
            count = int(ev.get("count", 0))
            
            if not name or count <= 0: continue
            
            # 주기에 따른 해당 월 포함 여부 확인 (예: 3개월마다 -> 1, 4, 7, 10월)
            if (month - 1) % cycle != 0: continue
            
            # 남은 가용 토요일에 순차 배분
            for _ in range(count):
                if not available_saturdays: break
                # 가용 토요일 중 가장 앞선 날짜 선택
                target_wd = available_saturdays.pop(0)
                assigned_weekends[target_wd["date"]] = name

    event_dates = list(assigned_weekends.keys())
    event_name_map = assigned_weekends

    final_entries = []
    pool_idx = {"월": 0, "화": 0, "수": 0, "목": 0, "금": 0}
    
    for wd in weekdays:
        date_str = wd["date"]
        
        # 1. 공휴일은 건너뜀
        if date_str in holidays:
            continue
            
        # 2. 이미 배정된 행사가 있으면 보존
        if date_str in occupied_map:
            final_entries.append({"date": date_str, "title": occupied_map[date_str]})
            continue
            
        # 3. 일요일은 건너뜀
        if wd["weekday"] == "일":
            continue
            
        # 4. 토요일 처리
        if wd["weekday"] == "토":
            if date_str in event_name_map:
                # [수정] 정기 행사를 대괄호와 함께 표시
                final_entries.append({"date": date_str, "title": f"[{event_name_map[date_str]}]"})
            continue
            
        # 5. 평일(월~금) 처리
        wd_str = wd["weekday"]
        if wd_str in pool:
            day_pool = pool[wd_str]
            if len(day_pool) > 0:
                content = day_pool[pool_idx[wd_str] % len(day_pool)]
                pool_idx[wd_str] += 1
            else:
                content = "수련 루틴 없음"
        else:
            content = "수련 루틴 없음"
            
        final_entries.append({"date": date_str, "title": content})

        
    return final_entries


# ─────────────────────────────────────────────────────────
# 연간 생성 (1월~12월 일괄)
# ─────────────────────────────────────────────────────────

def generate_full_year_plan(
    ai_handler,
    year: int,
    gym_profile: dict,
    age_category: dict,
    curriculum_md: str,
    special_note: str = "",
    progress_callback=None,
    excel_path: str = None
) -> list:
    """1월부터 12월까지 연간 수련계획을 일괄 생성합니다."""
    from modules.training_planner.calendar_writer import get_existing_events_from_excel

    all_entries = []
    for month in range(1, 13):
        print(f"\n{'='*40}")
        print(f"🗓️ {year}년 {month}월 계획 생성 중 (하이브리드 모드)...")
        
        # 엑셀 파일이 있으면 해당 월의 기존 일정(연간계획표 등)을 읽어옴
        existing = []
        if excel_path and os.path.exists(excel_path):
            existing = get_existing_events_from_excel(excel_path, month)

        entries = generate_plan_with_ai(
            ai_handler, year, month,
            gym_profile, age_category, curriculum_md,
            special_note, existing_events=existing
        )
        all_entries.extend(entries)
        if progress_callback:
            progress_callback(month, 12)

    print(f"\n✅ [연간 생성 완료] 총 {len(all_entries)}개 일정 (빈칸 없음 보장)")
    return all_entries
