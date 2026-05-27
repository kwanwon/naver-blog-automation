# -*- coding: utf-8 -*-
import sys
import os
import re

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath("."))

from modules.pipelines.band_pipeline import BandPipeline

def simulate_post(platform, topic, ai_content):
    """밴드 포스팅 결과물 시뮬레이션 (사람 톤 + 태그 밀착 버전)"""
    
    # 1단계: 본문 및 태그 추출
    body_match = re.search(r'본문:\s*(.*?)\s*태그:', ai_content, re.DOTALL)
    body = body_match.group(1).strip() if body_match else ai_content
    
    # 태그 추출
    tag_match = re.search(r'태그:\s*(.*)', ai_content, re.DOTALL)
    ai_tags = [t.strip() for t in tag_match.group(1).split(',')] if tag_match else []
    
    # 2단계: BandPipeline을 통한 최종 처리
    # 시뮬레이션을 위해 실제 관장님의 설정을 모방한 '샘플' 데이터입니다.
    # 실제 프로그램 실행 시에는 밴드 탭에 직접 입력하신 '해시태그' 칸의 내용을 100% 가져옵니다.
    mock_settings = {
        'band_hashtags': "부평합기도#부평라이온체육관#라이온합기도#한국체대라이온체육관#호신술전문도장", 
        'blog_tags': ""
    }
    
    final_body, final_tags = BandPipeline.process(
        body, 
        ai_tags, 
        "/Users/gm2hapkido/.gemini/antigravity", 
        mode=platform,
        fallback_settings=mock_settings
    )
    
    print(f"\n[시뮬레이션 결과]")
    print("="*50)
    print("[실제 밴드 포스팅 본문]")
    print("-" * 50)
    print(final_body)
    print("-" * 50)
    print("\n[최종 태그 (공백 없이 붙여쓰기)]")
    print("".join([f"#{t}" for t in final_tags]))
    print("="*50 + "\n")

# --- 시나리오: 감동->보기 좋았습니다 (사람 톤 반영) ---
human_ai_response = """
본문: 3시부 수련생들과 함께 음악 줄넘기 기초 과정을 성실히 마무리했습니다. 더블오더 동작을 익히는 과정에서 아이들이 보여준 끈기 있게 하는 모습은 참 보기 좋았습니다. 처음에는 발이 걸려 멈칫하기도 했지만, 끝까지 포기하지 않고 리듬을 맞추며 성장의 발판을 마련했네요. 오늘 하루도 고생 많았습니다.

태그: 3시부, 줄넘기, 음악줄넘기, 더블오더, 수련기록
"""

simulate_post(
    platform='manual_topic',
    topic="[3시부] 음악 줄넘기 기초",
    ai_content=human_ai_response
)
