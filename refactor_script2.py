import os

APP_PATH = "/Users/gm2hapkido/Desktop/라이온개발자/blog_writer_app.py"

with open(APP_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. upload_to_blog 교체
import re

# `def upload_to_blog` 부터 `return False` 직전까지 찾기 (정확히 어디까지인지 정규식으로)
# 사실상 try 밖은 건드리지 않고, dlg 생성 직후부터 끝까지 교체.

# upload_to_blog() 내부의 복잡한 로직을 _execute_unified_blog_posting 호출로 단순화합니다.
def replace_upload_to_blog(text):
    start_marker = "                # 줄바꿈 처리 (한 줄이 25자를 넘지 않도록, 단어가 잘리지 않게)"
    end_marker = "                    # 사용 횟수 증가"
    
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("upload_to_blog 블록을 찾을 수 없습니다.")
        return text
        
    replacement = """
                # [리팩토링] 통합 파이프라인 호출
                dlg.content.controls[0].value = "블로그 포스팅 작성 중..."
                page.update()
                
                gpt_tags = getattr(self, 'current_tags', [])
                
                success = self._execute_unified_blog_posting(
                    page=page,
                    topic=title_input.value,
                    content_str=content_input.value,
                    target_folder=None,
                    reservation_time=None,
                    ai_tags=gpt_tags,
                    title=title_input.value
                )
                
                if not success:
                    raise Exception("통합 파이프라인 업로드 실패")
                    
"""
    return text[:start_idx] + replacement + text[end_idx:]

content = replace_upload_to_blog(content)


# 2. _on_blog_drive_detected 교체
def replace_folder_watch(text):
    start_marker = "                # 이미지 핸들러 초기화 (감지된 폴더의 이미지들을 로드함)"
    end_marker = "                    print(f\"❌ [DriveWatcher] 블로그 자동 포스팅 실패\")"
    
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("_on_blog_drive_detected 블록을 찾을 수 없습니다.")
        return text
        
    # start_marker를 포함해서 위로 `blog_auto = NaverBlogAutomation` 부분도 다 지움
    start_marker_full = "                # 인스턴스 생성 (감지된 폴더를 이미지 소스로 사용)"
    start_idx_full = text.find(start_marker_full)
    
    end_idx_full = end_idx + len("                    print(f\"❌ [DriveWatcher] 블로그 자동 포스팅 실패\")")
    
    replacement = """
                # [리팩토링] 통합 파이프라인 호출
                success = self._execute_unified_blog_posting(
                    page=self.page_ref,
                    topic=title,
                    content_str=content,
                    target_folder=folder_path,
                    reservation_time=None,
                    ai_tags=result.get('tags', []),
                    title=title
                )
                
                if success:
                    print(f"✅ [DriveWatcher] 블로그 자동 포스팅 완료!")
                    # 처리된 파일 중앙 백업 폴더로 이동 (FileManager 사용)
                    self.file_manager.move_to_backup(files, folder_name)
                else:
                    print(f"❌ [DriveWatcher] 블로그 자동 포스팅 실패")
"""
    return text[:start_idx_full] + replacement + text[end_idx_full:]

content = replace_folder_watch(content)


# 3. 스케줄러 (handle_scheduled_task) 블로그 예약 모드 교체
def replace_scheduler_blog(text):
    start_marker = "                        # 태그: GPT 태그 + 사용자 설정 태그 병합"
    end_marker = "                            print(\"    ⏸️ '자동 발행'이 꺼져 있어 수동 발행을 위해 대기합니다.\")"
    
    start_idx = text.find(start_marker)
    if start_idx == -1:
        print("scheduler blog 블록을 찾을 수 없습니다.")
        return text
        
    # end_marker는 한참 뒤에 있음
    # wait_seconds 전까지 지움
    end_marker_full = "                            reservation_success = True"
    end_idx = text.find(end_marker_full, start_idx)
    
    if end_idx == -1:
        print("scheduler blog end 블록을 찾을 수 없습니다.")
        return text
        
    end_idx_full = end_idx + len(end_marker_full)
    
    replacement = """
                        # [리팩토링] 통합 파이프라인 호출
                        # 예약 모드: res_time 을 reservation_time 파라미터로 전달
                        success = self._execute_unified_blog_posting(
                            page=self.page_ref,
                            topic=title,
                            content_str=content,
                            target_folder=None,
                            reservation_time=res_time,
                            ai_tags=result.get('tags', []),
                            title=title
                        )
                        
                        if success:
                            success_cnt += 1
                            print(f"    ✅ 블로그 예약/발행 통합 파이프라인 성공")
                            publish_success = True
                            reservation_success = True
                        else:
                            print(f"    ❌ 블로그 예약/발행 통합 파이프라인 실패")
"""
    return text[:start_idx] + replacement + text[end_idx_full:]

content = replace_scheduler_blog(content)


with open(APP_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 파일 교체 작업 완료")
