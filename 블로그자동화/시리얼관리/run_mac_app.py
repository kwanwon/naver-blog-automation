#!/usr/bin/env python3
"""
macOS에서 Tkinter 앱을 실행하기 위한 래퍼 스크립트
"""
import os
import sys
import tkinter as tk
import logging
import platform

def get_app_path():
    """애플리케이션 실행 디렉토리의 절대 경로를 반환합니다."""
    try:
        # 일반 실행 환경
        return os.path.dirname(os.path.abspath(__file__))
    except:
        # PyInstaller 등으로 패키징된 환경
        if hasattr(sys, 'frozen'):
            return os.path.dirname(sys.executable)
        else:
            # 다른 방법으로도 시도
            try:
                import inspect
                return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            except:
                return os.getcwd()

# 현재 스크립트 경로를 얻음
current_dir = get_app_path()

# 로깅 설정
logging.basicConfig(
    filename=os.path.join(current_dir, 'mac_wrapper.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    logging.info(f"시스템 정보: {platform.system()} {platform.release()}")
    logging.info(f"파이썬 버전: {sys.version}")
    logging.info(f"현재 디렉토리: {current_dir}")
    
    # 경로 확인
    files = os.listdir(current_dir)
    logging.info(f"디렉토리 내 파일: {files}")
    
    # 중요 파일 확인
    if "serial_validator.py" not in files:
        logging.error("serial_validator.py 파일을 찾을 수 없습니다!")
        sys.exit(1)
    
    # 현재 경로를 Python 경로에 추가하여 모듈을 찾을 수 있게 함
    sys.path.insert(0, current_dir)
    logging.info("serial_validator 모듈 임포트 시도...")
    from serial_validator import SerialManager
    
    # macOS에서 창이 올바르게 표시되도록 설정
    if platform.system() == 'Darwin':
        logging.info("macOS용 설정 적용 중...")
        root = tk.Tk()
        root.withdraw()  # 빈 창 숨기기
        
        # macOS에서 앱을 포그라운드로 가져오기
        try:
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
        except Exception as e:
            logging.warning(f"포그라운드 설정 실패 (무시 가능): {e}")
        # 루트 창 소멸
        root.destroy()
    
    # 앱 실행
    logging.info("앱 시작...")
    app = SerialManager()
    app.run()

except Exception as e:
    logging.error(f"오류 발생: {str(e)}", exc_info=True)
    
    # 오류 메시지 표시
    try:
        import tkinter.messagebox as messagebox
        messagebox.showerror("오류", f"앱 실행 중 오류가 발생했습니다:\n{str(e)}\n\n자세한 내용은 mac_wrapper.log 파일을 확인하세요.")
    except:
        pass
    
    sys.exit(1) 