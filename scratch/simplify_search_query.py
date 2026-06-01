import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            # 주소와 상호를 조합한 검색어 생성
            search_query = f"{address} {dojang_name}".strip()
            print(f"검색할 쿼리: {search_query}")"""
    
    replacement = """            # 쿼리 생성: 도장명이 있으면 도장명만, 없으면 주소만 사용 (너무 길면 네이버 서버 에러 발생)
            search_query = dojang_name if dojang_name else address
            # 만약 괄호가 포함되어 있다면 괄호 안의 내용도 제거하여 가장 핵심어만 검색
            if '(' in search_query:
                search_query = search_query.split('(')[0].strip()
            print(f"검색할 쿼리: '{search_query}'")"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully simplified search query.")
    else:
        print("Target string not found.")

if __name__ == "__main__":
    fix()
