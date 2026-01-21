"""
Chrome 브라우저 및 ChromeDriver 자동 관리 모듈
Windows 배포용 프로그램에서 Chrome 관련 설정을 자동화합니다.
"""

import os
import sys
import platform
import subprocess
import json
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Tuple

# requests 모듈이 없을 때를 대비한 안전한 import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests 모듈이 설치되지 않았습니다. ChromeDriver 자동 다운로드 기능을 사용할 수 없습니다.")

class ChromeManager:
    def __init__(self, base_dir: str):
        """
        Chrome 관리자 초기화
        
        Args:
            base_dir: 프로그램 기본 디렉토리
        """
        self.base_dir = base_dir
        self.platform_system = platform.system().lower()
        self.is_windows = self.platform_system == 'windows'
        
        # ChromeDriver 저장 경로
        self.chromedriver_dir = os.path.join(base_dir, 'chromedriver')
        self.chromedriver_path = None
        
        # Windows에서 ChromeDriver 실행 파일 경로
        if self.is_windows:
            self.chromedriver_path = os.path.join(self.chromedriver_dir, 'chromedriver.exe')
        else:
            self.chromedriver_path = os.path.join(self.chromedriver_dir, 'chromedriver')
        
        # PyInstaller 빌드 환경에서 번들 내부 ChromeDriver 확인
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bundle_chromedriver_dir = os.path.join(sys._MEIPASS, 'chromedriver')
            if self.is_windows:
                bundle_chromedriver_path = os.path.join(bundle_chromedriver_dir, 'chromedriver.exe')
            else:
                bundle_chromedriver_path = os.path.join(bundle_chromedriver_dir, 'chromedriver')
            
            # 번들 내부에 ChromeDriver가 있으면 우선 사용
            if os.path.exists(bundle_chromedriver_path):
                self.chromedriver_dir = bundle_chromedriver_dir
                self.chromedriver_path = bundle_chromedriver_path
                print(f"🎯 번들 내부 ChromeDriver 사용: {self.chromedriver_path}")
    
    def check_chrome_installed(self) -> Tuple[bool, str]:
        """
        Chrome 브라우저 설치 여부 확인
        
        Returns:
            Tuple[bool, str]: (설치됨 여부, 버전 정보 또는 오류 메시지)
        """
        try:
            if self.is_windows:
                # Windows에서 Chrome 설치 확인
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ]
                
                for chrome_path in chrome_paths:
                    if os.path.exists(chrome_path):
                        # Chrome 버전 확인
                        try:
                            result = subprocess.run(
                                [chrome_path, "--version"], 
                                capture_output=True, 
                                text=True, 
                                timeout=10
                            )
                            if result.returncode == 0:
                                version = result.stdout.strip()
                                print(f"✅ Chrome 발견: {version}")
                                return True, version
                        except Exception as e:
                            print(f"Chrome 버전 확인 실패: {e}")
                            return True, "버전 확인 불가"
                
                print("❌ Chrome이 설치되지 않았습니다.")
                return False, "Chrome이 설치되지 않았습니다."
            
            else:
                # macOS/Linux에서 Chrome 설치 확인
                try:
                    result = subprocess.run(
                        ["google-chrome", "--version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        print(f"✅ Chrome 발견: {version}")
                        return True, version
                except:
                    pass
                
                # macOS에서 다른 경로 확인
                if platform.system() == 'Darwin':
                    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                    if os.path.exists(chrome_path):
                        try:
                            result = subprocess.run(
                                [chrome_path, "--version"], 
                                capture_output=True, 
                                text=True, 
                                timeout=10
                            )
                            if result.returncode == 0:
                                version = result.stdout.strip()
                                print(f"✅ Chrome 발견: {version}")
                                return True, version
                        except Exception as e:
                            print(f"Chrome 버전 확인 실패: {e}")
                            return True, "버전 확인 불가"
                
                print("❌ Chrome이 설치되지 않았습니다.")
                return False, "Chrome이 설치되지 않았습니다."
                
        except Exception as e:
            print(f"Chrome 확인 중 오류: {e}")
            return False, f"오류: {str(e)}"
    
    def get_chrome_version(self) -> Optional[str]:
        """
        설치된 Chrome 버전 추출
        
        Returns:
            Optional[str]: Chrome 버전 (예: "120.0.6099.109")
        """
        try:
            if self.is_windows:
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ]
                
                for chrome_path in chrome_paths:
                    if os.path.exists(chrome_path):
                        result = subprocess.run(
                            [chrome_path, "--version"], 
                            capture_output=True, 
                            text=True, 
                            timeout=10
                        )
                        if result.returncode == 0:
                            version_text = result.stdout.strip()
                            # "Google Chrome 120.0.6099.109"에서 "120.0.6099.109" 추출
                            version = version_text.split()[-1]
                            return version
            else:
                # macOS/Linux
                try:
                    result = subprocess.run(
                        ["google-chrome", "--version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    if result.returncode == 0:
                        version_text = result.stdout.strip()
                        version = version_text.split()[-1]
                        return version
                except:
                    pass
                
                if platform.system() == 'Darwin':
                    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                    if os.path.exists(chrome_path):
                        result = subprocess.run(
                            [chrome_path, "--version"], 
                            capture_output=True, 
                            text=True, 
                            timeout=10
                        )
                        if result.returncode == 0:
                            version_text = result.stdout.strip()
                            version = version_text.split()[-1]
                            return version
            
            return None
            
        except Exception as e:
            print(f"Chrome 버전 확인 중 오류: {e}")
            return None
    
    def get_chromedriver_version_info(self, chrome_version: str) -> Optional[str]:
        """
        Chrome 버전에 맞는 ChromeDriver 버전 정보 가져오기
        
        Args:
            chrome_version: Chrome 버전 (예: "120.0.6099.109")
            
        Returns:
            Optional[str]: ChromeDriver 버전 또는 None
        """
        if not REQUESTS_AVAILABLE:
            print("❌ requests 모듈이 없어 ChromeDriver 버전 정보를 가져올 수 없습니다.")
            return None
            
        try:
            # Chrome 버전에서 메이저 버전 추출 (예: "120")
            major_version = chrome_version.split('.')[0]
            
            # ChromeDriver API에서 버전 정보 가져오기
            if major_version.isdigit() and int(major_version) >= 115:
                # Chrome 115 이상은 새로운 API 사용
                url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{major_version}"
            else:
                # Chrome 114 이하는 구 API 사용
                url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            
            print(f"🔍 ChromeDriver 버전 정보 확인: {url}")
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                chromedriver_version = response.text.strip()
                print(f"✅ ChromeDriver 버전: {chromedriver_version}")
                return chromedriver_version
            else:
                print(f"❌ ChromeDriver 버전 정보 가져오기 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"ChromeDriver 버전 정보 확인 중 오류: {e}")
            return None
    
    def download_chromedriver(self, chromedriver_version: str) -> bool:
        """
        ChromeDriver 다운로드 및 설치
        
        Args:
            chromedriver_version: ChromeDriver 버전
            
        Returns:
            bool: 다운로드 성공 여부
        """
        if not REQUESTS_AVAILABLE:
            print("❌ requests 모듈이 없어 ChromeDriver를 다운로드할 수 없습니다.")
            return False
            
        try:
            # ChromeDriver 디렉토리 생성
            os.makedirs(self.chromedriver_dir, exist_ok=True)
            
            # 다운로드 URL 결정
            if self.is_windows:
                platform_name = "win32"
                executable_name = "chromedriver.exe"
            elif platform.system() == 'Darwin':
                # macOS에서 ARM64 (M1/M2/M3) vs x64 확인
                if platform.machine() == 'arm64':
                    platform_name = "mac-arm64"
                else:
                    platform_name = "mac-x64"
                executable_name = "chromedriver"
            else:
                platform_name = "linux64"
                executable_name = "chromedriver"
            
            # Chrome 버전에서 메이저 버전 추출
            chrome_version = self.get_chrome_version()
            if not chrome_version:
                print("❌ Chrome 버전을 확인할 수 없습니다.")
                return False
            
            major_version = chrome_version.split('.')[0]
            
            if major_version.isdigit() and int(major_version) >= 115:
                # Chrome 115 이상은 새로운 다운로드 URL
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{chromedriver_version}/{platform_name}/chromedriver-{platform_name}.zip"
            else:
                # Chrome 114 이하는 구 다운로드 URL
                url = f"https://chromedriver.storage.googleapis.com/{chromedriver_version}/chromedriver_{platform_name}.zip"
            
            print(f"📥 ChromeDriver 다운로드: {url}")
            
            # 파일 다운로드
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                print(f"❌ ChromeDriver 다운로드 실패: HTTP {response.status_code}")
                return False
            
            # ZIP 파일 저장
            zip_path = os.path.join(self.chromedriver_dir, "chromedriver.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ ChromeDriver ZIP 파일 다운로드 완료: {zip_path}")
            
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.chromedriver_dir)
            
            # ZIP 파일 삭제
            os.remove(zip_path)
            
            # 실행 권한 설정 (Windows가 아닌 경우)
            if not self.is_windows and os.path.exists(self.chromedriver_path):
                os.chmod(self.chromedriver_path, 0o755)
            
            # 다운로드 성공 확인
            if os.path.exists(self.chromedriver_path):
                print(f"✅ ChromeDriver 설치 완료: {self.chromedriver_path}")
                return True
            else:
                print(f"❌ ChromeDriver 설치 실패: {self.chromedriver_path} 파일이 없습니다.")
                return False
                
        except Exception as e:
            print(f"ChromeDriver 다운로드 중 오류: {e}")
            return False
    
    def setup_chromedriver(self) -> Tuple[bool, str]:
        """
        ChromeDriver 설정 (자동 다운로드 포함)
        
        Returns:
            Tuple[bool, str]: (성공 여부, 메시지)
        """
        try:
            # Chrome 설치 확인
            chrome_installed, chrome_info = self.check_chrome_installed()
            if not chrome_installed:
                return False, f"Chrome이 설치되지 않았습니다. {chrome_info}"
            
            # Chrome 버전 확인
            chrome_version = self.get_chrome_version()
            if not chrome_version:
                return False, "Chrome 버전을 확인할 수 없습니다."
            
            print(f"🔍 Chrome 버전: {chrome_version}")
            
            # 이미 ChromeDriver가 있는지 확인
            if os.path.exists(self.chromedriver_path):
                print(f"✅ ChromeDriver가 이미 설치되어 있습니다: {self.chromedriver_path}")
                return True, "ChromeDriver가 이미 설치되어 있습니다."
            
            # ChromeDriver 버전 정보 가져오기
            chromedriver_version = self.get_chromedriver_version_info(chrome_version)
            if not chromedriver_version:
                return False, "Chrome 버전에 맞는 ChromeDriver를 찾을 수 없습니다."
            
            # ChromeDriver 다운로드
            if self.download_chromedriver(chromedriver_version):
                return True, f"ChromeDriver {chromedriver_version} 설치 완료"
            else:
                return False, "ChromeDriver 다운로드에 실패했습니다."
                
        except Exception as e:
            print(f"ChromeDriver 설정 중 오류: {e}")
            return False, f"오류: {str(e)}"
    
    def get_chromedriver_path(self) -> Optional[str]:
        """
        ChromeDriver 경로 반환
        
        Returns:
            Optional[str]: ChromeDriver 경로 또는 None
        """
        if os.path.exists(self.chromedriver_path):
            return self.chromedriver_path
        return None
    
    def cleanup_chromedriver(self):
        """
        ChromeDriver 정리 (필요시 사용)
        """
        try:
            if os.path.exists(self.chromedriver_dir):
                shutil.rmtree(self.chromedriver_dir)
                print(f"🗑️ ChromeDriver 디렉토리 삭제: {self.chromedriver_dir}")
        except Exception as e:
            print(f"ChromeDriver 정리 중 오류: {e}")

# 테스트 함수
def test_chrome_manager():
    """ChromeManager 테스트"""
    print("🧪 ChromeManager 테스트 시작...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_manager = ChromeManager(base_dir)
    
    # Chrome 설치 확인
    chrome_installed, chrome_info = chrome_manager.check_chrome_installed()
    print(f"Chrome 설치 상태: {chrome_installed}")
    print(f"Chrome 정보: {chrome_info}")
    
    if chrome_installed:
        # ChromeDriver 설정
        success, message = chrome_manager.setup_chromedriver()
        print(f"ChromeDriver 설정: {success}")
        print(f"메시지: {message}")

if __name__ == "__main__":
    test_chrome_manager()
