#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromeDriver 자동 수정 스크립트
- macOS 보안 속성 자동 제거
- 실행 권한 자동 설정
- 손상된 ChromeDriver 자동 재다운로드
"""

import os
import subprocess
import stat
import time
import platform
from pathlib import Path

class ChromeDriverAutoFixer:
    def __init__(self):
        self.system = platform.system()
        self.wdm_base_path = Path.home() / ".wdm" / "drivers" / "chromedriver"
        
    def find_chromedriver_files(self):
        """모든 ChromeDriver 파일 찾기"""
        chromedriver_files = []
        
        if self.wdm_base_path.exists():
            # .wdm 폴더에서 ChromeDriver 찾기
            for path in self.wdm_base_path.rglob("chromedriver"):
                if path.is_file() and not path.name.endswith('.chromedriver'):
                    chromedriver_files.append(path)
                    
        return chromedriver_files
    
    def fix_macos_chromedriver(self, chromedriver_path):
        """macOS ChromeDriver 보안 속성 및 권한 수정"""
        try:
            print(f"🔧 ChromeDriver 수정 중: {chromedriver_path}")
            
            # 1. 확장 속성 확인 및 제거
            try:
                result = subprocess.run(['xattr', '-l', str(chromedriver_path)], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"  📋 발견된 확장 속성:")
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            print(f"    - {line.strip()}")
                    
                    # 모든 확장 속성 제거
                    subprocess.run(['xattr', '-c', str(chromedriver_path)], 
                                 check=True, timeout=10)
                    print(f"  ✅ 확장 속성 제거 완료")
                else:
                    print(f"  ✅ 확장 속성 없음")
                    
            except subprocess.TimeoutExpired:
                print(f"  ⚠️ xattr 명령 타임아웃")
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️ xattr 명령 실패: {e}")
            
            # 2. 실행 권한 설정
            try:
                # 755 권한 설정 (rwxr-xr-x)
                os.chmod(chromedriver_path, 0o755)
                print(f"  ✅ 실행 권한 설정 완료")
            except Exception as e:
                print(f"  ❌ 권한 설정 실패: {e}")
                return False
            
            # 3. 실행 테스트
            try:
                result = subprocess.run([str(chromedriver_path), '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"  🎉 실행 테스트 성공: {version}")
                    return True
                else:
                    print(f"  ❌ 실행 테스트 실패: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                print(f"  ❌ 실행 테스트 타임아웃")
                return False
            except Exception as e:
                print(f"  ❌ 실행 테스트 오류: {e}")
                return False
                
        except Exception as e:
            print(f"❌ ChromeDriver 수정 중 오류: {e}")
            return False
    
    def clean_corrupted_wdm_cache(self):
        """손상된 WebDriverManager 캐시 정리"""
        try:
            print("🧹 WebDriverManager 캐시 정리 중...")
            
            if self.wdm_base_path.exists():
                import shutil
                shutil.rmtree(self.wdm_base_path)
                print("✅ 캐시 정리 완료 - 새로운 ChromeDriver가 자동 다운로드됩니다")
                return True
            else:
                print("✅ 캐시 폴더 없음")
                return True
                
        except Exception as e:
            print(f"❌ 캐시 정리 실패: {e}")
            return False
    
    def auto_fix_all(self):
        """모든 ChromeDriver 자동 수정"""
        print("🚀 ChromeDriver 자동 수정 시작...")
        
        if self.system != "Darwin":
            print("ℹ️  macOS가 아니므로 수정 건너뜀")
            return True
        
        chromedriver_files = self.find_chromedriver_files()
        
        if not chromedriver_files:
            print("📂 ChromeDriver 파일을 찾을 수 없습니다")
            print("   처음 실행 시 WebDriverManager가 자동으로 다운로드합니다")
            return True
        
        print(f"📋 발견된 ChromeDriver 파일: {len(chromedriver_files)}개")
        
        success_count = 0
        for chromedriver_path in chromedriver_files:
            if self.fix_macos_chromedriver(chromedriver_path):
                success_count += 1
        
        print(f"✅ 수정 완료: {success_count}/{len(chromedriver_files)}개")
        
        if success_count == 0:
            print("⚠️  모든 ChromeDriver 수정 실패 - 캐시 정리를 시도합니다")
            return self.clean_corrupted_wdm_cache()
        
        return success_count > 0

def main():
    """메인 실행 함수"""
    fixer = ChromeDriverAutoFixer()
    success = fixer.auto_fix_all()
    
    if success:
        print("🎉 ChromeDriver 자동 수정 완료!")
        return 0
    else:
        print("❌ ChromeDriver 수정 실패")
        return 1

if __name__ == "__main__":
    exit(main()) 