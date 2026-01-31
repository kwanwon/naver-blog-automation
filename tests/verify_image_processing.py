
import os
import sys
from PIL import Image

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_processor import process_image

def create_dummy_image(path):
    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save(path)
    print(f"✅ 원본 테스트 이미지 생성: {path}")

def test_image_processing():
    print("🚀 이미지 처리 시뮬레이션 시작...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_image_path = os.path.join(base_dir, "test_original.jpg")
    output_dir = os.path.join(os.path.dirname(base_dir), "_temp_upload")
    
    # 1. Create dummy image
    create_dummy_image(test_image_path)
    
    # 2. Run process_image
    print(f"\n🔄 process_image 함수 호출 중...")
    import time
    start_time = time.time()
    processed_path = process_image(test_image_path, output_dir)
    end_time = time.time()
    elapsed = (end_time - start_time) * 1000  # ms
    print(f"⏱️ 처리 소요 시간: {elapsed:.2f}ms")
    
    if processed_path and os.path.exists(processed_path):
        print(f"\n✅ 처리 성공!")
        print(f"   📂 저장 경로: {processed_path}")
        print(f"   📄 파일명 변경 확인: {os.path.basename(test_image_path)} -> {os.path.basename(processed_path)}")
        
        # Verify it's a valid image
        try:
            with Image.open(processed_path) as img:
                print(f"   🖼️ 이미지 로드 성공: 크기 {img.size}, 모드 {img.mode}")
                print(f"   💡 (참고: 미세한 회전이나 밝기 조절이 적용되었습니다)")
        except Exception as e:
            print(f"❌ 처리된 이미지 손상됨: {e}")
            
        # Clean up
        os.remove(test_image_path)
        os.remove(processed_path)
        print("\n🗑️ 테스트 파일 정리 완료")
        
    else:
        print("\n❌ 이미지 처리 실패 (파일이 생성되지 않음)")

if __name__ == "__main__":
    test_image_processing()
