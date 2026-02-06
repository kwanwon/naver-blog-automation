
import sys
import threading

class StreamLogger:
    """stdout/stderr를 캡처하여 UI로 전송하는 로거"""
    def __init__(self, log_file_path=None):
        self.terminal = sys.stdout
        self.log_buffer = []
        self.log_callback = None
        self.lock = threading.Lock()
        self.max_lines = 1000  # 최대 라인 수
        self.log_file = None
        if log_file_path:
            try:
                self.log_file = open(log_file_path, 'w', encoding='utf-8', buffering=1)
            except:
                pass

    def write(self, message):
        try:
            # 터미널 출력 유지
            if self.terminal:
                self.terminal.write(message)
                self.terminal.flush()
            
            # 파일 출력
            if self.log_file:
                try:
                    self.log_file.write(message)
                    self.log_file.flush()
                except:
                    pass
            
            # 버퍼에 저장
            with self.lock:
                self.log_buffer.append(message)
                # 버퍼 크기 관리 (가끔 정리)
                if len(self.log_buffer) > self.max_lines * 1.5:
                    self.log_buffer = self.log_buffer[-self.max_lines:]
            
            # UI 콜백 (실시간 업데이트)
            if self.log_callback:
                try:
                    self.log_callback(message)
                except:
                    pass
        except Exception:
            pass # 로깅 중 에러 무시

    def flush(self):
        if self.terminal:
            self.terminal.flush()

    def get_logs(self):
        with self.lock:
            return "".join(self.log_buffer)

    def set_callback(self, callback):
        self.log_callback = callback
