import random
import time
from datetime import datetime, timedelta
import json
import os
import threading
from typing import List, Dict, Any, Optional, Callable

# 작업 우선순위 정의 (플레이리스트 모드에서는 순서대로 실행)
PRIORITY_MAP = {
    'blog': 1,
    'band': 1,
    'cafe': 1,
    'blog_reply': 1,
    'band_reply': 1,
    'neighbor_visit': 1,
    'idle': 2
}

TASK_TYPE_PRIORITY = {
    'morning': 1,
    'regular': 1,
    'closing': 1,
    'visit': 2,
    'reply': 3,
    'neighbor': 1,
    'reservation_batch': 1,
    '댓글답글': 1
}

class ScheduledTask:
    def __init__(self, task_id: str, platform: str, task_type: str, 
                 start_time: str = "00:00", end_time: str = "23:59", 
                 data: Optional[Dict[str, Any]] = None):
        self.task_id = task_id
        self.platform = platform
        self.task_type = task_type
        self.start_time_str = start_time  # 플레이리스트 모드에서는 사용 안함
        self.end_time_str = end_time
        self.data = data or {}
        
        self.scheduled_time: Optional[datetime] = None
        self.is_completed = False
        self.last_run_date: Optional[str] = None
        self.last_status = "ready"  # ready, running, completed, failed, paused

    def get_priority(self) -> int:
        """작업 우선순위 반환 (플레이리스트에서는 순서 우선)"""
        platform_priority = PRIORITY_MAP.get(self.platform, 5)
        type_priority = TASK_TYPE_PRIORITY.get(self.task_type, 5)
        return platform_priority * 10 + type_priority

    def reset_for_today(self):
        """작업 상태 초기화 (플레이리스트 모드용)"""
        self.is_completed = False
        self.last_status = "ready"

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "platform": self.platform,
            "task_type": self.task_type,
            "start_time": self.start_time_str,
            "end_time": self.end_time_str,
            "data": self.data,
            "scheduled_time": self.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if self.scheduled_time else None,
            "is_completed": self.is_completed,
            "last_status": self.last_status
        }


class SmartScheduler:
    """🎵 플레이리스트 스타일 스케줄러"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self.paused = False  # 일시정지 상태
        self.thread: Optional[threading.Thread] = None
        self.on_task_executed: Optional[Callable[[ScheduledTask], None]] = None
        
        # 현재 실행 위치 (플레이리스트 인덱스)
        self.current_index = 0
        
        # 작업 실행 락
        self.current_task_lock = threading.Lock()
        self.is_task_running = False
        
        # 🆕 매일 자동 시작 설정
        self.daily_auto_enabled = False
        self.daily_start_time = "07:00"  # 기본 시작 시간
        self.daily_random_range = 15  # ±15분 랜덤
        self.daily_auto_thread: Optional[threading.Thread] = None
        self._last_reset_date: Optional[str] = None  # 마지막 초기화 날짜
        
        # 🆕 특별 예약 (폴더 감지) 설정
        self.special_reservation_enabled = False
        self.special_reservations: List[Dict[str, str]] = [{"start": "09:00", "end": "10:00"}]
        self.current_special_slot_end: str = ""
        self.special_reservation_running = False
        self.special_reservation_thread: Optional[threading.Thread] = None
        self.on_special_reservation: Optional[Callable[[], None]] = None  # 시작 콜백 함수
        self.on_special_reservation_end: Optional[Callable[[], None]] = None  # 🆕 종료 콜백 함수
        self.paused_by_special = False  # 특별 예약으로 인한 일시정지 여부
        
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = []
                    for t in data:
                        task = ScheduledTask(
                            t.get('task_id', str(random.randint(1000, 9999))),
                            t['platform'],
                            t['task_type'],
                            t.get('start_time', '00:00'),
                            t.get('end_time', '23:59'),
                            t.get('data')
                        )
                        task.last_status = t.get('last_status', 'ready')
                        task.is_completed = t.get('is_completed', False)
                        self.tasks.append(task)
            except Exception as e:
                print(f"Error loading tasks: {e}")
                self.tasks = []

    def save_tasks(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump([t.to_dict() for t in self.tasks], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def add_task(self, platform, task_type, start_time="00:00", end_time="23:59", data=None):
        """🎵 플레이리스트에 작업 추가 (맨 뒤에 추가)"""
        task_id = f"{platform}_{task_type}_{int(time.time())}"
        task = ScheduledTask(task_id, platform, task_type, start_time, end_time, data)
        self.tasks.append(task)
        self.save_tasks()
        return task

    def remove_task(self, task_id: str):
        """작업 삭제"""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        self.save_tasks()

    def move_task_up(self, task: ScheduledTask):
        """🆕 작업 순서 위로 이동"""
        idx = self.tasks.index(task)
        if idx > 0:
            self.tasks[idx], self.tasks[idx-1] = self.tasks[idx-1], self.tasks[idx]
            self.save_tasks()

    def move_task_down(self, task: ScheduledTask):
        """🆕 작업 순서 아래로 이동"""
        idx = self.tasks.index(task)
        if idx < len(self.tasks) - 1:
            self.tasks[idx], self.tasks[idx+1] = self.tasks[idx+1], self.tasks[idx]
            self.save_tasks()

    def start(self):
        """▶️ 플레이리스트 시작 (처음부터 실행)"""
        if self.running:
            print("⚠️ 스케줄러가 이미 실행 중입니다.")
            return
        
        # 모든 작업 초기화
        self.current_index = 0
        for task in self.tasks:
            task.reset_for_today()
        self.save_tasks()
        
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._run_playlist, daemon=True)
        self.thread.start()
        print("▶️ 플레이리스트 스케줄러 시작됨")

    def pause(self):
        """⏸️ 일시정지 (현재 작업 완료 후 대기)"""
        if not self.running:
            print("⚠️ 스케줄러가 실행 중이 아닙니다.")
            return
        
        self.paused = True
        print("⏸️ 일시정지 요청됨 (현재 작업 완료 후 대기)")

    def resume(self):
        """▶️ 재개 (일시정지 해제)"""
        if not self.running:
            print("⚠️ 스케줄러가 실행 중이 아닙니다.")
            return
        
        if not self.paused:
            print("ℹ️ 이미 실행 중입니다.")
            return
        
        self.paused = False
        print("▶️ 플레이리스트 재개됨")

    def stop(self):
        """⏹️ 중지 (처음으로 초기화)"""
        self.running = False
        self.paused = False
        self.current_index = 0
        
        # 모든 작업 초기화
        for task in self.tasks:
            task.reset_for_today()
        self.save_tasks()
        
        if self.thread:
            self.thread.join(timeout=2)
        print("⏹️ 스케줄러 중지됨 (처음으로 초기화)")

    def _run_playlist(self):
        """🎵 플레이리스트 순차 실행 루프"""
        print(f"🎵 플레이리스트 실행 시작 - 총 {len(self.tasks)}개 작업")
        
        while self.running and self.current_index < len(self.tasks):
            # 일시정지 상태 확인
            if self.paused:
                print(f"⏸️ 일시정지 중... (현재 위치: {self.current_index + 1}/{len(self.tasks)})")
                time.sleep(1)
                continue
            
            # 현재 작업 가져오기
            task = self.tasks[self.current_index]
            
            # 이미 완료된 작업은 스킵
            if task.is_completed:
                print(f"⏭️ [{self.current_index + 1}/{len(self.tasks)}] {task.platform.upper()} - 이미 완료됨, 스킵")
                self.current_index += 1
                continue
            
            print(f"\n🎵 [{self.current_index + 1}/{len(self.tasks)}] 작업 실행: [{task.platform.upper()}] {task.task_type}")
            
            # ⏳ 대기 작업 처리 (Wait Task)
            if task.platform == 'wait':
                target_time = task.data.get('target_time')
                print(f"⏳ 대기 작업 시작: {target_time}까지 대기 중...")
                task.last_status = 'waiting'
                self.save_tasks()
                
                try:
                    # 목표 시간 파싱
                    now = datetime.now()
                    target_h, target_m = map(int, target_time.split(':'))
                    target_dt = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                    
                    # 이미 지난 시간이라면? (오늘 내일 결정)
                    # 사용자 의도는 "오늘 이 시간까지 기다려라"임.
                    # 만약 지금 14:00인데 09:00까지 기다리라고 하면? -> 이미 지났으므로 즉시 통과 (대기 안함)
                    if now >= target_dt:
                        print(f"⏩ 목표 시간({target_time})이 이미 지났으므로 즉시 다음 단계로 진행합니다.")
                    else:
                        # 대기 루프
                        while self.running and not self.paused:
                            now = datetime.now()
                            if now >= target_dt:
                                print(f"⏰ 목표 시간({target_time}) 도달! 대기 종료.")
                                break
                            
                            remaining = (target_dt - now).total_seconds()
                            if remaining > 60:
                                # 1분 이상 남았으면 로그 덜 찍기
                                if int(remaining) % 60 == 0:
                                    print(f"⏳ {target_time}까지 대기 중... ({int(remaining/60)}분 남음)")
                            else:
                                print(f"⏳ {target_time}까지 대기 중... ({int(remaining)}초 남음)")
                            
                            time.sleep(1)
                            
                            # 일시정지 체크 (루프 내부)
                            while self.paused and self.running:
                                time.sleep(1)

                    if self.running:
                        task.is_completed = True
                        task.last_status = 'completed'
                        task.last_run_date = datetime.now().strftime("%Y-%m-%d")
                        print(f"✅ 대기 작업 완료")
                        
                except Exception as e:
                    print(f"❌ 대기 작업 중 오류: {e}")
                    task.last_status = 'failed'
                
                self.save_tasks()
                self.current_index += 1
                continue

            with self.current_task_lock:
                self.is_task_running = True
            
            task.last_status = 'running'
            self.save_tasks()
            
            try:
                # 작업 실행 콜백 호출
                if self.on_task_executed:
                    self.on_task_executed(task)
                
                task.is_completed = True
                task.last_status = 'completed'
                task.last_run_date = datetime.now().strftime("%Y-%m-%d")
                print(f"✅ [{self.current_index + 1}/{len(self.tasks)}] 작업 완료: [{task.platform.upper()}] {task.task_type}")
                
            except Exception as e:
                print(f"❌ 작업 실행 중 오류: {e}")
                task.last_status = 'failed'
            
            finally:
                with self.current_task_lock:
                    self.is_task_running = False
                self.save_tasks()
            
            # 다음 작업으로 이동
            self.current_index += 1
            
            # 작업 간 대기 시간 (락이 있으므로 짧게)
            if self.running and self.current_index < len(self.tasks):
                print(f"⏳ 다음 작업 준비 중...")
                time.sleep(5)  # 5초 대기
        
        # 플레이리스트 완료
        if self.current_index >= len(self.tasks):
            print(f"\n🎉 플레이리스트 완료! 총 {len(self.tasks)}개 작업 처리됨")
            self.running = False

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        completed = [t for t in self.tasks if t.is_completed]
        pending = [t for t in self.tasks if not t.is_completed]
        
        return {
            "running": self.running,
            "paused": self.paused,
            "is_task_running": self.is_task_running,
            "current_index": self.current_index,
            "total_tasks": len(self.tasks),
            "pending": len(pending),
            "completed": len(completed),
            "progress": f"{self.current_index}/{len(self.tasks)}"
        }

    def get_current_task(self) -> Optional[ScheduledTask]:
        """현재 실행 중인 작업 반환"""
        if 0 <= self.current_index < len(self.tasks):
            return self.tasks[self.current_index]
        return None

    # ============================================
    # 🆕 매일 자동 초기화 및 시작 기능
    # ============================================
    
    def set_daily_auto_start(self, enabled: bool, start_time: str, random_range: int = 15):
        """매일 자동 시작 설정"""
        self.daily_auto_enabled = enabled
        self.daily_start_time = start_time
        self.daily_random_range = random_range
        
        if enabled:
            # 🆕 활성화 시점이 이미 시작 시간을 지났다면 오늘분은 건너뛰도록 설정
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            # 자정 초기화도 오늘분은 이미 완료된 것으로 간주 (즉시 초기화 방지)
            if not self._last_reset_date:
                self._last_reset_date = today_str
            
            try:
                # 시작 시간 파싱 및 오늘 시작 시간 계산
                start_h, start_m = map(int, start_time.split(':'))
                start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                
                # 만약 지금이 설정된 시간보다 늦다면, 오늘분은 시작한 것으로 간주하여 즉시 실행 방지
                if now >= start_dt:
                    self._today_started = True
                    self._today_started_date = today_str
                    self._today_random_delay_date = today_str
                    print(f"   ℹ️ 오늘 시작 시간({start_time})이 이미 지났습니다. 내일부터 정상 작동합니다.")
            except Exception as e:
                print(f"⚠️ 매일 자동 시작 시간 계산 중 오류: {e}")

        print(f"[Date] 매일 자동 시작 설정: {'활성화' if enabled else '비활성화'} (시간: {start_time}, 랜덤: ±{random_range}분)")
    
    def start_daily_auto_monitor(self):
        """매일 자동 시작 감시 스레드 시작"""
        if self.daily_auto_thread and self.daily_auto_thread.is_alive():
            return
        
        self.daily_auto_thread = threading.Thread(
            target=self._daily_auto_monitor_loop, 
            daemon=True
        )
        self.daily_auto_thread.start()
        print("🔄 매일 자동 시작 감시 시작됨")
    
    def stop_daily_auto_monitor(self):
        """매일 자동 시작 감시 스레드 중지"""
        self.daily_auto_enabled = False
        print("🔄 매일 자동 시작 감시 중지됨")
    
    def _daily_auto_monitor_loop(self):
        """매일 자동 초기화 및 시작 감시 루프"""
        print("🔍 매일 자동 시작 감시 루프 시작")
        
        while self.daily_auto_enabled:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            try:
                # 1️⃣ 자정 초기화 체크 (날짜가 바뀌면)
                if self._last_reset_date != today_str:
                    print(f"\n🌅 [일일 초기화] 새로운 날짜 감지: {today_str}")
                    self._reset_all_tasks()
                    self._last_reset_date = today_str
                    self.current_index = 0  # 처음부터 다시
                    print(f"✅ [일일 초기화] 모든 작업 초기화 완료")
                
                # 2️⃣ 설정된 시간에 자동 시작 (아직 실행 중이 아닐 때만)
                if not self.running:
                    # 시작 시간 파싱
                    start_h, start_m = map(int, self.daily_start_time.split(':'))
                    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    
                    # 랜덤 지연 계산 (한 번만)
                    if not hasattr(self, '_today_random_delay') or self._today_random_delay_date != today_str:
                        self._today_random_delay = random.randint(-self.daily_random_range, self.daily_random_range)
                        self._today_random_delay_date = today_str
                        actual_start = start_dt + timedelta(minutes=self._today_random_delay)
                        print(f"🎲 [일일 자동] 오늘 시작 시간: {actual_start.strftime('%H:%M')} (기본 {self.daily_start_time} + 랜덤 {self._today_random_delay}분)")
                    
                    actual_start = start_dt + timedelta(minutes=self._today_random_delay)
                    
                    # 시작 시간이 지났고 오늘 아직 시작 안 했으면 시작
                    if now >= actual_start:
                        if not hasattr(self, '_today_started') or self._today_started_date != today_str:
                            print(f"\n🚀 [일일 자동] 플레이리스트 자동 시작!")
                            self.start()
                            self._today_started = True
                            self._today_started_date = today_str
            
            except Exception as e:
                print(f"⚠️ 일일 자동 시작 감시 오류: {e}")
            
            time.sleep(60)  # 1분마다 체크
    
    def _reset_all_tasks(self):
        """모든 작업 상태 초기화"""
        for task in self.tasks:
            task.is_completed = False
            task.last_status = 'pending'
        self.save_tasks()

    # ============================================
    # 🆕 특별 예약 (폴더 감지) 기능
    # ============================================
    
    def set_special_reservations(self, enabled: bool, time_slots: List[Dict[str, str]]):
        """특별 예약 다중 시간대 설정"""
        self.special_reservation_enabled = enabled
        self.special_reservations = time_slots
        print(f"[Date] 특별 예약 설정: {enabled} ({len(time_slots)}개 시간대)")
    
    def start_special_reservation_monitor(self):
        """특별 예약 감시 스레드 시작"""
        if self.special_reservation_thread and self.special_reservation_thread.is_alive():
            return
        
        self.special_reservation_thread = threading.Thread(
            target=self._special_reservation_monitor_loop, 
            daemon=True
        )
        self.special_reservation_thread.start()
        print("🔍 특별 예약 감시 시작됨")
    
    def stop_special_reservation_monitor(self):
        """특별 예약 감시 스레드 중지"""
        self.special_reservation_enabled = False
        if self.special_reservation_thread:
            self.special_reservation_thread = None
        print("🔍 특별 예약 감시 중지됨")
    
    def _special_reservation_monitor_loop(self):
        """특별 예약 시간 감시 루프"""
        print("🔍 특별 예약 감시 루프 시작")
        
        while self.special_reservation_enabled:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            
            try:
                is_in_special_time = False
                matched_slot = None
                
                # 등록된 모든 시간대를 순회하며 현재 시간이 포함되는지 확인
                for slot in self.special_reservations:
                    start_h, start_m = map(int, slot["start"].split(':'))
                    end_h, end_m = map(int, slot["end"].split(':'))
                    
                    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    end_dt = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                    
                    if start_dt <= now <= end_dt:
                        is_in_special_time = True
                        matched_slot = slot
                        break
                
                if is_in_special_time and not self.special_reservation_running:
                    # 특별 예약 시간 시작!
                    self.current_special_slot_end = matched_slot["end"]
                    print(f"\n🚨 [특별 예약] 시간 도달! ({matched_slot['start']} ~ {matched_slot['end']})")
                    self._run_special_reservation()
                    
                elif not is_in_special_time and self.paused_by_special:
                    # 특별 예약 시간 종료 → 플레이리스트 재개
                    print(f"✅ [특별 예약] 시간 종료 - 플레이리스트 재개")
                    self.paused_by_special = False
                    self.special_reservation_running = False
                    if self.running:
                        self.paused = False
            
            except Exception as e:
                print(f"⚠️ 특별 예약 감시 오류: {e}")
            
            time.sleep(30)  # 30초마다 체크
    
    def _run_special_reservation(self):
        """특별 예약 (폴더 감지) 실행"""
        self.special_reservation_running = True
        
        # 플레이리스트 일시정지
        if self.running and not self.paused:
            print("⏸️ [특별 예약] 플레이리스트 일시정지")
            self.paused = True
            self.paused_by_special = True
            
            # 현재 작업이 완료될 때까지 대기
            while self.is_task_running:
                print("   ⏳ 현재 작업 완료 대기 중...")
                time.sleep(3)
        
        # 콜백 함수 실행 (폴더 감지 작업)
        if self.on_special_reservation:
            print("🚀 [특별 예약] 폴더 감지 작업 시작!")
            try:
                self.on_special_reservation()
                print("✅ [특별 예약] 폴더 감지 작업 완료!")
            except Exception as e:
                print(f"❌ [특별 예약] 폴더 감지 작업 오류: {e}")
        else:
            print("⚠️ [특별 예약] 콜백 함수가 설정되지 않았습니다.")
        
        # 종료 시간까지 대기 (추가 폴더 감지가 있을 수 있음)
        while True:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            
            try:
                if not self.current_special_slot_end:
                    break
                    
                end_h, end_m = map(int, self.current_special_slot_end.split(':'))
                end_dt = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                
                if now >= end_dt:
                    break
                    
                remaining = (end_dt - now).total_seconds()
                print(f"⏳ [특별 예약] 종료까지 {int(remaining/60)}분 {int(remaining%60)}초 남음...")
                time.sleep(60)  # 1분마다 체크
                
            except:
                break
        
        # 특별 예약 종료 → 폴더 감지 중지 + 플레이리스트 재개
        print("✅ [특별 예약] 종료 - 폴더 감지 중지 및 플레이리스트 자동 재개")
        
        # 🆕 종료 콜백 호출 (폴더 감지 중지)
        if self.on_special_reservation_end:
            try:
                print("🛑 [특별 예약] 폴더 감지 중지 중...")
                self.on_special_reservation_end()
                print("✅ [특별 예약] 폴더 감지 중지 완료")
            except Exception as e:
                print(f"⚠️ [특별 예약] 폴더 감지 중지 오류: {e}")
        
        self.special_reservation_running = False
        if self.paused_by_special:
            self.paused = False
            self.paused_by_special = False


# 사용 예시 (디버깅용)
if __name__ == "__main__":
    scheduler = SmartScheduler("scheduler_config.json")
    if not scheduler.tasks:
        scheduler.add_task("band", "morning")
        scheduler.add_task("blog", "regular")
        scheduler.add_task("cafe", "regular")
    
    def handle_task(task):
        print(f"Task Triggered: {task.to_dict()}")
        time.sleep(2)  # 작업 시뮬레이션
        
    scheduler.on_task_executed = handle_task
    scheduler.start()
    
    print("Scheduler running... Press Ctrl+C to stop.")
    try:
        while scheduler.running:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
