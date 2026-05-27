# -*- coding: utf-8 -*-
import sys
import os
sys.path.append("/Users/gm2hapkido/Desktop/라이온개발자")

from modules.ai_experts.blog_expert import BlogExpert
from config.config import Config

# API 키 설정
Config.GEMINI_API_KEY = "AIzaSyDkT_4Fhi9GdPY6dI7KdG8gmwuPVCAofTc"
Config.GPT_API_KEY = "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"

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
