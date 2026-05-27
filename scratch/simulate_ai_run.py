# -*- coding: utf-8 -*-
import os
import sys
from dotenv import load_dotenv

# 현재 스크립트 기준 상위 경로를 path에 추가하여 프로젝트 모듈 로드 가능하게 함
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

import openai
import google.generativeai as genai

def run_simulation():
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not openai_key or not gemini_key:
        print("에러: OpenAI 또는 Gemini API 키가 .env 파일에 설정되어 있지 않습니다.")
        return

    # 주제 선정
    topic = "틀어진 골반을 바로잡는 낙법의 척추 정렬 효과"
    
    # 1. 수정한 페르소나 (Writer Persona)
    persona = """[Writer Persona]
당신은 현대인의 올바른 신체 움직임과 건강을 연구하는 운동 생리학 전문가이자 무도 칼럼니스트입니다.
신뢰감 있고 전문성이 느껴지는 문체로 글을 서술합니다."""

    # 2. 수정한 내용 구성 규칙 (Content Structure)
    instructions = """[Content Structure: Quality over Quantity]
Target Length: 1,200 ~ 1,300 characters. (모바일 가독성과 정보성을 모두 잡는 최적의 길이)
Intro (Local & Info): 가벼운 건강 상식이나 독자의 공감을 이끌어내는 질문으로 시작합니다.
Body (Expertise): 전문 용어(예: 근방추, 코어, 척추 정렬 등)를 반드시 포함하되, 독자가 쉽게 이해할 수 있도록 명확하게 풀어 설명하세요.
Outro (Actionable Tip): 일상생활이나 집에서 쉽게 따라 할 수 있는 가벼운 운동 방법이나 격려를 제공합니다."""

    # 3. 수정한 AI 말투 방지 필터 (Strict Style Rules)
    style_rules = """[Strict Style Rules: Anti-AI Filter]
No Quotes: 제목과 본문에 따옴표(" ", ' ') 사용 금지. 강조는 **[대괄호]**나 볼드체로 하세요.
Human-like List: 숫자(1. 2. 3.) 대신 '첫 번째는', '둘째는', '하나. 둘.' 처럼 사람의 호흡으로 쓰세요.
Forbidden Words: 최고, 최선, 소중한, 놀라운, 발전하는, 결론적으로, 요약하자면 (AI가 즐겨 쓰는 단어 제외).
Local Touch: 체육관의 지역적 정체성을 자연스럽게 녹여내세요."""

    # 프롬프트 조립
    system_message = f"""당신은 현대인의 건강과 올바른 신체 움직임을 연구하는 운동 생리학 전문가이자 무도 칼럼니스트입니다.
말투: 군더더기 없이 깔끔하고 담백한 말투 (~해요, ~네요, ~하죠?)
호칭 원칙: 독자에게 직접 건네는 '부모님', '학부모님' 호칭은 절대 금지하고, 생략하여 자연스럽게 글을 시작하세요.

[🚨 사용자 지정 지침 - 최우선 순위 적용]
{persona}

{style_rules}

[추가 사용자 지침]
{instructions}
"""

    user_prompt = f"""주제: {topic}
형식: [제목], [본문], [태그] 섹션으로 구분하여 작성하세요.
- [제목]: 독자의 깊은 공감과 감동을 자아내는 독창적이고 매력적인 제목. (20~35자 내외, 따옴표 금지, 교과서적 제목 금지)
- [본문]: 지침에 따른 공백 포함 700자 ~ 900자 내외의 깔끔하고 전문적인 글 (모든 문단은 2~3문장 단위로만 작성하고, 문단 사이에는 빈 줄을 두어 가독성을 높이세요.)
- [태그]: 본문과 관련된 키워드 15개를 # 기호 없이 쉼표로만 구분하여 작성하세요.
"""

    # GPT-4o-Mini 테스트
    print("--- GPT-4o-Mini 생성 시작 ---")
    try:
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        gpt_result = response.choices[0].message.content.strip()
        print("GPT-4o-Mini 생성 성공!\n")
    except Exception as e:
        gpt_result = f"GPT 생성 오류: {e}"
        print(gpt_result)

    # Gemini 테스트 (Fallback 및 재시도 포함)
    print("--- Gemini 생성 시작 ---")
    import time
    
    gemini_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"]
    gemini_result = None
    
    for model_name in gemini_models:
        print(f"[{model_name}] 모델 시도 중...")
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(model_name)
            prompt_text = f"{system_message}\n\n{user_prompt}"
            response = model.generate_content(
                prompt_text,
                generation_config={"temperature": 0.7}
            )
            gemini_result = response.text.strip()
            print(f"Gemini {model_name} 생성 성공!\n")
            break
        except Exception as e:
            err_msg = str(e)
            print(f"Gemini {model_name} 오류: {err_msg}")
            if "429" in err_msg:
                print("Rate Limit(429) 감지. 5초 후 다음 모델 또는 재시도 진행합니다...")
                time.sleep(5)
            continue
            
    if not gemini_result:
        gemini_result = "Gemini 모든 모델 호출 실패 (Quota 초과 및 제한)"

    # 마크다운 결과 파일 작성
    output_path = os.path.join(base_dir, "scratch", "simulation_result.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 🤖 AI 모델별 포스팅 시뮬레이션 결과 비교\n\n")
        f.write(f"**테스트 주제:** {topic}\n\n")
        
        f.write("## 🟢 1. GPT-4o-Mini 결과\n")
        f.write("```markdown\n")
        f.write(f"{gpt_result}\n")
        f.write("```\n\n")
        
        f.write("## 🔵 2. Gemini 2.5 Flash-Lite 결과\n")
        f.write("```markdown\n")
        f.write(f"{gemini_result}\n")
        f.write("```\n")
        
    print(f"시뮬레이션 완료! 결과가 다음 경로에 저장되었습니다: {output_path}")

if __name__ == "__main__":
    run_simulation()
