
import os
import glob
import unicodedata

def find_real_path():
    print(" === 🔍 구글 드라이브 경로 찾는 중... === \n")
    
    home = os.path.expanduser("~")
    # 가능한 모든 패턴 검색
    patterns = [
        os.path.join(home, "내 드라이브*"),
        os.path.join(home, "Google Drive*"),
        "/Volumes/GoogleDrive*"
    ]
    
    found_paths = []
    
    for pattern in patterns:
        for path in glob.glob(pattern):
            found_paths.append(path)
            
    if not found_paths:
        print("❌ 구글 드라이브 폴더를 찾을 수 없습니다.")
        print("   구글 드라이브 앱이 켜져 있는지 확인해 주세요!")
        return

    print("✅ 발견된 구글 드라이브 경로:")
    
    for drive_path in found_paths:
        # 수련사진및영상 폴더 찾기
        target_path = os.path.join(drive_path, "수련사진및영상")
        
        # NFD(자소분리) -> NFC(완성형) 변환
        nfc_path = unicodedata.normalize('NFC', target_path)
        
        if os.path.exists(target_path) or os.path.exists(nfc_path):
            print(f"\n[🎯 복사해서 붙여넣으세요!]")
            print(f"{nfc_path}")
            return
        else:
             # 혹시 폴더 이름이 자소분리되어 있을 수 있으니 직접 검색
             sub_folders = glob.glob(os.path.join(drive_path, "*"))
             for sub in sub_folders:
                 if "수련사진" in unicodedata.normalize('NFC', sub):
                     print(f"\n[🎯 복사해서 붙여넣으세요!]")
                     print(f"{unicodedata.normalize('NFC', sub)}")
                     return

    print("\n⚠️ '수련사진및영상' 폴더를 찾지 못했습니다.")
    print("   폴더 이름이 정확한지 확인해 주세요.")

if __name__ == "__main__":
    find_real_path()
