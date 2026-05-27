import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from modules.training_planner.planner_engine import generate_plan_with_ai

class MockAIHandler:
    def ask(self, user_prompt, system_prompt, max_tokens):
        # AI가 줄 법한 수련 풀 5개만 샘플로 반환 (실제로는 30개 생성)
        return """
        [
            "준비운동A\\n체력훈련A\\n메인수련A\\n게임A",
            "준비운동B\\n체력훈련B\\n메인수련B\\n게임B",
            "준비운동C\\n체력훈련C\\n메인수련C\\n게임C",
            "준비운동D\\n체력훈련D\\n메인수련D\\n게임D",
            "준비운동E\\n체력훈련E\\n메인수련E\\n게임E"
        ]
        """

def run_simulation():
    mock_ai = MockAIHandler()
    gym_profile = {
        "gym_name": "라이온짐",
        "sport": "합기도",
        "routine_1": "성장스트레칭",
        "routine_2": "에니몰드릴",
        "routine_3": "호신술",
        "routine_4": "미션피구"
    }
    age_category = {"name": "유치부", "description": "5~7세"}
    curriculum_md = "기술 커리큘럼 샘플 데이터"
    
    # 2026년 5월 시뮬레이션
    month = 5
    year = 2026
    
    print(f"--- {year}년 {month}월 하이브리드 시뮬레이션 시작 ---")
    entries = generate_plan_with_ai(mock_ai, year, month, gym_profile, age_category, curriculum_md)
    
    # 결과 분석
    print("\n[검증 결과]")
    print(f"총 생성된 날짜 수: {len(entries)}")
    
    # 모든 평일이 채워졌는지 확인 (2026년 5월 평일은 월~금)
    # 5월 5일은 공휴일로 제외되어야 함
    dates = [e["date"] for e in entries]
    
    missing = []
    # 2026년 5월 평일 체크 (주말/공휴일 제외)
    # 1(금), 4(월), 6(수), 7(목), 8(금)...
    # 5(화)는 어린이날
    for d in range(1, 32):
        from datetime import date
        dt = date(2026, 5, d)
        wd = dt.strftime("%a") # Mon, Tue...
        date_str = dt.strftime("%Y-%m-%d")
        
        # 공휴일 (신정, 어린이날 등)
        is_holiday = date_str in ["2026-05-05"]
        is_weekend = dt.weekday() >= 5
        
        if not is_holiday and not is_weekend:
            if date_str not in dates:
                missing.append(date_str)
    
    if not missing:
        print("✅ 100% 성공: 모든 평일이 공란 없이 채워졌습니다.")
    else:
        print(f"❌ 실패: 다음 날짜가 누락되었습니다: {missing}")

    for e in entries[:5]:
        print(f"날짜: {e['date']} | 내용: {e['title'].replace('\\n', ' / ')}")

if __name__ == "__main__":
    run_simulation()
