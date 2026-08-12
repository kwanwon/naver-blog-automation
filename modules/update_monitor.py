#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업데이트 모니터링 시스템
업데이트 성공률 추적 및 피드백 수집
"""

import os
import json
import time
from datetime import datetime, timedelta
import logging

class UpdateMonitor:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.monitor_file = os.path.join(self.base_dir, 'config', 'update_monitor.json')
        self.logger = self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logger = logging.getLogger('update_monitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def load_monitor_data(self):
        """모니터링 데이터 로드"""
        try:
            if os.path.exists(self.monitor_file):
                with open(self.monitor_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.create_default_monitor_data()
        except Exception as e:
            self.logger.error(f"모니터링 데이터 로드 실패: {e}")
            return self.create_default_monitor_data()
    
    def create_default_monitor_data(self):
        """기본 모니터링 데이터 생성"""
        return {
            "update_attempts": [],
            "update_successes": [],
            "update_failures": [],
            "version_history": [],
            "user_feedback": [],
            "statistics": {
                "total_attempts": 0,
                "total_successes": 0,
                "total_failures": 0,
                "success_rate": 0.0,
                "last_update_check": None,
                "last_successful_update": None
            }
        }
    
    def save_monitor_data(self, data):
        """모니터링 데이터 저장"""
        try:
            os.makedirs(os.path.dirname(self.monitor_file), exist_ok=True)
            with open(self.monitor_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"모니터링 데이터 저장 실패: {e}")
    
    def record_update_attempt(self, current_version, target_version):
        """업데이트 시도 기록"""
        try:
            data = self.load_monitor_data()
            
            attempt = {
                "timestamp": datetime.now().isoformat(),
                "current_version": current_version,
                "target_version": target_version,
                "status": "attempted"
            }
            
            data["update_attempts"].append(attempt)
            data["statistics"]["total_attempts"] += 1
            data["statistics"]["last_update_check"] = datetime.now().isoformat()
            
            # 최근 100개만 유지
            if len(data["update_attempts"]) > 100:
                data["update_attempts"] = data["update_attempts"][-100:]
            
            self.save_monitor_data(data)
            self.logger.info(f"업데이트 시도 기록: {current_version} -> {target_version}")
            
        except Exception as e:
            self.logger.error(f"업데이트 시도 기록 실패: {e}")
    
    def record_update_success(self, current_version, new_version, duration=None):
        """업데이트 성공 기록"""
        try:
            data = self.load_monitor_data()
            
            success = {
                "timestamp": datetime.now().isoformat(),
                "from_version": current_version,
                "to_version": new_version,
                "duration_seconds": duration,
                "status": "success"
            }
            
            data["update_successes"].append(success)
            data["statistics"]["total_successes"] += 1
            data["statistics"]["last_successful_update"] = datetime.now().isoformat()
            
            # 버전 히스토리 업데이트
            data["version_history"].append({
                "version": new_version,
                "installed_at": datetime.now().isoformat(),
                "previous_version": current_version
            })
            
            # 성공률 계산
            total_attempts = data["statistics"]["total_attempts"]
            if total_attempts > 0:
                data["statistics"]["success_rate"] = data["statistics"]["total_successes"] / total_attempts * 100
            
            # 최근 100개만 유지
            if len(data["update_successes"]) > 100:
                data["update_successes"] = data["update_successes"][-100:]
            if len(data["version_history"]) > 50:
                data["version_history"] = data["version_history"][-50:]
            
            self.save_monitor_data(data)
            self.logger.info(f"업데이트 성공 기록: {current_version} -> {new_version}")
            
        except Exception as e:
            self.logger.error(f"업데이트 성공 기록 실패: {e}")
    
    def record_update_failure(self, current_version, target_version, error_message):
        """업데이트 실패 기록"""
        try:
            data = self.load_monitor_data()
            
            failure = {
                "timestamp": datetime.now().isoformat(),
                "current_version": current_version,
                "target_version": target_version,
                "error_message": str(error_message),
                "status": "failed"
            }
            
            data["update_failures"].append(failure)
            data["statistics"]["total_failures"] += 1
            
            # 성공률 재계산
            total_attempts = data["statistics"]["total_attempts"]
            if total_attempts > 0:
                data["statistics"]["success_rate"] = data["statistics"]["total_successes"] / total_attempts * 100
            
            # 최근 100개만 유지
            if len(data["update_failures"]) > 100:
                data["update_failures"] = data["update_failures"][-100:]
            
            self.save_monitor_data(data)
            self.logger.warning(f"업데이트 실패 기록: {current_version} -> {target_version} - {error_message}")
            
        except Exception as e:
            self.logger.error(f"업데이트 실패 기록 실패: {e}")
    
    def record_user_feedback(self, feedback_type, message, version=None):
        """사용자 피드백 기록"""
        try:
            data = self.load_monitor_data()
            
            feedback = {
                "timestamp": datetime.now().isoformat(),
                "type": feedback_type,  # "positive", "negative", "suggestion", "bug_report"
                "message": message,
                "version": version,
                "user_id": "anonymous"  # 개인정보 보호
            }
            
            data["user_feedback"].append(feedback)
            
            # 최근 200개만 유지
            if len(data["user_feedback"]) > 200:
                data["user_feedback"] = data["user_feedback"][-200:]
            
            self.save_monitor_data(data)
            self.logger.info(f"사용자 피드백 기록: {feedback_type} - {message[:50]}...")
            
        except Exception as e:
            self.logger.error(f"사용자 피드백 기록 실패: {e}")
    
    def get_statistics(self):
        """통계 정보 반환"""
        try:
            data = self.load_monitor_data()
            stats = data["statistics"].copy()
            
            # 추가 통계 계산
            now = datetime.now()
            
            # 최근 30일 성공률
            recent_successes = [s for s in data["update_successes"] 
                              if datetime.fromisoformat(s["timestamp"]) > now - timedelta(days=30)]
            recent_attempts = [a for a in data["update_attempts"] 
                             if datetime.fromisoformat(a["timestamp"]) > now - timedelta(days=30)]
            
            if len(recent_attempts) > 0:
                stats["recent_success_rate"] = len(recent_successes) / len(recent_attempts) * 100
            else:
                stats["recent_success_rate"] = 0.0
            
            # 평균 업데이트 시간
            successful_updates_with_duration = [s for s in data["update_successes"] 
                                              if s.get("duration_seconds")]
            if successful_updates_with_duration:
                avg_duration = sum(s["duration_seconds"] for s in successful_updates_with_duration) / len(successful_updates_with_duration)
                stats["average_update_duration"] = round(avg_duration, 2)
            else:
                stats["average_update_duration"] = None
            
            # 최근 피드백 요약
            recent_feedback = [f for f in data["user_feedback"] 
                             if datetime.fromisoformat(f["timestamp"]) > now - timedelta(days=30)]
            stats["recent_feedback_count"] = len(recent_feedback)
            
            feedback_types = {}
            for feedback in recent_feedback:
                feedback_type = feedback["type"]
                feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1
            stats["feedback_breakdown"] = feedback_types
            
            return stats
            
        except Exception as e:
            self.logger.error(f"통계 계산 실패: {e}")
            return {}
    
    def generate_report(self):
        """모니터링 리포트 생성"""
        try:
            stats = self.get_statistics()
            
            report = f"""
📊 업데이트 시스템 모니터링 리포트
{'='*50}

📈 전체 통계:
- 총 업데이트 시도: {stats.get('total_attempts', 0)}회
- 성공: {stats.get('total_successes', 0)}회
- 실패: {stats.get('total_failures', 0)}회
- 전체 성공률: {stats.get('success_rate', 0):.1f}%

[Date] 최근 30일:
- 성공률: {stats.get('recent_success_rate', 0):.1f}%
- 평균 업데이트 시간: {stats.get('average_update_duration', 'N/A')}초

💬 사용자 피드백:
- 최근 30일 피드백: {stats.get('recent_feedback_count', 0)}건
"""
            
            feedback_breakdown = stats.get('feedback_breakdown', {})
            if feedback_breakdown:
                report += "- 피드백 유형별:\n"
                for feedback_type, count in feedback_breakdown.items():
                    report += f"  • {feedback_type}: {count}건\n"
            
            if stats.get('last_successful_update'):
                last_update = datetime.fromisoformat(stats['last_successful_update'])
                report += f"\n[Time] 마지막 성공 업데이트: {last_update.strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
            
        except Exception as e:
            self.logger.error(f"리포트 생성 실패: {e}")
            return "리포트 생성 중 오류가 발생했습니다."
    
    def cleanup_old_data(self, days=90):
        """오래된 데이터 정리"""
        try:
            data = self.load_monitor_data()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 오래된 데이터 필터링
            data["update_attempts"] = [a for a in data["update_attempts"] 
                                     if datetime.fromisoformat(a["timestamp"]) > cutoff_date]
            data["update_successes"] = [s for s in data["update_successes"] 
                                      if datetime.fromisoformat(s["timestamp"]) > cutoff_date]
            data["update_failures"] = [f for f in data["update_failures"] 
                                     if datetime.fromisoformat(f["timestamp"]) > cutoff_date]
            data["user_feedback"] = [f for f in data["user_feedback"] 
                                   if datetime.fromisoformat(f["timestamp"]) > cutoff_date]
            
            self.save_monitor_data(data)
            self.logger.info(f"{days}일 이전 데이터 정리 완료")
            
        except Exception as e:
            self.logger.error(f"데이터 정리 실패: {e}")

def main():
    """테스트 및 리포트 생성"""
    monitor = UpdateMonitor()
    
    print("📊 업데이트 모니터링 시스템")
    print("=" * 40)
    
    # 통계 표시
    print(monitor.generate_report())
    
    # 데이터 정리 (90일 이전)
    monitor.cleanup_old_data(90)

if __name__ == "__main__":
    main()
