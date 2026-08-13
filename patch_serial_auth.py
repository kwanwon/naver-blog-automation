import re

with open("serial_auth_window.py", "r", encoding="utf-8") as f:
    text = f.read()

replacement = """            # 현재 창 닫기
            try:
                page.window_close()
            except:
                pass
            
            # BlogApp.exe 실행 후 런처는 완전 종료
            import os, threading
            def _exit():
                import time
                time.sleep(1)   # BlogApp.exe 실행 시간 확보
                os._exit(0)     # 런처 프로세스 강제 종료
            threading.Thread(target=_exit, daemon=True).start()"""

text = re.sub(r"            # 현재 창 닫기\n            try:\n                page\.window_close\(\)\n            except:\n                pass", replacement, text)

with open("serial_auth_window.py", "w", encoding="utf-8") as f:
    f.write(text)
print("serial_auth_window patched!")
