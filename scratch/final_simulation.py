# -*- coding: utf-8 -*-
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append('/Users/gm2hapkido/Desktop/라이온개발자')

from modules.ai_experts.blog_expert import BlogExpert
from modules.ai_experts.band_expert import BandExpert
from modules.ai_experts.cafe_expert import CafeExpert

def run_simulation():
    print("🚀 [시뮬레이션 시작] 🦁 라이온 개발자 플랫폼 독립화 및 안정화 검증\n")
    
    # 1. 블로그 시뮬레이션 (친근한 아주머니 톤 + 클릭 유도형 제목)
    print("--- 1. 블로그 포스팅 시뮬레이션 ---")
    blog_expert = BlogExpert(use_dummy=False)
    blog_topics = ["합기도 수련이 아이들 자존감에 미치는 영향", "봄철 환절기, 우리 아이 면역력 키우는 비결"]
    
    for i, topic in enumerate(blog_topics):
        print(f"  👉 테스트 {i+1} 주제: {topic}")
        result = blog_expert.generate_blog_content(topic, task_type='regular')
        if result:
            print(f"  [제목]: {result['title']}")
            print(f"  [본문 요약]: {result['content'][:150]}...")
            print(f"  [마지막 문구]: ...{result['content'][-150:].strip()}")
            print(f"  [태그]: {result.get('tags', [])[:5]}...")
        print("-" * 50)

    # 2. 밴드 시뮬레이션 (사실 기반 날씨/뉴스 + 5:5 말투)
    print("\n--- 2. 밴드 스케줄러 시뮬레이션 ---")
    band_expert = BandExpert(use_dummy=False)
    
    # 오전 (날씨 중심)
    print("  👉 [오전 7:00 예약] 날씨 수치 인용 테스트")
    morning_result = band_expert.generate_band_content("활기찬 아침을 여는 인사", task_type='morning', target_time="07:00")
    if morning_result:
        print(f"  [본문]: {morning_result['content']}")
    
    # 오후 (뉴스/이슈 중심)
    print("\n  👉 [오후 14:00 예약] 뉴스/정보 중심 테스트")
    afternoon_result = band_expert.generate_band_content("오후 수련 안내 및 건강 상식", task_type='regular', target_time="14:00")
    if afternoon_result:
        print(f"  [본문]: {afternoon_result['content'][:200]}...")

    # 자동감지 (환각 방지)
    print("\n  👉 [자동감지 포스팅] 환각 방지(지명/대회명) 테스트")
    detect_result = band_expert.generate_band_content("전국합기도대회 소식", task_type='regular')
    if detect_result:
        print(f"  [본문]: {detect_result['content']}")
        if "전남" in detect_result['content'] or "양양" not in detect_result['content'] and "강원도" not in detect_result['content']:
             print("  ⚠️ 경고: 환각 현상 의심됨 (확인 필요)")
        else:
             print("  ✅ 결과: 환각 없이 주제에만 집중함.")

    # 3. 카페 시뮬레이션 (5:5 말투 + 정보성)
    print("\n--- 3. 카페 포스팅 시뮬레이션 ---")
    cafe_expert = CafeExpert(use_dummy=False)
    cafe_result = cafe_expert.generate_cafe_content("신입 수련생을 위한 합기도 입문 가이드")
    if cafe_result:
        print(f"  [본문]: {cafe_result['content'][:200]}...")

    print("\n✅ 시뮬레이션 종료")

if __name__ == "__main__":
    run_simulation()
