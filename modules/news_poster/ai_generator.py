import os
import json
import re
from datetime import datetime
from utils.path_utils import get_gpt_settings_path, get_user_settings_path

class AIGenerator:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.gpt_settings_path = get_gpt_settings_path()
        self.user_settings_path = get_user_settings_path()

    def _load_settings(self):
        """Loads both GPT settings and user settings from config paths."""
        gpt_settings = {}
        user_settings = {}

        if os.path.exists(self.gpt_settings_path):
            try:
                with open(self.gpt_settings_path, 'r', encoding='utf-8') as f:
                    gpt_settings = json.load(f)
            except Exception as e:
                print(f"[Error] [AIGenerator] Failed to load gpt settings: {e}")

        if os.path.exists(self.user_settings_path):
            try:
                with open(self.user_settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
            except Exception as e:
                print(f"[Error] [AIGenerator] Failed to load user settings: {e}")

        return gpt_settings, user_settings

    def generate_news_post(self, news_title, news_desc, weather_data=None):
        """
        Generates blog post title and body using Gemini API based on news and weather data,
        conforming to the customized persona, style, and brand instructions.
        """
        print(f"[Step] [AIGenerator] Initializing blog post generation for news: '{news_title[:20]}...'")

        gpt_settings, user_settings = self._load_settings()
        api_key = gpt_settings.get('gemini_api_key', '')
        
        if not api_key:
            raise ValueError("Gemini API Key is not set in AI settings. Please check your UI configuration.")

        # Resolve gym background contexts
        gym_name = user_settings.get('gym_name', user_settings.get('dojang_name', '체육관'))
        gym_sport = user_settings.get('gym_sport', '운동')
        slogan = user_settings.get('slogan', '')
        address = user_settings.get('address', '')
        contact = user_settings.get('contact', '')

        # Resolve persona/style parameters
        _persona_prompt_map = {
            'expert_sport':  "주제에 깊은 통찰과 전문성을 가진 유익한 정보 칼럼니스트이자 연구원입니다. 과학적 원리와 유용한 효과를 신뢰감 있게 설명하는 시점으로 작성하세요.",
            'sabeom':        "건강한 라이프스타일과 긍정적인 에너지를 전파하는 다정한 웰니스 에디터입니다. 활기찬 분위기와 긍정적인 일상의 가치를 생생하고 따뜻하게 전달해 주세요.",
            'parent_friend': "일상적인 건강과 웰니스 고민에 깊이 공감하고 함께 호흡하는 친근한 정보 큐레이터입니다. 독자의 시선에서 쉽게 이해할 수 있도록 실질적으로 유용한 상식과 팁을 다정하게 전달해 주세요.",
            'sports_coach':  "에너지 넘치고 활기찬 신체 단련 피트니스 코치입니다. 독자에게 강렬한 동기부여와 활력을 선사하고 신체를 활기차게 수련하는 가치를 경쾌하게 전달해 주세요.",
            'mental_mentor': "깊은 마음공부와 정서적 안정에 통찰이 깊은 마음 웰니스 멘토입니다. 현대인과 아이들이 겪는 만성 스트레스, 심리적 불안을 전인격적 정서 케어와 따뜻한 마음의 안정 가치로 잔잔하게 보듬어 주세요.",
            'rehab_expert':  "해부학적 전문 지식을 가진 스포츠 재활 트레이너이자 물리치료 관점의 해부 지도자입니다. 관절과 척추 주변의 정렬, 생리학적 안전 밸런스를 매우 과학적이고 체계적인 관점으로 설명하세요."
        }
        
        blog_persona_mode = gpt_settings.get('blog_persona_mode', 'expert_sport')
        if blog_persona_mode == 'custom':
            persona_prompt = gpt_settings.get('blog_persona_mode_custom', '').strip()
            if not persona_prompt:
                persona_prompt = _persona_prompt_map['expert_sport']
        else:
            persona_prompt = _persona_prompt_map.get(blog_persona_mode, _persona_prompt_map['expert_sport'])

        _style_prompt_map = {
            'haeyo':     "군더더기 없이 깔끔하고 다정다감한 대화체 말투 (~해요, ~에요, ~하죠?)로 독자에게 친근하게 다가가는 어조로 작성하세요. 딱딱한 말투(~입니다만 반복)는 금지합니다.",
            'imnida':    "전문적이고 신뢰감을 주는 정중한 격식체 말투 (~입니다, ~합니다)를 사용하여 신뢰도가 높고 진중한 보도자료 칼럼처럼 격조 있게 작성하세요.",
            'half_half': "다정한 대화체(~해요, ~네요)와 정중한 격식체(~입니다, ~합니다)를 5:5 비율로 자연스럽게 섞어서 신뢰감과 친근함을 조화롭게 확보하여 작성하세요."
        }
        blog_style_mode = gpt_settings.get('blog_style_mode', 'haeyo')
        style_prompt = _style_prompt_map.get(blog_style_mode, _style_prompt_map['haeyo'])

        # Resolve informational instructions
        info_instructions = gpt_settings.get('informational_instructions', '')
        if not info_instructions:
            info_instructions = user_settings.get('informational_instructions', '독자에게 매우 가치 있는 건강 및 생활 정보를 담백하게 전해드리는 구조')

        # Format weather string if available
        weather_str = ""
        if weather_data:
            weather_str = f"기온: {weather_data.get('temp', '쾌적한')}도, 하늘상태: {weather_data.get('sky', '맑음')}"
        else:
            weather_str = "쾌적하고 활기찬 하루"

        current_dt = datetime.now()
        date_str = current_dt.strftime("%Y년 %m월 %d일")

        system_message = f"""당신은 네이버 블로그에 뉴스 핫이슈를 쉽고 명확하게 풀어 설명하여 큰 공감과 정보성 가치를 전달하는 전문 AI 에디터이자 칼럼니스트입니다.
- **[역할 (페르소나)]**: {persona_prompt}
- **[말투 (스타일)]**: {style_prompt}
- **[정보성 지침]**: {info_instructions}

[🚨 필수 포스팅 구조 및 형식 규칙 - 엄격 준수 ⭐⭐⭐⭐⭐]
1. 당신이 출력하는 전체 포스팅 텍스트는 반드시 **`[제목]`**, **`[본문]`**, 그리고 **`[검색어]`** 마커 형식을 100% 준수해야 하며, 다른 설명이나 다른 텍스트를 포함해서는 안 됩니다.
2. **`[제목]`** 섹션: 
   - 20~35자 내외의 흥미롭고 호기심을 유발하는 깔끔한 제목 1줄을 직접 지으십시오.
   - 뻔하고 교과서적인 문투(예: '~~의 중요성', '~~에 대해 알아보자')는 **절대 금지**합니다.
   - 제목에는 날씨나 상호, 해시태그를 포함시키지 마십시오.
3. **`[본문]`** 섹션:
   - 첫 시작 문장은 날씨 안부로 시작해야 합니다: "오늘 날씨 정보({weather_str})를 전하며 활기찬 하루 인사를 드립니다." 형태의 매우 담백하고 자연스러운 인사를 1문장으로 적고 빈 줄을 두어 단락을 끝내십시오. (감상적 칭찬이나 사족 금지)
   - 두 번째 문단부터 주어진 **[뉴스 정보]**를 바탕으로, 독자들이 이해하기 쉬운 논리적인 가치를 서술하십시오.
   - 무리한 '체육관 홍보'나 "방문하세요", "등록하세요" 같은 유도성 상업 멘트는 **100% 전면 금지**입니다. 오직 신뢰할 수 있는 정보 칼럼의 품격을 지켜 서술하십시오.
   - 마지막 마무리로, 아래의 [체육관 정보 및 슬로건]을 조화롭고 부드럽게 한 줄 덧붙여서 끝내십시오.
4. **`[검색어]`** 섹션:
   - 이 뉴스 기사 및 포스팅 칼럼의 핵심 소재(예: 소아비만, 건강 훈련, 성장판, 스트레칭 등)에 가장 잘 어울리는 Pexels 영어 검색 키워드 1개(예: childhood obesity, stretching, running track, healthy lifestyle, kids exercise 등)를 소문자로 짧게 2~3단어 이내로 1줄만 작성하십시오.

[체육관 정보 및 슬로건]
- 상호명: {gym_name} ({gym_sport} 전문 교육관)
- 슬로건: {slogan}
- 위치 및 연락처: {address} (문의: {contact})

[🚨 가독성 행갈이 규칙 ⭐⭐⭐]
- 모바일 가독성을 위해 모든 단락은 **최대 2~3문장** 단위로 짧게 쪼개어 구성하고, 단락과 단락 사이에는 무조건 빈 줄(`\n\n`)을 비워두십시오.
"""

        user_prompt = f"""[뉴스 정보]
- 제목: {news_title}
- 요약: {news_desc}
- 날짜: {date_str}

위 뉴스를 활용하여, 유익하고 신선한 관점의 블로그 칼럼 포스팅을 작성해 주세요."""

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-1.5-flash") # Stable & fast model
            
            response = model.generate_content(
                f"{system_message}\n\n{user_prompt}",
                generation_config={"temperature": 0.7, "max_output_tokens": 4096, "top_p": 0.9},
                request_options={"timeout": 60}
            )
            
            result_text = ""
            if hasattr(response, "text") and response.text:
                result_text = response.text
            elif hasattr(response, "candidates"):
                parts = []
                for cand in getattr(response, "candidates", []):
                    content = getattr(cand, "content", None)
                    if content:
                        for part in getattr(content, "parts", []):
                            txt = getattr(part, "text", None)
                            if txt:
                                parts.append(txt)
                if parts:
                    result_text = "\n".join(parts)

            if not result_text:
                raise ValueError("Gemini returned empty response.")

            # Parse [제목], [본문] and [검색어]
            title = ""
            body = ""
            image_keyword = "children fitness healthy"
            
            title_match = re.search(r'\[제목\](.*?)\[본문\]', result_text, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                remaining = result_text.split("[본문]")[-1].strip()
                if "[검색어]" in remaining:
                    body = remaining.split("[검색어]")[0].strip()
                    image_keyword = remaining.split("[검색어]")[-1].strip()
                else:
                    body = remaining
            else:
                # Fallback parse if markers were slightly malformed
                lines = result_text.strip().split("\n")
                if len(lines) > 2:
                    title = lines[0].replace("[제목]", "").replace("**", "").strip()
                    body_lines = []
                    for ln in lines[1:]:
                        if "[검색어]" in ln:
                            image_keyword = ln.replace("[검색어]", "").replace("**", "").strip()
                        else:
                            body_lines.append(ln)
                    body = "\n".join(body_lines).replace("[본문]", "").strip()
                else:
                    title = f"알아두면 유익한 오늘의 뉴스: {news_title}"
                    body = result_text

            # Clean markdown decorators from title and image_keyword
            title = re.sub(r'[*#_`\[\]]', '', title).strip()
            image_keyword = re.sub(r'[*#_`\[\]]', '', image_keyword).strip()
            if not image_keyword:
                image_keyword = "children fitness healthy"

            print(f"[Step] [AIGenerator] Successfully generated content. Title: '{title[:15]}...', Keyword: '{image_keyword}'")
            return title, body, image_keyword

        except Exception as ex:
            print(f"[Error] [AIGenerator] Generation failed: {ex}")
            # Safe Fallback in case of total failure
            fallback_title = f"[뉴스 인사이트] {news_title}"
            fallback_body = f"""오늘 날씨 정보({weather_str})를 전하며 활기찬 하루 인사를 드립니다.\n\n최근 언론을 통해 보도된 소식 중 관심 있게 살펴볼 뉴스가 있습니다.\n\n- 뉴스 주제: {news_title}\n\n- 내용: {news_desc}\n\n이러한 현상은 우리의 건강과 일상에 다양한 시사점을 던져주고 있습니다. 평상시 규칙적인 운동과 올바른 신체 활동을 통해 기초 체력을 탄탄하게 다져놓는 것은 언제나 큰 예방이자 삶의 건강한 기틀이 됩니다.\n\n우리 모두 건강하고 안전한 하루가 되기를 바라며, 항상 정성을 다해 함께하겠습니다.\n\n* {gym_name} ({gym_sport} 전문) | {slogan}\n* 위치: {address} (연락처: {contact})"""
            return fallback_title, fallback_body, "children fitness healthy"
