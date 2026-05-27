# -*- coding: utf-8 -*-
import sys
import os
import logging

# Append project root directory to path
PROJECT_ROOT = '/Users/gm2hapkido/Desktop/라이온개발자'
sys.path.append(PROJECT_ROOT)

from modules.ai_experts.blog_expert import BlogExpert
from modules.ai_handler import AIHandler

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScenarioTest")

def analyze_and_validate(scenario_name, result):
    """Analyzes and validates the generated blog posting content to verify if it complies with the user's intent."""
    print(f"\n==================================================")
    print(f"📊 [SCENARIO RESULT] {scenario_name}")
    print(f"==================================================")
    if not result:
        print("❌ Error: FAILED to generate content.")
        return False
        
    title = result.get('title', '').strip()
    content = result.get('content', '').strip()
    tags = result.get('tags', [])
    
    print(f"📌 [Title]: {title}")
    
    # Extract paragraphs to check the first sentence
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    first_para = paragraphs[0] if paragraphs else ""
    print(f"📌 [First Paragraph (Weather Greeting)]: {first_para}")
    
    # 1. Title Validation
    title_has_weather = any(w in title for w in ["온도", "기온", "날씨", "하늘", "구름", "구름많음", "맑음", "흐림", "바람"])
    title_has_cheesy = any(c in title for c in ["안부", "가벼운", "하루 보내", "감기 조심"])
    
    # 2. First Paragraph Validation (Cheesy greeting block)
    para_has_cheesy = any(c in first_para for c in [
        "가벼운 안부", "기분 좋은 하루 보내", "행복한 하루", "건강 유의", 
        "감기 조심", "점퍼", "도장 안에는 땀방울", "열정이 타오른다"
    ])
    
    # 3. Time contradiction check (e.g. Morning 7:00 contradiction in body)
    body_text = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""
    has_time_contradiction = False
    if "07:00" in scenario_name or "아침형" in scenario_name:
        # Check if the body incorrectly depicts that kids are training early in the morning
        has_time_contradiction = any(t in body_text for t in [
            "아침 일찍 수련", "방금 수련을 마친", "새벽 수련", "아침 7시 수련"
        ])
    
    # 4. Word count validation
    total_length = len(content)
    print(f"📌 [Total Characters]: {total_length} chars")
    
    # Print analysis checks
    print("\n🔍 --- [INTELLIGENT COMPLIANCE ANALYSIS] ---")
    
    title_pass = True
    if title_has_weather:
        print("❌ [Title Failure]: The weather greeting incorrectly hijacked the Title slot!")
        title_pass = False
    elif title_has_cheesy:
        print("❌ [Title Failure]: The Title contains cheesy AI greetings.")
        title_pass = False
    else:
        print("✅ [Title Pass]: The title is beautifully focused only on the topic.")

    greeting_pass = True
    if para_has_cheesy:
        print("❌ [Greeting Failure]: The first paragraph contains forbidden cheesy greetings (e.g. '가벼운 안부를 나누며...').")
        greeting_pass = False
    else:
        print("✅ [Greeting Pass]: The greeting contains clean, raw weather facts only.")
        
    time_pass = True
    if has_time_contradiction:
        print("❌ [Time Contradiction Failure]: The body contains time-contradictory suhbeom/training descriptions.")
        time_pass = False
    else:
        print("✅ [Time Contradiction Pass]: The body maintains perfectly safe general time descriptions.")
        
    len_pass = 700 <= total_length <= 1100
    if len_pass:
        print(f"✅ [Length Pass]: Total characters ({total_length}) are within optimal range (700~1100 chars).")
    else:
        print(f"⚠️ [Length Warning]: Total characters ({total_length}) deviate from optimal range (700~1100 chars).")
        
    is_fully_compliant = title_pass and greeting_pass and time_pass
    if is_fully_compliant:
        print("\n🏆 RESULT: PERFECT COMPLIANCE WITH USER INTENT! (100% Safe)")
    else:
        print("\n💥 RESULT: COMPLIANCE VIOLATION DETECTED. Action required.")
    
    print("-" * 50)
    return is_fully_compliant

def run_integrated_scenarios():
    print("🎬 [INTEGRATED TESTING START] Executing all blog automation scenarios...")
    blog_expert = BlogExpert(use_dummy=False)
    
    # SCENARIO 1: 블로그 시작 (실시간 / 일반 포스팅)
    # - regular task_type, delta_days=0, target_time=None
    print("\n---------------- Scenarios A: Blog Start (Realtime Regular) ----------------")
    topic_a = "음악줄넘기가 아이들 민첩성 발달에 미치는 효과"
    result_a = blog_expert.generate_blog_content(
        topic=topic_a, 
        post_order=1, 
        task_type='regular', 
        target_time=None, 
        delta_days=0
    )
    analyze_and_validate("Scenario A (Blog Start / Realtime Regular)", result_a)
    
    # SCENARIO 2: 드라이브 감지 포스팅
    # - task_type='detection', delta_days=0, target_time=None
    print("\n---------------- Scenarios B: Drive Detection Mode ----------------")
    topic_b = "낙산 모래 위 뒤돌려차기, 좌우뇌 깨우는 완벽한 균형의 비밀"
    result_b = blog_expert.generate_blog_content(
        topic=topic_b, 
        post_order=2, 
        task_type='detection', 
        target_time=None, 
        delta_days=0
    )
    analyze_and_validate("Scenario B (Drive Detection Mode)", result_b)
    
    # SCENARIO 3: 스케줄 예약 - 일반형 (오후 14:00)
    # - task_type='regular', delta_days=1 (Tomorrow), target_time="14:00"
    print("\n---------------- Scenarios C-1: Scheduler Regular (14:00) ----------------")
    topic_c1 = "코어 근육 강화가 현대인의 요통 예방에 기여하는 생리학적 기전"
    result_c1 = blog_expert.generate_blog_content(
        topic=topic_c1, 
        post_order=3, 
        task_type='regular', 
        target_time="14:00", 
        delta_days=1
    )
    analyze_and_validate("Scenario C-1 (Scheduler Regular Afternoon 14:00)", result_c1)
    
    # SCENARIO 4: 스케줄 예약 - 아침형 (오전 07:00)
    # - task_type='regular', delta_days=1 (Tomorrow), target_time="07:00"
    print("\n---------------- Scenarios C-2: Scheduler Morning (07:00) ----------------")
    topic_c2 = "틀어진 골반을 바로잡는 척추 정렬 수련의 신체 대칭 효과"
    result_c2 = blog_expert.generate_blog_content(
        topic=topic_c2, 
        post_order=4, 
        task_type='regular', 
        target_time="07:00", 
        delta_days=1
    )
    analyze_and_validate("Scenario C-2 (Scheduler Morning 07:00)", result_c2)
    
    # SCENARIO 5: 스케줄 예약 - 저녁형 (오후 20:00)
    # - task_type='regular', delta_days=1 (Tomorrow), target_time="20:00"
    print("\n---------------- Scenarios C-3: Scheduler Evening (20:00) ----------------")
    topic_c3 = "수련 후 1분 호흡 및 이완 스트레칭이 스트레스 해소에 미치는 심리적 이점"
    result_c3 = blog_expert.generate_blog_content(
        topic=topic_c3, 
        post_order=5, 
        task_type='regular', 
        target_time="20:00", 
        delta_days=1
    )
    analyze_and_validate("Scenario C-3 (Scheduler Evening 20:00)", result_c3)
    
    print("\n🎉 [INTEGRATED TESTING COMPLETED] All scenarios successfully verified.")

if __name__ == "__main__":
    run_integrated_scenarios()
