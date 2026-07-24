# -*- coding: utf-8 -*-
import logging
from .base_expert import BaseAIExpert
from config.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class SocialExpert(BaseAIExpert):
    def __init__(self, use_dummy=False):
        super().__init__(use_dummy)

    def generate_social_content(self, topic):
        """이웃 소통(댓글/답글) 전용 콘텐츠 생성"""
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상 완벽 차단
        self._reload_all_settings()
        
        settings = self._load_settings()
        
        idle_instr = settings.get('idle_instructions', "")
        if not idle_instr.strip():
            idle_instr = (
                "이웃의 글을 직접 읽고 진심으로 소통하는 정성스러운 댓글을 작성해주세요.\n"
                "- [절대 금지]: '안녕하세요', '반갑습니다', '좋은 글이네요', '~매력을 느껴봅니다' 등 기계적이고 상투적인 인사말/총평을 100% 생략하세요.\n"
                "- [본문 반영]: 본문 속 구체적인 사실(사진 모습, 겪은 일, 특징 등)을 최소 1~2개 짚어서 구체적으로 언급하세요.\n"
                "- [분량]: PC 화면 기준 1.5~2줄 이상 (3~4문장, 공백 포함 120~180자 내외)으로 풍성하고 성의 있게 작성하세요.\n"
                "- [톤]: 다정하고 친근한 이웃의 말투 (~네요, ~해요)를 사용하세요."
            )

        system_message = f"""당신은 이웃과 소통하는 블로거입니다.
지침: {idle_instr}
{self._get_common_system_rules('idle')}
"""
        base_prompt = f"상대방 글 주제: {topic}\n공감하는 댓글을 작성해주세요."

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
                        temperature=0.8, max_tokens=150
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_message, base_prompt)
                else: continue

                if content:
                    content = self._apply_stability_filter(content, 'idle')
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)
                    
                    # 최종 검증: 만약 AI가 지침을 어기고 '안녕하세요', '반갑네요' 등으로 시작하면 강제 제거
                    for greeting in ['안녕하세요', '반갑습니다', '반갑네요', '반가워요']:
                        if content.startswith(greeting):
                            content = re.sub(f'^{greeting}[,!\.\s]*', '', content).strip()
                    
                    return {
                        "content": content,
                        "model": model_name
                    }
            except Exception as e:
                logger.error(f"소통 생성 오류 ({model_name}): {e}")
                continue

        return {"content": "오늘도 멋진 하루 되세요!", "model": "fallback"}

    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150, selected_models: list = None) -> str:
        """간단한 댓글 답글 생성용 메서드"""
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상 완벽 차단
        self._reload_all_settings()
        
        models_to_use = selected_models if selected_models else self.selected_models
        if not models_to_use: models_to_use = [Config.GPT_MODEL]
            
        for step in range(len(models_to_use)):
            if self.stop_event.is_set():
                return "중단됨"
            model_idx = (self.current_model_index + step) % len(models_to_use)
            model_name = models_to_use[model_idx]
            
            if not self._check_daily_limit(model_name): continue

            try:
                provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
                if provider == "openai":
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
                        temperature=0.8, max_tokens=max_tokens
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_prompt, user_text)
                else: continue

                if content:
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % len(models_to_use)
                    return content
            except Exception as e:
                logger.error(f"답글 생성 오류 ({model_name}): {e}")
                continue
        
        return "감사합니다! 행복한 하루 되세요."
