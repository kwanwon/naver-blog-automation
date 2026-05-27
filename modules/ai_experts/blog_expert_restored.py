The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
# -*- coding: utf-8 -*-
import logging
import re
import json
import urllib.request
import urllib.parse
import ssl
import threading
from .base_expert import BaseAIExpert
from config.config import Config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BlogExpert(BaseAIExpert):
    def __init__(self, use_dummy=False):
        super().__init__(use_dummy)

    def generate_blog_content(self, topic, post_order=1, post_type_config=None, task_type='regular', target_time=None, delta_days=0):
        """블로그 전용 콘텐츠 생성 (최적화 및 안정화 버전)"""
        # 🔄 [상태 격리] 포스팅 시작 전 최신 설정을 실시간 재로드하여 쳇바퀴 증상(타 플랫폼 설정 오염) 완벽 차단
        self._reload_all_settings()
        
        settings = self._load_settings()
        user_settings = self._load_user_settings()
        
        # 🟢 사용자 맞춤형 페르소나 및 종목 컨텍스트 주입
        dojang_name = user_settings.get('dojang_name', user_settings.get('gym_name', '도장'))
        user_sports = user_settings.get('gym_sport', '운동')
        
        # 호칭 결정 로직 (체육관/도장 vs 학원)
        is_gym = any(k in dojang_name for k in ['도장', '체육관', '관', '짐', 'Gym', 'Hapkido', '합기도', '태권도'])
        teacher_title = "사범님" if is_gym else "선생님"
        

<truncated 28597 bytes>
 어색한 느낌을 줍니다.) 호칭을 완전히 생략하고 "안녕하세요! 오늘도 기분 좋은 하루 보내고 계신가요?", "안녕하세요! 활기찬 도장 소식과 함께 인사드립니다."와 같이 독자와 도장 사이의 친근하고 신선한 인간적인 말투로만 작문하여 첫 문단을 시작하세요.
5. **포스팅 구조 및 행갈이 강제화 (매우 엄격 ⭐⭐⭐)**:
    - 모바일 가독성을 극대화하기 위해, **모든 문단은 반드시 2~3문장 단위로 구성**해야 합니다. 
    - 4문장 이상 길게 이어진 문단은 가독성을 망치므로 **절대 금지**하며, 문단 내부에서는 줄바꿈(\n) 없이 문장들이 한 칸 공백으로 자연스럽게 이어지도록 완성해야 합니다.
    - 모든 잘게 쪼갠 문단 사이에는 **반드시 명확하게 빈 줄(엔터 두 번, `\n\n`)을 비워** 눈이 편안한 시각적 여백을 100% 확보하세요. 이 규칙은 타협 불가한 필수 의무 사항입니다.

[작성 규칙 및 금지 사항]
{external_rules}

[🚨 사용자 지정 지침 (UI CUSTOM INSTRUCTIONS - 최우선 순위)]
아래의 지침은 사용자가 UI에서 직접 설정한 최신 지침이며, 이전의 모든 백그라운드 규칙보다 최우선하여 100% 적용되어야 합니다.
이 지침과 이전 지침이 충돌할 경우, 반드시 아래 지침을 따르세요:

{smart_ui_prompt}

[추가 사용자 지침 (텍스트 직접 입력)]:
{type_instructions}


{length_cap_instruction}
"""
        # 실시간 정보 주입
        search_results = self._search_brave(topic)
        if search_results:
            system_message += f"\n\n[System: 실시간 검색 결과]\n{search_results}"