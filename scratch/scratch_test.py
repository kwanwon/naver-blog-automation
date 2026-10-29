# -*- coding: utf-8 -*-
import sys
import os
sys.path.append("/Users/gm2hapkido/Desktop/라이온개발자")

from modules.ai_experts.blog_expert import BlogExpert
from config.config import Config

# API 키 설정 (테스트 시 환경 변수 또는 실제 설정 파일에서 로드)
Config.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
Config.GPT_API_KEY = os.environ.get("OPENAI_API_KEY", "")

print("🧪 [Test] BlogExpert 생성 테스트 시작...")
expert = BlogExpert(use_dummy=False)

# 테스트 주제
topic = "아이들의 기초체력 증진이 중요한 이유"

# 블로그 글 생성 시도 (post_order = 1)
result = expert.generate_blog_content(topic, post_order=1)

print("\n================== 생성된 블로그 제목 ==================")
print(result.get("title"))

print("\n================== 생성된 블로그 본문 ==================")
print(result.get("content"))

print("\n================== 생성된 블로그 태그 ==================")
print(result.get("tags"))

print("\n================== 사용된 AI 모델 ==================")
print(result.get("model"))
