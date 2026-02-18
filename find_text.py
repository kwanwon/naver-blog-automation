import os

file_path = r'c:\dev\naver-blog-automation\blog_writer_app.py'

search_terms = ['simple_login']

try:
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            line_num = i + 1
            for term in search_terms:
                if term in line:
                    print(f"Found '{term}' at line {line_num}: {line.strip()[:100]}")
except Exception as e:
    print(f"Error: {e}")
