# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any

class SmartReply:
    """
    지역 마케팅을 위한 스마트 댓글/답글 생성기
    상대방의 글/댓글 의도를 파악하고, 페르소나에 맞춰 적절한 반응을 생성합니다.
    """
    
    def __init__(self, ai_handler, persona_manager):
        self.ai_handler = ai_handler
        self.persona_manager = persona_manager
        self.logger = logging.getLogger("SmartReply")
        
    def check_sensitive_topic(self, text: str) -> bool:
        """
        텍스트에 민감한 주제(화재, 사고, 부상 등)가 포함되어 있는지 확인
        """
        sensitive_keywords = ['화재', '사고', '부상', '사망', '별세', '추모', '피해', '재난', '지진', '홍수', '태풍', '침수', '전복', '충돌']
        return any(keyword in text for keyword in sensitive_keywords)

    def classify_intent(self, text: str, selected_models: list = None) -> str:
        """
        상대방 글/댓글의 의도를 분류
        :return: 'SENSITIVE', 'GREETING', 'QUESTION', 'LEAD', 'OTHER', 'SPAM'
        """
        # 1. 민감 주제 우선 체크 (안전 필터)
        if self.check_sensitive_topic(text):
            return 'SENSITIVE'

        try:
            system_msg = """
당신은 텍스트 의도 분석기입니다. 주어진 텍스트를 분석하여 다음 중 하나로 분류하세요:
1. GREETING: 단순 인사, 좋은 글 잘 봤다는 내용
2. QUESTION: 질문이 포함된 내용 (가격, 위치, 시간 등)
3. LEAD: 등록 문의, 상담 요청, 가격 문의 등 영업 기회
4. SPAM: 광고, 무의미한 내용
5. OTHER: 기타 일상적인 대화

출력 형식: 오직 대문자 카테고리명만 출력 (예: QUESTION)
"""
            if self.ai_handler and hasattr(self.ai_handler, 'generate_reply'):
                intent = self.ai_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=text,
                    max_tokens=10,
                    selected_models=selected_models
                ).strip().upper()
                
                valid_intents = ['GREETING', 'QUESTION', 'LEAD', 'SPAM', 'OTHER']
                for v in valid_intents:
                    if v in intent:
                        return v
                return 'OTHER'
                
            return 'OTHER' # fallback
            
        except Exception as e:
            self.logger.error(f"의도 분류 실패: {e}")
            return 'OTHER'

    def analyze_reply_intent(self, text: str) -> str:
        """
        답글(Reply)의 의도를 분석합니다.
        :return: 'INQUIRY' (문의) or 'GREETING' (인사/기타)
        """
        try:
            system_msg = """
            당신은 댓글 의도 판별기입니다.
            사용자의 답글이 '가격', '위치', '수업 시간', '입관 절차', '상담 요청' 등 구체적인 체육관/도장 관련 문의인지,
            아니면 단순한 '감사합니다', '맞팔해요', '좋은 정보네요' 등 일반적인 소통인지 분류하세요.

            Output Format:
            - INQUIRY: 문의성 내용일 경우
            - GREETING: 단순 인사, 감사, 일반 소통일 경우
            """
            
            if self.ai_handler and hasattr(self.ai_handler, 'generate_reply'):
                result = self.ai_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=text,
                    max_tokens=10
                ).strip().upper()
                if "INQUIRY" in result: return "INQUIRY"
                return "GREETING"
                
            return "GREETING" # Fallback
            
        except Exception as e:
            self.logger.error(f"답글 의도 분석 실패: {e}")
            return "GREETING"

    def generate_inquiry_response(self, text: str, contact_info: Dict[str, str]) -> str:
        """
        문의에 대한 답변 생성 (가격 정보 제외, 연락처 안내 위주)
        """
        try:
            phone = contact_info.get('phone', '')
            kakao = contact_info.get('kakao', '')
            
            # Context
            system_msg = f"""
            당신은 체육관/도장의 친절한 상담원입니다.
            고객의 문의 내용에 대해 정중하고 친절하게 답변해주세요.

            [필수 규칙]
            1. **가격/회비 정보는 절대 구체적으로 언급하지 마세요.** (상담을 유도하세요)
            2. 대신 **직접 연락처나 카카오톡 상담**으로 유도하는 멘트를 반드시 포함하세요.
            3. 말투는 매우 친절하고 상냥하게 하세요.
            4. 이모지를 적절히 사용하여 딱딱하지 않게 하세요.

            [연락처 정보]
            - 전화번호: {phone}
            - 카카오톡 상담: {kakao}

            [답변 구조]
            1. 문의 주셔서 감사하다는 인사
            2. 문의에 대한 간략한 응대 (자세한건 방문/연락 필요)
            3. 연락처 및 카톡 안내
            4. 맺음말
            """

            if self.ai_handler and hasattr(self.ai_handler, 'generate_reply'):
                return self.ai_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=text,
                    max_tokens=300
                )
            
            # Fallback Template
            return f"문의 주셔서 감사합니다! ^^ \n자세한 상담은 아래 연락처로 주시면 친절히 안내해 드리겠습니다.\n\n📞 상담 문의: {phone}\n💬 카톡 상담: {kakao}\n\n편하게 연락 주세요! :)"
            
        except Exception as e:
            self.logger.error(f"답변 생성 실패: {e}")
            return "문의 감사합니다. 상담 번호로 연락 주시면 안내해 드리겠습니다."

    def generate_greeting_response(self, text: str) -> str:
        """
        단순 인사/공감 댓글에 대한 답글 생성 (감사 인사)
        """
        try:
            system_msg = """
            당신은 블로그 운영자입니다.
            방문자가 남긴 "잘 보고 갑니다", "공감해요", "좋은 글이네요" 등의 인사성 댓글에 대해
            감사의 마음을 담아 친절하게 답글을 작성해주세요.

            [작성 지침]
            1. 상대방의 인사나 공감에 대해 감사의 마음을 전하세요.
            2. 단답형 멘트("감사합니다😊")나 매크로 같은 답변은 피하고, 상대방이 쓴 댓글 내용을 기반으로 한 번 더 언급하며 자연스럽게 대답하세요.
            3. (중요) 내가 상대방 블로그에 방문한 상황일 수도 있으므로, 무조건 "방문해 주셔서 감사합니다"라고 하지 마세요. "소통"에 초점을 맞추세요.
            4. 홍보성 멘트는 넣지 마세요.
            5. 길이는 너무 짧지 않게 2~3문장(50~100자 내외)으로 작성하여 성의를 보여주세요.
            """

            if self.ai_handler and hasattr(self.ai_handler, 'generate_reply'):
                return self.ai_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=text,
                    max_tokens=150
                )
            
            # Fallback
            return "방문해 주셔서 감사합니다! 좋은 하루 보내세요~ ^^"
            
        except Exception as e:
            self.logger.error(f"인사 답글 생성 실패: {e}")
            return "감사합니다! 자주 소통해요! :)"
    def generate_reply(self, target_text: str, intent: str, platform: str = 'blog', is_outbound: bool = False, selected_models: list = None) -> str:
        """
        상대방 글에 대한 댓글/답글 생성
        :param is_outbound: True이면 남의 블로그에 찾아가서 다는 댓글 (홍보 절대 금지), False이면 내 블로그에 달린 댓글에 대한 답글
        """
        
        # 1. 페르소나 컨텍스트 설정
        if is_outbound:
            # [남의 블로그 방문 시] - 철저한 방문자 모드 (성의 있는 긴 댓글 2배 확대)
            persona_context = """
당신은 블로그 이웃들의 게시글을 직접 꼼꼼히 끝까지 읽고 진심 어린 감상과 소통 댓글을 남기는 따뜻하고 센스 있는 이웃 블로거입니다.

[필수 작성 지침 - 성의 있는 긴 댓글 2배 확대 ⭐⭐⭐⭐⭐]
1. **본문 핵심 2가지 이상 직접 인용**: 글 제목이나 단문 감상만 읊지 말고, 본문 내용에 적힌 구체적인 내용(사진 속 모습, 기술적 사실, 경험담, 구체적 장소/제품 특징 등)을 최소 2가지 이상 본문에 언급하며 공감하세요.
2. **풍성하고 정성스러운 분량 (2배 확대)**:
   - 최소 **2~3문단 이상 (3~5문장, 공백 포함 150자 ~ 300자 내외)**의 풍성한 분량으로 작성하세요.
   - 단 1문장의 짧거나 무성의한 댓글(예: "~과정이 정말 중요하네요!", "~잘 보았습니다!")은 100% 엄격히 금지합니다.
3. **다정한 교감 및 질문 곁들이기**: 이웃이 전달하고자 하는 주제에 깊이 공감해 주고, 마지막에는 다정한 반응이나 관련 질문을 덧붙여 사람과 대화하듯 정성스럽게 서술하세요.

[절대 금지 사항]
1. **당신의 정체(체육관 관장, 지도자 등)를 절대 밝히지 마세요.**
2. **"우리 체육관", "저희 도장", "상담", "프로그램" 등 홍보성 단어를 절대 사용하지 마세요.**
3. 제목만 대충 본 듯한 뻔하고 기계적인 멘트(예: "~의 반전 매력을 느껴봅니다", "매력적이네요", "중요하네요" 단답)는 100% 금지합니다.
"""
        else:
            # [내 블로그 답글 시] - 기존 페르소나 (관장님 모드)
            persona_context = self.persona_manager.get_system_prompt_context()
        
        # 2. 의도별 추가 지침
        intent_instruction = ""
        marketing_block = ""
        
        if intent == 'SENSITIVE':
            intent_instruction = "가장 중요: 절대 홍보하지 마세요. 오직 걱정과 위로의 마음만 전하세요. '안전이 최우선입니다', '큰 피해 없으시길 바랍니다' 등."
            marketing_block = "블로그/체육관 언급 금지. 홍보 금지."
        elif intent == 'GREETING':
            intent_instruction = "이웃의 글에 대해 다정하게 반응하고, 본문 내용을 짚으며 반갑게 소통하세요. 홍보 멘트는 하지 마세요."
        elif intent == 'QUESTION':
            if is_outbound:
                intent_instruction = "상대방의 질문이나 글 내용에 대해 친절하게 답하고 공감하되, 당신의 체육관을 홍보하지 마세요. 순수한 정보 공유 차원에서 답하세요."
            else:
                intent_instruction = "질문에 대해 친절하고 정확하게 답변하세요. 질문에 대한 답을 주는 과정에서만 자연스럽게 우리 프로그램을 언급하세요."
        elif intent == 'LEAD':
            if is_outbound:
                intent_instruction = "상대방이 운동이나 주제에 관심을 보인다면 격려해주세요. 하지만 우리 체육관으로 오라고 하지 마세요."
            else:
                intent_instruction = "정중하게 상담을 안내하세요. 연락처나 방문 방법을 안내하되 강요하지 마세요."
        else:
            intent_instruction = "이웃처럼 친근하게 소통하세요. 글 내용의 구체적 포인트를 언급하고 칭찬과 응원을 보내세요."
            if is_outbound:
                marketing_block = "내 체육관 이야기 금지. 순수 소통만."
            else:
                marketing_block = "억지로 체육관 이야기를 꺼내지 마세요 (ID가 홍보 역할을 합니다)."
            
        system_msg = f"""
{persona_context}

[현재 상황]
상대방이 {platform}에 쓴 글/댓글을 보고 답장을 쓰려고 합니다.
상대방의 의도: {intent}

[작성 지침]
- {intent_instruction}
- {marketing_block}
- 분량: 단답형(예: "감사합니다", "~중요하네요")은 절대 피하고, 반드시 3~5문장 (공백 포함 150자 ~ 300자 내외)으로 풍성하고 정성스럽게 작성하세요.
- 봇이 아닌 진정성 있는 '사람'처럼 상대방 글/댓글의 구체적 내용을 짚으며 다정하게 대화하세요.
"""
        try:
            if self.ai_handler and hasattr(self.ai_handler, 'generate_reply'):
                # Handle empty input (likely emoticon/sticker only)
                if not target_text or not target_text.strip():
                    target_text = "[이모티콘 또는 사진만 있는 댓글]"
                    system_msg += "\n[추가 상황] 상대방이 텍스트 없이 이모티콘이나 사진만 남겼습니다. 이에 대해 감사의 의미를 담아 센스 있게 답글을 남겨주세요."

                # Add variety instruction to prevent repetition
                system_msg += "\n[중요 지침] 매번 똑같은 표현을 피하고, 다양하고 창의적이며 진정성 있는 긴 댓글을 작성하세요."

                return self.ai_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=target_text,
                    max_tokens=500,
                    selected_models=selected_models
                )
            
            return "안녕하세요! 좋은 글 잘 보고 갑니다. ^^" # fallback
            
        except Exception as e:
            self.logger.error(f"답글 생성 실패: {e}")
            return "안녕하세요! 소통하고 싶어서 들렀습니다."

