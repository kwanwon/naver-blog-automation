# -*- coding: utf-8 -*-
import json
import os
import logging
from typing import Dict, List, Any

class PersonaManager:
    """
    지역 마케팅을 위한 업체 페르소나(Persona) 관리 클래스
    업체의 상세 정보(경력, 지도 철학, 프로그램 등)를 저장하고 로드합니다.
    """
    
    def __init__(self, base_path: str):
        self.config_path = os.path.join(base_path, 'config', 'marketing_persona.json')
        self.logger = logging.getLogger("PersonaManager")
        self._ensure_config_exists()
        
    def _ensure_config_exists(self):
        """설정 파일이 없으면 기본 템플릿 생성"""
        if not os.path.exists(self.config_path):
            default_data = {
                "business_name": "",
                "location": "",
                "director_profile": "",
                "key_instructions": "", # 주요 지도 방침
                "programs": "",
                "target_keywords": "", # 양양 맘카페, 속초 맛집 등
                "marketing_tone": "친절한 전문가 (Polite Expert)",
                "contact_info": ""
            }
            self.save_persona(default_data)
            
    def load_persona(self) -> Dict[str, Any]:
        """페르소나 데이터 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"페르소나 로드 실패: {e}")
            return {}
            
    def save_persona(self, data: Dict[str, Any]) -> bool:
        """페르소나 데이터 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"페르소나 저장 실패: {e}")
            return False
            
    def get_system_prompt_context(self) -> str:
        """AI에게 주입할 시스템 프롬프트 컨텍스트 생성"""
        data = self.load_persona()
        
        context = f"""
당신은 '{data.get('business_name', '우리 업체')}'의 마케팅 및 상담 전담 AI입니다.
위치: {data.get('location', '미정')}

[관장님/대표님 프로필]
{data.get('director_profile', '정보 없음')}

[주요 프로그램 및 특징]
{data.get('programs', '정보 없음')}

[지도 철학 및 핵심 가치]
{data.get('key_instructions', '정보 없음')}

[연락처 및 안내]
{data.get('contact_info', '정보 없음')}

[말투 및 태도]
{data.get('marketing_tone', '친절하고 전문적인 태도')}

작성 지침:
1. 지역 주민에게 친근한 이웃처럼 다가가세요. 판매자가 아닌 '소통하는 이웃'의 태도를 유지하세요 (Soft engagement).
2. 상대방의 글 내용을 진심으로 공감하고 칭찬하는 데 집중하세요.
3. **먼저 체육관 홍보를 하지 마세요.** 상대방이 운동/체육관에 대해 질문하거나 관심을 보일 때만 자연스럽게 답변하세요.
4. ID와 프로필 사진이 이미 홍보 역할을 하고 있으므로, 댓글 본문은 순수한 소통에 집중하는 것이 장기적인 팬을 만드는 길입니다.
"""
        return context
