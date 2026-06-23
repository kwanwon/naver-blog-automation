# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger(__name__)
import os
import sys
from .ai_experts.blog_expert import BlogExpert
from .ai_experts.band_expert import BandExpert
from .ai_experts.cafe_expert import CafeExpert
from .ai_experts.social_expert import SocialExpert

logger = logging.getLogger(__name__)

class AIHandler:
    """
    AI 전문가 시스템의 파사드(Facade)이자 라우터 역할을 수행합니다.
    기존 모듈과의 호환성을 100% 유지하면서 각 요청을 전문 AI 클래스로 전달합니다.
    """
    def __init__(self, use_dummy=False):
        self.use_dummy = use_dummy
        
        # 전문가 객체 초기화
        self.blog_expert = BlogExpert(use_dummy)
        self.band_expert = BandExpert(use_dummy)
        self.cafe_expert = CafeExpert(use_dummy)
        self.social_expert = SocialExpert(use_dummy)
        
        # 하위 호환성을 위한 속성 복사 (필요한 경우)
        self.selected_models = self.blog_expert.selected_models
        self.gemini_api_key = self.blog_expert.gemini_api_key
        self.current_model_index = self.blog_expert.current_model_index

    @property
    def model(self):
        return self.blog_expert.model

    @property
    def openai_client(self):
        return self.blog_expert.openai_client

    @property
    def settings(self):
        return self.blog_expert.settings

    def generate_content(self, topic, post_order=1, post_type_config=None, platform='blog', task_type=None, target_time=None, delta_days=0):
        """블로그 및 일반 포스팅 생성 요청을 라우팅합니다."""
        if platform == 'blog':
            return self.blog_expert.generate_blog_content(
                topic=topic, 
                post_order=post_order, 
                post_type_config=post_type_config, 
                task_type=task_type, 
                target_time=target_time,
                delta_days=delta_days
            )
        elif platform in ['band', 'drive_auto', 'manual_topic']:
            result = self.band_expert.generate_band_content(topic, platform, task_type or 'regular', target_time, delta_days)
            if result and result.get('content'):
                import os
                import re
                from modules.pipelines.band_pipeline import BandPipeline
                from utils.path_utils import get_app_data_dir
                app_data_dir = get_app_data_dir()
                folder_name = "수련"
                if platform == 'drive_auto':
                    match = re.match(r'^\[(.*?)\]', topic)
                    if match:
                        folder_name = match.group(1).strip()
                    else:
                        folder_name = "수련"
                elif platform == 'manual_topic':
                    match = re.match(r'^\[(.*?)\]', topic)
                    if match:
                        folder_name = match.group(1).strip()
                    else:
                        # 괄호가 없으면 전체 주제(혹은 첫 단어)를 폴더명으로 간주
                        folder_name = topic.strip()
                
                assembled_content, final_tags = BandPipeline.process(
                    content=result.get('content', ''),
                    ai_tags=result.get('tags', []),
                    app_data_dir=app_data_dir,
                    mode='band' if platform == 'band' else 'drive_auto',
                    folder_name=folder_name
                )
                result['content'] = assembled_content
                result['tags'] = ", ".join(final_tags)
            return result
        elif platform == 'cafe':
            return self.cafe_expert.generate_cafe_content(topic, task_type or 'regular', target_time, delta_days)
        elif platform == 'idle':
            return self.social_expert.generate_social_content(topic)
        else:
            # 기본값은 블로그 전문가에게 위임
            return self.blog_expert.generate_blog_content(topic, post_order, post_type_config, task_type, target_time, delta_days)

    def generate_platform_content(self, topic, platform='blog', task_type='regular', target_time=None, news_pool=None, previous_news=None, delta_days=0, post_type_config=None, post_order=1):
        """Routing content generation requests for each platform with post_order support for cycling tips."""
        if platform == 'blog':
            return self.blog_expert.generate_blog_content(
                topic=topic,
                post_order=post_order,
                post_type_config=post_type_config,
                task_type=task_type, 
                target_time=target_time, 
                delta_days=delta_days
            )
        elif platform in ['band', 'drive_auto', 'manual_topic']:
            result = self.band_expert.generate_band_content(topic, platform, task_type, target_time, delta_days, news_pool=news_pool)
            if result and result.get('content'):
                import os
                import re
                from modules.pipelines.band_pipeline import BandPipeline
                from utils.path_utils import get_app_data_dir
                app_data_dir = get_app_data_dir()
                folder_name = "수련"
                if platform == 'drive_auto':
                    match = re.match(r'^\[(.*?)\]', topic)
                    if match:
                        folder_name = match.group(1).strip()
                    else:
                        folder_name = "수련"
                elif platform == 'manual_topic':
                    match = re.match(r'^\[(.*?)\]', topic)
                    if match:
                        folder_name = match.group(1).strip()
                    else:
                        folder_name = topic.strip()
                
                assembled_content, final_tags = BandPipeline.process(
                    content=result.get('content', ''),
                    ai_tags=result.get('tags', []),
                    app_data_dir=app_data_dir,
                    mode='band' if platform == 'band' else 'drive_auto',
                    folder_name=folder_name
                )
                result['content'] = assembled_content
                result['tags'] = ", ".join(final_tags)
            return result
        elif platform == 'cafe':
            return self.cafe_expert.generate_cafe_content(topic, task_type, target_time, delta_days)
        elif platform == 'idle':
            return self.social_expert.generate_social_content(topic)
        else:
            return self.blog_expert.generate_blog_content(
                topic=topic,
                post_order=post_order,
                post_type_config=post_type_config,
                task_type=task_type, 
                target_time=target_time, 
                delta_days=delta_days
            )

    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150, selected_models: list = None, platform: str = 'idle') -> str:
        """댓글 및 답글 생성 요청을 SocialExpert로 전달합니다."""
        return self.social_expert.generate_reply(system_prompt, user_text, max_tokens, selected_models)

    def ask(self, user_prompt: str, system_prompt: str = "당신은 유능한 도우미입니다.", max_tokens: int = 2000, selected_models: list = None) -> str:
        """전문가 시스템을 거치지 않고 직접 AI에게 질문을 던집니다. (주로 독립 모듈에서 사용)"""
        # SocialExpert의 generate_reply를 활용하여 범용 질문 처리
        return self.social_expert.generate_reply(
            system_prompt=system_prompt,
            user_text=user_prompt,
            max_tokens=max_tokens,
            selected_models=selected_models
        )

    def scan_and_learn_image_folders(self, base_dir: str = None, force_rescan: bool = False) -> dict:
        """
        블로그사진폴더 내 하위 폴더를 스캔하고 AI 키워드를 자동 학습합니다.
        GUI 버튼 또는 프로그램 시작 시 호출하세요.

        Args:
            base_dir: ImageFolderManager의 base_dir (None이면 프로젝트 루트 자동 감지)
            force_rescan: True면 기존 학습 결과 무시하고 전체 재학습

        Returns:
            dict: 학습된 폴더별 키워드 규칙
        """
        import os
        from folder_manager import ImageFolderManager

        if base_dir is None:
            # 현재 실행 파일 기준으로 프로젝트 루트 자동 탐색
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        print(f"[Step 1] [AIHandler] 이미지 폴더 스캔 시작: {base_dir} (상태: 시도)")
        fm = ImageFolderManager(base_dir=base_dir)

        def ai_ask_fn(prompt: str) -> str:
            """AI 호출 래퍼 (AIHandler.ask()를 그대로 활용)"""
            try:
                return self.ask(prompt, max_tokens=300)
            except Exception as e:
                logger.warning(f"[AIHandler] AI 키워드 요청 실패: {e}")
                return ""

        result = fm.scan_and_learn_keywords(ai_ask_fn=ai_ask_fn, force_rescan=force_rescan)
        print(f"[Step 2] [AIHandler] 이미지 폴더 AI 학습 완료: {len(result)}개 규칙 저장 (상태: 성공)")
        return result

    # 하위 호환성을 위해 자주 사용되는 유틸리티 메서드 노출 (필요시)
    def _load_settings(self):
        return self.blog_expert._load_settings()

    def _load_user_settings(self):
        return self.blog_expert._load_user_settings()

    def _get_trending_topics(self, count=3, force_refresh=False):
        """하위 호환성을 위해 트렌딩 주제 탐색 기능을 blog_expert로부터 위임받아 제공합니다."""
        return self.blog_expert._get_trending_topics(count=count, force_refresh=force_refresh)

if __name__ == "__main__":
    # 테스트 코드
    handler = AIHandler(use_dummy=True)
    print("AI Handler Expert System 초기화 성공")
    result = handler.generate_content("태권도 수련의 가치", platform='blog')
    print(f"테스트 생성 결과 (블로그): {result.get('title')}")