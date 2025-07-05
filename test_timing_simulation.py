import time
import threading
from datetime import datetime

class GPTResponseSimulator:
    """GPT 응답 시뮬레이션"""
    def __init__(self):
        self.is_generating = False
        self.response_ready = False
        self.title = ""
        self.content = ""
        
    def start_generation(self, topic):
        """GPT 응답 생성 시작 (비동기)"""
        self.is_generating = True
        self.response_ready = False
        self.title = ""
        self.content = ""
        
        def generate():
            print(f"🤖 GPT 응답 생성 시작: {topic}")
            # 실제 GPT 응답 시간 시뮬레이션 (3-7초 랜덤)
            import random
            response_time = random.uniform(3, 7)
            print(f"⏱️ 예상 응답 시간: {response_time:.1f}초")
            
            time.sleep(response_time)
            
            # 응답 완료
            self.title = f"[생성된 제목] {topic}"
            self.content = f"[생성된 내용] {topic}에 대한 상세한 블로그 글입니다..."
            self.is_generating = False
            self.response_ready = True
            print(f"✅ GPT 응답 생성 완료 ({response_time:.1f}초 소요)")
            
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()

class PostingSimulator:
    """포스팅 시뮬레이션"""
    def __init__(self):
        self.gpt_sim = GPTResponseSimulator()
        
    def method_2_fixed_wait(self, topic, wait_seconds=10):
        """방안 2: 고정 대기 시간"""
        print(f"\n🔥 방안 2 시뮬레이션 시작 (고정 대기 {wait_seconds}초)")
        start_time = time.time()
        
        # 1. GPT 응답 시작
        self.gpt_sim.start_generation(topic)
        
        # 2. 고정 시간 대기
        print(f"⏳ {wait_seconds}초 고정 대기 중...")
        time.sleep(wait_seconds)
        
        # 3. 응답 상태 확인
        if self.gpt_sim.response_ready:
            print(f"✅ 성공: GPT 응답 완료됨")
            print(f"📄 제목: {self.gpt_sim.title}")
            success = True
        else:
            print(f"❌ 실패: GPT 응답 아직 미완료")
            print(f"🔄 생성 중: {self.gpt_sim.is_generating}")
            success = False
            
        total_time = time.time() - start_time
        print(f"⏱️ 총 소요 시간: {total_time:.1f}초")
        return success, total_time
        
    def method_3_smart_wait(self, topic, max_wait=30, check_interval=1):
        """방안 3: 상태 확인 루프"""
        print(f"\n🧠 방안 3 시뮬레이션 시작 (스마트 대기, 최대 {max_wait}초)")
        start_time = time.time()
        
        # 1. GPT 응답 시작
        self.gpt_sim.start_generation(topic)
        
        # 2. 상태 확인 루프
        waited_time = 0
        while waited_time < max_wait:
            time.sleep(check_interval)
            waited_time += check_interval
            
            print(f"🔍 {waited_time}초 경과 - GPT 상태 확인 중...")
            
            if self.gpt_sim.response_ready:
                print(f"✅ 성공: GPT 응답 완료됨 ({waited_time}초 대기)")
                print(f"📄 제목: {self.gpt_sim.title}")
                success = True
                break
        else:
            print(f"❌ 실패: {max_wait}초 타임아웃")
            success = False
            
        total_time = time.time() - start_time
        print(f"⏱️ 총 소요 시간: {total_time:.1f}초")
        return success, total_time

def run_comparison_test():
    """두 방안 비교 테스트"""
    print("=" * 60)
    print("🎯 GPT 응답 시간 vs 포스팅 타이밍 시뮬레이션")
    print("=" * 60)
    
    topics = ["태권도 기본 동작", "합기도 호신술", "무도 정신"]
    
    results_method_2 = []
    results_method_3 = []
    
    for i, topic in enumerate(topics, 1):
        print(f"\n📝 테스트 {i}: {topic}")
        print("-" * 40)
        
        # 방안 2 테스트 (10초 고정 대기)
        sim_2 = PostingSimulator()
        success_2, time_2 = sim_2.method_2_fixed_wait(topic, 10)
        results_method_2.append((success_2, time_2))
        
        time.sleep(1)  # 테스트 간 간격
        
        # 방안 3 테스트 (스마트 대기)
        sim_3 = PostingSimulator()
        success_3, time_3 = sim_3.method_3_smart_wait(topic, 30, 1)
        results_method_3.append((success_3, time_3))
        
        time.sleep(2)  # 다음 테스트를 위한 대기
    
    # 결과 분석
    print("\n" + "=" * 60)
    print("📊 시뮬레이션 결과 분석")
    print("=" * 60)
    
    # 방안 2 결과
    success_rate_2 = sum(1 for success, _ in results_method_2 if success) / len(results_method_2) * 100
    avg_time_2 = sum(time for _, time in results_method_2) / len(results_method_2)
    
    print(f"\n🔥 방안 2 (고정 대기 10초):")
    print(f"   성공률: {success_rate_2:.1f}%")
    print(f"   평균 시간: {avg_time_2:.1f}초")
    print(f"   장점: 구현 간단, 예측 가능한 시간")
    print(f"   단점: 비효율적, GPT 빠를 때 시간 낭비")
    
    # 방안 3 결과
    success_rate_3 = sum(1 for success, _ in results_method_3 if success) / len(results_method_3) * 100
    avg_time_3 = sum(time for _, time in results_method_3) / len(results_method_3)
    
    print(f"\n🧠 방안 3 (스마트 대기):")
    print(f"   성공률: {success_rate_3:.1f}%")
    print(f"   평균 시간: {avg_time_3:.1f}초")
    print(f"   장점: 효율적, 실제 필요 시간만 대기")
    print(f"   단점: 구현 복잡, 디버깅 어려움")
    
    # 권장사항
    print(f"\n🎯 권장사항:")
    if success_rate_3 >= success_rate_2 and avg_time_3 <= avg_time_2:
        print(f"   ✅ 방안 3 (스마트 대기) 권장")
        print(f"   이유: 더 높은 성공률과 효율적인 시간 사용")
    elif success_rate_2 > success_rate_3:
        print(f"   ✅ 방안 2 (고정 대기) 권장")
        print(f"   이유: 더 높은 성공률 (안정성 우선)")
    else:
        print(f"   ⚖️ 상황에 따라 선택")
        print(f"   빠른 구현: 방안 2, 효율성: 방안 3")

if __name__ == "__main__":
    run_comparison_test() 