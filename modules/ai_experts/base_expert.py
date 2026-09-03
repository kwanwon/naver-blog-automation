# -*- coding: utf-8 -*-
from config.config import Config
import logging
import random
import os
import sys
import json
import urllib.request
import urllib.parse
import time
import traceback
import re
import ssl
import threading
from datetime import datetime, timedelta
from typing import Any, List
from utils.path_utils import get_config_dir, get_log_dir, get_api_key_path, get_app_settings_path
from utils.security_utils import deobfuscate, deobfuscate_dict_fields

# OpenAI 최신 SDK 대응
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_bundle_config_path():
    """macOS 앱 번들 내 config 경로를 반환합니다."""
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            macos_dir = os.path.dirname(exe_path)
            
            macos_config = os.path.join(macos_dir, 'config')
            if os.path.exists(macos_config):
                return macos_config
                
            resources_config = os.path.join(os.path.dirname(macos_dir), 'Resources', 'config')
            if os.path.exists(resources_config):
                return resources_config
            
            frameworks_config = os.path.join(os.path.dirname(macos_dir), 'Frameworks', 'config')
            if os.path.exists(frameworks_config):
                return frameworks_config

            frameworks_root = os.path.join(os.path.dirname(macos_dir), 'Frameworks')
            if os.path.exists(os.path.join(frameworks_root, 'ai_settings.txt')):
                return frameworks_root
                
            return macos_config
    except Exception:
        pass
    return None

class BaseAIExpert:
    # 🟢 기상청 단기예보 격자 좌표 매핑 (지역명 → nx, ny)
    KMA_GRID_MAP = {
        "서울": (60, 127), "서울특별시": (60, 127), "서울시": (60, 127),
        "강남구": (61, 126), "강동구": (62, 126), "강북구": (61, 128),
        "강서구": (58, 126), "관악구": (59, 125), "광진구": (62, 126),
        "구로구": (58, 125), "금천구": (59, 124), "노원구": (61, 129),
        "도봉구": (61, 129), "동대문구": (61, 127), "동작구": (59, 125),
        "마포구": (59, 127), "서대문구": (59, 127), "서초구": (61, 125),
        "성동구": (61, 127), "성북구": (61, 128), "송파구": (62, 126),
        "양천구": (58, 126), "영등포구": (58, 126), "용산구": (60, 126),
        "은평구": (59, 128), "종로구": (60, 127), "중구": (60, 127),
        "중랑구": (62, 128),
        "인천": (55, 124), "인천광역시": (55, 124), "인천시": (55, 124),
        "부평구": (55, 124), "인천 부평구": (55, 124), "부평": (55, 124),
        "남동구": (56, 124), "연수구": (56, 123), "미추홀구": (54, 124),
        "계양구": (56, 126), "서구": (55, 126), "중구 인천": (54, 125),
        "동구 인천": (54, 125), "강화군": (51, 130),
        "수원": (60, 121), "수원시": (60, 121), "성남": (63, 124), "성남시": (63, 124),
        "고양": (57, 128), "고양시": (57, 128), "용인": (64, 119), "용인시": (64, 119),
        "부천": (56, 125), "부천시": (56, 125), "안산": (58, 121), "안산시": (58, 121),
        "안양": (59, 123), "안양시": (59, 123), "남양주": (64, 128), "남양주시": (64, 128),
        "화성": (57, 119), "화성시": (57, 119), "평택": (62, 114), "평택시": (62, 114),
        "의정부": (61, 130), "의정부시": (61, 130), "시흥": (57, 123), "시흥시": (57, 123),
        "파주": (56, 131), "파주시": (56, 131), "김포": (55, 128), "김포시": (55, 128),
        "광명": (58, 125), "광명시": (58, 125), "광주시": (65, 123),
        "군포": (59, 122), "군포시": (59, 122), "하남": (64, 126), "하남시": (64, 126),
        "오산": (62, 118), "오산시": (62, 118), "이천": (68, 121), "이천시": (68, 121),
        "양평": (69, 125), "양평군": (69, 125),
        "부산": (98, 76), "부산광역시": (98, 76), "부산시": (98, 76),
        "대구": (89, 90), "대구광역시": (89, 90), "대구시": (89, 90),
        "광주": (58, 74), "광주광역시": (58, 74),
        "대전": (67, 100), "대전광역시": (67, 100), "대전시": (67, 100),
        "울산": (102, 84), "울산광역시": (102, 84), "울산시": (102, 84),
        "세종": (66, 103), "세종특별자치시": (66, 103), "세종시": (66, 103),
        "춘천": (73, 134), "춘천시": (73, 134),
        "원주": (76, 122), "원주시": (76, 122),
        "강릉": (92, 131), "강릉시": (92, 131),
        "속초": (87, 141), "속초시": (87, 141),
        "양양": (88, 138), "양양군": (88, 138),
        "청주": (69, 107), "청주시": (69, 107),
        "천안": (63, 110), "천안시": (63, 110),
        "충주": (76, 114), "충주시": (76, 114),
        "전주": (63, 89), "전주시": (63, 89),
        "익산": (60, 91), "익산시": (60, 91),
        "여수": (73, 66), "여수시": (73, 66),
        "순천": (70, 70), "순천시": (70, 70),
        "목포": (50, 67), "목포시": (50, 67),
        "포항": (102, 94), "포항시": (102, 94),
        "경주": (100, 91), "경주시": (100, 91),
        "김해": (95, 77), "김해시": (95, 77),
        "진주": (81, 75), "진주시": (81, 75),
        "창원": (89, 77), "창원시": (89, 77),
        "거제": (90, 69), "거제시": (90, 69),
        "제주": (52, 38), "제주시": (52, 38), "제주특별자치도": (52, 38),
        "서귀포": (52, 33), "서귀포시": (52, 33),
    }

    def __init__(self, use_dummy=False):
        self.use_dummy = use_dummy
        self.stop_event = threading.Event()  # 🛑 긴급 중지 플래그
        self.settings = self._load_settings()
        
        try:
            self._log_path = os.path.join(get_log_dir(), 'debug.log')
        except Exception:
            user_home = os.path.expanduser("~")
            self._log_path = os.path.join(user_home, ".blog_automation", 'logs', 'debug.log')
        
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        
        self._session_id = "debug-session"
        self._run_id = "run-model"
        self._hypothesis_rotation = "M1"
        self.instance_id = id(self)

        self.selected_models = []
        self.current_model_index = 0
        self.model = ""
        self.gemini_api_key = ""
        self.custom_prompt = {}
        
        # 앱 시작 시 최초 설정 1회 로드 (이후에는 각 generate 호출 시 _reload_all_settings로 갱신)
        self._reload_all_settings()
        
        # OpenAI 초기화는 처음 1회만 (API 키 변경 등은 재시작 필요)
        try:
            api_key = None
            if self.settings and 'api_key' in self.settings and self.settings['api_key']:
                api_key = self.settings['api_key']
                logger.info("GPT 설정 파일에서 API 키를 로드했습니다.")
            else:
                file_api_key = self._load_api_key_from_file()
                if file_api_key:
                    api_key = file_api_key
                    logger.info("api_key.json 파일에서 API 키를 로드했습니다.")
                else:
                    api_key = Config.GPT_API_KEY
                    logger.info("환경변수에서 API 키를 로드했습니다.")
            
            if api_key == 'your-api-key-here' or not api_key:
                logger.warning("API 키가 설정되지 않았습니다. 더미 모드로 전환합니다.")
                self.use_dummy = True
                self.api_key = ""
            else:
                self.api_key = api_key
                if OpenAI:
                    self.openai_client = OpenAI(api_key=api_key, timeout=60.0)
                    logger.info("OpenAI 클라이언트 초기화 성공 (new SDK, timeout=60s)")
                else:
                    import openai
                    openai.api_key = api_key
                    self.openai_client = openai
                    logger.info("OpenAI 클라이언트 초기화 성공 (legacy)")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 중 오류 발생: {str(e)}")
            self.use_dummy = True
        
        self._print_usage_status()

    def _reload_all_settings(self):
        """
        [핵심 안정화 로직]
        AI 콘텐츠 생성 전, 실시간으로 파일에서 최신 설정을 강제 재로드합니다.
        (쳇바퀴 증상 및 타 플랫폼 설정 오염 완벽 방지)
        """
        # 1. 설정 동기화
        self.settings = self._load_settings()
        
        # 2. 모델 목록 동기화
        original_models = self.settings.get('selected_models', [])
        self.selected_models = []
        for m in original_models:
            if m in Config.AI_MODELS:
                self.selected_models.append(m)
            else:
                inferred_provider = "gemini" if "gemini" in m.lower() else "openai"
                Config.AI_MODELS[m] = {
                    "provider": inferred_provider,
                    "name": m,
                    "manual_add": True
                }
                self.selected_models.append(m)
                
        if not self.selected_models:
            self.selected_models = [Config.GPT_MODEL]
            
        # 3. 인덱스 및 키 동기화
        if self.current_model_index >= len(self.selected_models):
            self.current_model_index = 0
        self.model = self.selected_models[self.current_model_index]
        
        self.gemini_api_key = self.settings.get('gemini_api_key', '') or Config.GEMINI_API_KEY
        self.custom_prompt = self._load_custom_prompt()

    def _dbg(self, location: str, message: str, data: dict | None = None, hypothesis_id: str | None = None):
        payload = {
            "sessionId": self._session_id,
            "runId": self._run_id,
            "hypothesisId": hypothesis_id or self._hypothesis_rotation,
            "location": location,
            "message": message,
            "data": {"instance_id": self.instance_id, **(data or {})},
            "timestamp": int(time.time() * 1000),
        }
        try:
            with open(self._log_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _print_usage_status(self):
        try:
            data = self._load_ai_usage()
            usage = data.get("usage", {})
            # 간소화된 표시
            logger.info(f"📊 [AI 사용량 체크] {usage}")
        except:
            pass

    def _load_settings(self):
        default_settings = {
            'persona': '친근하고 전문적인 블로그 작성자',
            'style': '쉽고 재미있게 설명하는 스타일',
            'tone': '친근하고 대화하듯이',
            'writing_style': {
                'intro': '흥미로운 질문이나 사례로 시작',
                'body': '구체적인 예시와 함께 단계별로 설명',
                'conclusion': '핵심 내용 요약과 독자 참여 유도'
            },
            'formatting': {
                'paragraph_length': '2-3문장',
                'use_emojis': True,
                'use_bullet_points': True
            }
        }
        fixed_review_instructions = """글 작성 후 반드시 다음 사항을 검토해주세요:
1. 오타와 맞춤법 오류가 없는지 확인
2. 문장 간 연결이 자연스러운지 확인
3. 논리적 흐름이 일관되는지 확인
4. 불필요한 반복이나 중복 표현이 없는지 확인
5. 전체적인 글의 통일성과 완성도 검토

"""
        # 1. ai_settings.txt 로드
        try:
            settings_path = os.path.join(get_config_dir(), 'ai_settings.txt')
            if not os.path.exists(settings_path):
                app_bundle_config = get_app_bundle_config_path()
                if app_bundle_config:
                    settings_path = os.path.join(app_bundle_config, 'ai_settings.txt')
                if not os.path.exists(settings_path):
                    settings_path = resource_path('config/ai_settings.txt')

            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    loaded_settings = deobfuscate_dict_fields(loaded_settings)
                    default_settings.update(loaded_settings)
                logger.info(f"GPT 설정 파일 로드 성공: {settings_path}")
        except Exception as e:
            logger.error(f"GPT 설정 파일 로드 중 오류 발생: {str(e)}")

        # 2. app_settings.json 로드 (API 키 포함)
        try:
            app_settings_path = get_app_settings_path()
            if os.path.exists(app_settings_path):
                with open(app_settings_path, 'r', encoding='utf-8') as f:
                    app_settings = json.load(f)
                    app_settings = deobfuscate_dict_fields(app_settings)
                    # 중요 API 키 및 사용자 설정값 업데이트
                    for k in ['brave_key', 'kma_api_key', 'api_key', 'gemini_api_key', 'weather_location', 'gym_name', 'dojang_name', 'gym_sport']:
                        if k in app_settings:
                            default_settings[k] = app_settings[k]
                    # 전체 설정을 안전하게 병합 (단, 기존 설정 유지하며 업데이트)
                    # default_settings.update(app_settings) 
                logger.info(f"앱 설정 파일 로드 성공: {app_settings_path}")
        except Exception as e:
            logger.error(f"앱 설정 파일 로드 중 오류 발생: {str(e)}")
            
        # 🆕 [기상청 API 키 등 사용자 설정 동기화 패치]
        try:
            user_settings = self._load_user_settings()
            if user_settings:
                for k in ['kma_api_key', 'brave_key', 'gemini_api_key', 'weather_location']:
                    if k in user_settings and user_settings[k]:
                        default_settings[k] = user_settings[k]
                if (not default_settings.get('weather_location') or default_settings.get('weather_location') == '서울') and user_settings.get('address'):
                    from utils.geo_utils import extract_weather_location
                    extracted = extract_weather_location(user_settings.get('address'))
                    if extracted:
                        default_settings['weather_location'] = extracted
        except Exception as e:
            logger.error(f"사용자 설정 파일 로드 중 오류 발생: {str(e)}")
        
        instr = default_settings.get('instructions', '')
        if fixed_review_instructions not in instr:
            default_settings['instructions'] = instr + fixed_review_instructions
        return default_settings

    def _read_rule_file(self, filename: str) -> str:
        try:
            path = os.path.join(get_config_dir(), filename)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return ""
        except Exception as e:
            logger.error(f"지침 파일 {filename} 로드 실패: {e}")
            return ""

    def _get_common_system_rules(self, platform='blog'):
        common_rules = self._read_rule_file('rules_common.txt')
        if not common_rules:
            common_rules = "[필수 준수 사항]\n1. 결론적으로, 잊지 마세요 등 AI 말투 절대 금지."
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        common_rules = common_rules.replace("{current_date}", current_date)
            
        platform_map = {
            'blog': 'rules_blog.txt',
            'band': 'rules_band.txt',
            'cafe': 'rules_cafe.txt',
            'drive_auto': 'rules_band_detection.txt',
            'idle': 'rules_social.txt'
        }
        
        if platform == 'manual_topic':
            platform_rules = self._read_rule_file('rules_band_detection.txt')
        else:
            platform_rules = self._read_rule_file(platform_map.get(platform, 'rules_blog.txt'))
        
        combined_rules = f"{common_rules}\n\n{platform_rules}"
        if platform == 'idle':
            combined_rules += "\n\n[소통 전용 지침]\n1. 상대방 본문 키워드 언급 필수.\n2. '안녕하세요', '반갑습니다', '반갑네요' 등 상투적인 첫인사 절대 금지. 바로 본문 내용에 대한 감상으로 시작하세요.\n3. 날씨 언급 절대 금지.\n4. 홍보 멘트 절대 금지."
        return combined_rules

    def _load_custom_prompt(self):
        custom_prompts = {}
        try:
            app_bundle_config = get_app_bundle_config_path()
            possible_paths = [
                os.path.join(get_config_dir(), 'custom_prompts.txt'),
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'custom_prompts.txt'),
            ]
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'custom_prompts.txt'))
            possible_paths.append(resource_path('config/custom_prompts.txt'))
            
            prompts_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    prompts_path = path
                    break
            
            if prompts_path:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        custom_prompts = json.loads(content)
                logger.info(f"커스텀 프롬프트 파일 로드 성공: {prompts_path}")
        except Exception as e:
            logger.error(f"커스텀 프롬프트 파일 로드 중 오류 발생: {str(e)}")
        return custom_prompts

    def _load_api_key_from_file(self):
        try:
            app_bundle_config = get_app_bundle_config_path()
            possible_paths = [
                os.path.join(get_config_dir(), 'api_key.json'),
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'api_key.json'),
            ]
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'api_key.json'))
            
            possible_paths.extend([
                os.path.join(os.path.abspath("."), 'config', 'api_key.json'),
                'config/api_key.json',
                resource_path('config/api_key.json')
            ])
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'api_key' in data and data['api_key']:
                            key = data['api_key']
                            if key.startswith("OBF:"):
                                key = deobfuscate(key[4:])
                            return key
        except Exception:
            pass
        return None

    def _load_user_settings(self):
        user_settings = {}
        try:
            # 🆕 1순위: 중앙 관리된 사용자 데이터 경로 (Windows / macOS 공통 표준)
            try:
                from utils.path_utils import get_user_settings_path
                central_path = get_user_settings_path()
                if central_path and os.path.exists(central_path):
                    with open(central_path, 'r', encoding='utf-8') as f:
                        user_settings = json.load(f)
                    logger.info(f"🔥 사용자 설정 파일 로드 성공 (중앙 경로): {central_path}")
                    return user_settings
            except Exception as ex_central:
                logger.debug(f"중앙 사용자 설정 경로 로드 시도 실패: {ex_central}")

            app_bundle_config = get_app_bundle_config_path()
            possible_paths = [
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'user_settings.txt'),
            ]
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'user_settings.txt'))
            
            possible_paths.extend([
                os.path.join(os.path.abspath("."), 'config', 'user_settings.txt'),
                'config/user_settings.txt',
                resource_path('config/user_settings.txt')
            ])
            
            settings_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    settings_path = abs_path
                    break
            
            if settings_path:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                logger.info(f"🔥 사용자 설정 파일 로드 성공: {settings_path}")
        except Exception as e:
            logger.error(f"🔥 사용자 설정 파일 로드 중 오류 발생: {str(e)}")
        return user_settings

    def _get_usage_path(self):
        try:
            return os.path.join(get_config_dir(), 'ai_usage.json')
        except:
            return os.path.join(self.settings.get('base_dir', '.'), 'config', 'ai_usage.json')

    def _load_ai_usage(self):
        path = self._get_usage_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {"date": datetime.now().strftime("%Y-%m-%d"), "usage": {}}

    def _save_ai_usage(self, data):
        try:
            path = self._get_usage_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _check_daily_limit(self, model_name):
        model_info = Config.AI_MODELS.get(model_name, {})
        limit = model_info.get('daily_limit')
        if limit is None:
            return True
        data = self._load_ai_usage()
        today = datetime.now().strftime("%Y-%m-%d")
        if data.get("date") != today:
            data = {"date": today, "usage": {}}
            self._save_ai_usage(data)
        used = data["usage"].get(model_name, 0)
        if used >= limit:
            logger.warning(f"⛔ {model_name} 일일 한도 초과 ({used}/{limit}) - 건너뜀")
            return False
        return True

    def _increment_usage(self, model_name):
        try:
            data = self._load_ai_usage()
            today = datetime.now().strftime("%Y-%m-%d")
            if data.get("date") != today:
                data = {"date": today, "usage": {}}
            data["usage"][model_name] = data["usage"].get(model_name, 0) + 1
            self._save_ai_usage(data)
            logger.info(f"📈 {model_name} 사용량 업데이트: {data['usage'][model_name]}회")
        except Exception as e:
            logger.error(f"사용량 업데이트 실패: {e}")

    def _apply_stability_filter(self, text: str, platform: str = 'blog', topic: str = '') -> str:
        import re  # 함수 로컬 스코프 전체에서 re 모듈을 안전하게 사용하기 위해 맨 위로 이동
        if not text:
            return text

        filtered_text = text
        # 0. Clean mechanical parent callouts and AI-style greetings
        if platform == 'blog':
            # [범용 배포 버전 호환 패치] 특정 도장/업종에 종속된 가짜 대회/심사/날씨 결합 강제 치환 필터를 비활성화하여 치명적인 문장 중복/반복 문제를 완벽히 소멸시킵니다.
            pass
        if platform == 'blog':
            parent_greetings = [
                r"안녕하세요[!\s,]*부모님", r"부모님[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*학부모님", r"학부모님[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*어머니", r"어머니[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*아버님", r"아버님[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*학부모님들", r"학부모님들[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*학부모\s*여러분", r"학부모\s*여러분[!\s,]*안녕하세요",
                r"안녕하세요[!\s,]*어머님", r"어머님[!\s,]*안녕하세요"
            ]
            for greet_pat in parent_greetings:
                filtered_text = re.sub(greet_pat, "안녕하세요!", filtered_text)
            
            # Remove direct single callouts (e.g. "부모님, 우리 아이들이" -> "우리 아이들이")
            filtered_text = re.sub(r"\b(?:부모님|학부모님|학부모님들|어머니|아버님)[,\s]+(우리\s+아이)", r"\1", filtered_text)

        # 1. 플랫폼별 금지 구문(Phrases) 정의
        filters = {
            'blog': [
                r"결론적으로", r"요약하자면", r"말씀드린 것처럼", r"마무리하겠습니다", r"마치겠습니다",
                r"오늘의 포스팅이 도움이 되셨길", r"다음 포스팅에서 만나요",
                r"예를\s*들어", r"예를\s*들면"
            ],
            'band': [
                r"결론적으로", r"요약하자면", r"말씀드린 것처럼", r"잊지 마세요", r"꼭 기억하세요",
                r"무엇보다도", r"다음으로", r"알려드릴게요", r"공유해볼게요", r"소개합니다", r"함께해요"
            ],
            'cafe': [
                r"결론적으로", r"요약하자면", r"광고", r"홍보", r"최고의", r"최선의"
            ]
        }

        # 2. 플랫폼별 제거할 추임새(Bad Words/Patterns) 정의
        bad_patterns = {
            'blog': [
                r"아이구[,\s]*", r"어머나[,\s]*", r"세상에[,\s]*", r"글쎄요[,\s]*", r"어머니[~,\s]*",
                r"외쳤어요", r"외쳤습니다", r"놀라운 변화", r"기적 같은", r"마법처럼"
            ],
            'band': [r"아이구[,\s]*", r"어머나[,\s]*", r"세상에[,\s]*", r"오늘도 즐거운 하루[,\s]*"],
            'cafe': [r"어머나[,\s]*", r"세상에[,\s]*"]
        }
        
        # 해당 플랫폼의 필터 적용
        current_filters = filters.get(platform, filters['blog'])
        for phrase in current_filters:
            filtered_text = re.sub(phrase + r"[,.\s]*", "", filtered_text).strip()
            
        # 해당 플랫폼의 추임새 제거
        current_bad_patterns = bad_patterns.get(platform, bad_patterns['blog'])
        for pat in current_bad_patterns:
            # 문장 시작 부분(도입부)에서 제거
            filtered_text = re.sub(r"^\s*" + pat, "", filtered_text, flags=re.MULTILINE).strip()
            # 본문 중간의 단어 제거
            word = pat.replace(r"[,\s]*", "").replace(r"[~,\s]*", "")
            filtered_text = filtered_text.replace(word, "").strip()

        # [추가] 블로그 전용: 말투 교정 (다. -> 요. / ㄴ다. -> 어요.)
        if platform == 'blog':
            filtered_text = self._correct_blog_tone(filtered_text)

        # 굵기 표시(**) 및 따옴표 제거
        filtered_text = filtered_text.replace('**', '').replace('"', '').replace("'", "")
        
        if platform == 'blog':
            # 블로그 본문 내의 해시태그 강제 제거 (태그 필드용이 아닌 본문 내 삽입 방지)
            if '#' in filtered_text:
                logger.info(f"블로그 본문 내 해시태그 감지 및 제거 수행")
                filtered_text = re.sub(r'#[\w가-힣]+', '', filtered_text).strip()
            filtered_text = re.sub(r'[ \t]+', ' ', filtered_text)
        return filtered_text

    def _correct_blog_tone(self, text: str) -> str:
        """딱딱한 '~다' 말투를 '~요' 말투로 강제 변환 (블로그 전용)"""
        if not text: return text
        
        # 교정 규칙 (정규식)
        corrections = [
            # 1. ~한다. -> ~해요. / ~합니다. -> ~해요.
            (r'([가-힣]+)한다\.', r'\1해요.'),
            (r'([가-힣]+)합니다\.', r'\1해요.'),
            (r'([가-힣]+)했습니다\.', r'\1했어요.'),
            (r'([가-힣]+)했었다\.', r'\1했었어요.'),
            
            # 2. ~이다. -> ~예요. / ~입니다. -> ~예요.
            (r'([가-힣]+)이다\.', r'\1예요.'),
            (r'([가-힣]+)입니다\.', r'\1예요.'),
            (r'([가-힣]+)이며\.', r'\1이구요.'),
            
            # 3. ~된다. -> ~돼요. / ~됩니다. -> ~돼요.
            (r'([가-힣]+)된다\.', r'\1돼요.'),
            (r'([가-힣]+)됩니다\.', r'\1돼요.'),
            (r'([가-힣]+)됐다\.', r'\1됐어요.'),
            (r'([가-힣]+)되었습니다\.', r'\1되었어요.'),
            
            # 4. ~있다. -> ~있어요. / ~있습니다. -> ~있어요.
            (r'([가-힣]+)있다\.', r'\1있어요.'),
            (r'([가-힣]+)있습니다\.', r'\1있어요.'),
            (r'([가-힣]+)있죠\.', r'\1있지요.'),
            
            # 5. ~한다면 -> ~한다면요
            (r'([가-힣]+)한다면\s', r'\1한다면요 '),
            
            # 6. 형용사 및 기타 종결어미
            (r'좋다\.', r'좋아요.'),
            (r'같다\.', r'같아요.'),
            (r'쉽다\.', r'쉬워요.'),
            (r'어렵다\.', r'어려워요.'),
            (r'많다\.', r'많아요.'),
            (r'적다\.', r'적어요.'),
            (r'크다\.', r'커요.'),
            (r'작다\.', r'작아요.'),
            
            # 7. '죠' 말투 강화 (수다스러운 느낌)
            (r'해요\.', r'해요. '), # 공백 추가로 리듬감
            (r'않다\.', r'않아요.'),
            (r'나온다\.', r'나오죠.'),
            (r'느껴진다\.', r'느껴지죠.'),
            (r'생각한다\.', r'생각해요.'),
            (r'권장한다\.', r'권장해요.'),
            (r'추천한다\.', r'추천드려요.'),
            (r'어렵다\.', r'어려워요.'),
            (r'높다\.', r'높아요.'),
            (r'적다\.', r'적어요.'),
            (r'많다\.', r'많아요.'),
            
            # 7. 기타 동사/형용사 어미
            (r'한다\.', r'해요.'),
            (r'이다\.', r'예요.'),
            (r'킨다\.', r'켜요.'),
            (r'준다\.', r'줘요.'),
            (r'본다\.', r'봐요.'),
            (r'온다\.', r'와요.'),
            (r'간다\.', r'가요.'),
            (r'먹는다\.', r'먹어요.'),
            (r'한다\.', r'해요.'),
        ]
        
        result = text
        for pattern, replacement in corrections:
            result = re.sub(pattern, replacement, result)
            
        return result

    def _generate_with_gemini(self, model_name: str, system_message: str, user_prompt: str, api_key: str = None) -> str:
        target_api_key = api_key if api_key else self.gemini_api_key
        if not target_api_key:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError("google-generativeai 패키지가 필요합니다. pip install google-generativeai") from e
        
        genai.configure(api_key=target_api_key)
        current_date_str = datetime.now().strftime("%Y년 %m월 %d일")
        date_instruction = f"\n\n[System: 시점 고정]\n오늘은 {current_date_str}입니다. 글의 시점은 반드시 오늘({current_date_str})을 기준으로 작성되어야 합니다."
        if system_message:
            system_message += date_instruction
        else:
            system_message = date_instruction
        model = genai.GenerativeModel(model_name)
        prompt_text = f"{system_message}\n\n{user_prompt}"
        response = model.generate_content(
            prompt_text,
            generation_config={"temperature": 0.7, "max_output_tokens": 8192, "top_p": 0.9},
            request_options={"timeout": 60}
        )
        content = self._extract_gemini_text(response)
        if not content:
            raise ValueError("Gemini 응답에서 본문을 추출할 수 없습니다.")
        return content.strip()

    def _extract_gemini_text(self, response: Any) -> str:
        if hasattr(response, "text") and response.text:
            return response.text
        if hasattr(response, "candidates"):
            parts: List[Any] = []
            for cand in getattr(response, "candidates", []):
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []):
                    txt = getattr(part, "text", None)
                    if txt:
                        parts.append(txt)
            if parts:
                return "\n".join(parts)
        return ""

    def _validate_content(self, content):
        if not content:
            return False
        content_length = len(content.strip())
        if content_length < 100:
            return False
        return True

    def _parse_content(self, content):
        """AI 생성 콘텐츠에서 제목, 본문, 태그를 분리하여 파싱 (유연한 마커 대응)"""
        try:
            tags_list = []
            
            # 1. 태그 섹션 분리 (다양한 마커 대응)
            tag_markers = ['[태그]', '태그:', '**태그:**', '### 태그', 'Tags:', 'Keywords:', '키워드:', '**키워드:**', '[키워드]', '[해시태그]', '해시태그:', '**해시태그:**', '### 해시태그']
            found_tag_marker = False
            
            # 변칙적인 숫자 포함 마커 (예: 키워드1:, 태그 1:) 탐색
            regex_marker = re.search(r'\n?\s*\*?\*?(?:태그|키워드)\s*\d*\s*:\*?\*?', content)
            if regex_marker:
                marker = regex_marker.group(0)
                tag_parts = content.split(marker, 1) # 첫 번째 마커에서만 분리
                content = tag_parts[0].strip()
                tags_text = tag_parts[1].strip()
                # 태그 텍스트 내부에 남아있는 '키워드2:', '키워드3:' 등 찌꺼기 제거
                tags_text = re.sub(r'\*?\*?(?:태그|키워드)\s*\d*\s*:\*?\*?', '', tags_text)
                tags_list = [t.strip() for t in re.split(r'[#,\s/]+', tags_text) if len(t.strip()) > 1]
                found_tag_marker = True
            else:
                for marker in tag_markers:
                    if marker in content:
                        tag_parts = content.split(marker)
                        # 마커 이전은 본문, 이후는 태그로 간주
                        content = tag_parts[0].strip()
                        tags_text = tag_parts[1].strip()
                        # 쉼표, 공백, 줄바꿈, 해시태그 등으로 태그 분리 (의미없는 1글자 기호 제거)
                        tags_list = [t.strip() for t in re.split(r'[#,\s/]+', tags_text) if len(t.strip()) > 1]
                        found_tag_marker = True
                        break
            
            # 마커가 없는데 본문 하단에 #해시태그나 나열된 단어가 있는 경우 추출 시도
            if not found_tag_marker:
                # 1) 해시태그 패턴 (#태그1 #태그2)
                body_tags = re.findall(r'#([\w가-힣]+)', content)
                if body_tags:
                    tags_list = [t.strip() for t in body_tags if len(t.strip()) > 1]
                    # 본문에서 해당 태그들 제거
                    content = re.sub(r'#[\w가-힣]+', '', content).strip()
                else:
                    # 2) 쉼표 나열 패턴 (단어1, 단어2, 단어3...) - 본문 마지막 줄 확인
                    lines = content.strip().split('\n')
                    if lines and ',' in lines[-1] and len(lines[-1].split(',')) > 5:
                        tags_list = [t.strip() for t in lines[-1].split(',') if len(t.strip()) > 1]
                        content = '\n'.join(lines[:-1]).strip()

            # 2. 본문 섹션 분리
            body_markers = ['[본문]', '본문:', '**본문:**', '### 본문', 'Content:', 'Body:']
            parts = []
            for marker in body_markers:
                if marker in content:
                    parts = content.split(marker)
                    break
            
            if len(parts) < 2:
                # 마커가 없는 경우 줄 단위로 분리
                lines = content.split('\n')
                title = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
            else:
                # 제목 섹션 처리
                title = parts[0].strip()
                body = parts[1].strip()
            
            # 🧹 [지능형 제목 마커 세정 엔진]
            # 앞부분에 오는 [제목], **제목**, 제목:, ### 제목, Title:, # 제목, ## 🚨 등 모든 형식의 마커 및 장식 기호 완벽 제거
            title = re.sub(
                r'^(?:\[\s*제목\s*\]|\*+\s*제목\s*\*+[:\s]*|제목[:\s]*|#+\s*제목[:\s]*|Title[:\s]*|#+\s*)\s*', 
                '', 
                title
            ).strip()
            # 제목에 남은 볼드 마크다운(**) 기호 깔끔하게 트림
            title = title.replace('**', '').replace('__', '').strip()
            
            # 3. 본문 내 잔여 마커 및 태그 찌꺼기 제거 (안전장치)
            for m in ['[본문]', '본문:', '**본문:**', '[태그]', '태그:', '**태그:**', '### 본문', '### 태그']:
                body = body.replace(m, '').strip()
            
            # 본문 하단에 남아있는 해시태그 제거 (시스템 태그와 중복 방지)
            body = re.sub(r'(\n\s*#[\w가-힣]+)+$', '', body).strip()
            body = re.sub(r'#[\w가-힣]{2,}', '', body).strip()
            
            # 🧹 [쉼표 찌꺼기 세정 엔진 - Comma Sweeper]
            # 해시태그가 지워지고 남은 끝단의 지저분한 연속 쉼표(',,,,,') 및 찌꺼기 단어 파편 완벽 소멸
            body = re.sub(r'[,.\s\xa0]{2,}(?:교육|태그|키워드|해시|발차기|대련|호신술)?\s*$', '', body).strip()
            # 본문 맨 마지막에 대롱대롱 매달려 있는 쉼표나 마침표 중복 잔여물 트림
            body = re.sub(r'[,]+$', '', body).strip()
            # 본문 중간의 깨진 쉼표 뭉치 정돈
            body = re.sub(r'[,]{2,}', ', ', body).strip()
            
            return title, body, tags_list
        except Exception as e:
            logger.error(f"콘텐츠 파싱 중 오류 발생: {str(e)}")
            lines = content.strip().split("\n")
            title = lines[0].strip()
            # 제목 라벨 제거 (폴백)
            for tm in ['[제목]', '제목:', '**제목:**', 'Title:']:
                title = title.replace(tm, '').strip()
            body = "\n".join(lines[1:]).strip()
            return title, body, []

    def _get_dummy_content(self, topic):
        exercise_content = "[도입] 건강한 삶을 위해 운동을 시작하세요.\n\n[장점] 체력 향상과 활기찬 일상.\n\n[결론] 운동은 삶의 질을 높입니다."
        default_content = f"[도입] 안녕하세요! 오늘은 {topic}에 대해 이야기해봅시다.\n\n[본문] 이것은 테스트용 더미 콘텐츠입니다."
        dummy_contents = {
            "운동 효과의 장점": {"title": "꾸준한 운동의 놀라운 효과!", "content": exercise_content},
            "default": {"title": f"[메모] {topic}에 대한 전문가의 이야기", "content": default_content}
        }
        dummy_content = dummy_contents.get(topic, dummy_contents["default"])
        user_settings = self._load_user_settings()
        first_sentence = user_settings.get('first_sentence', '').strip()
        if first_sentence:
            dummy_content["content"] = f"{first_sentence}\n\n{dummy_content['content']}"
        return dummy_content

    def _format_content_for_mobile(self, content):
        formatted_lines = []
        for paragraph in content.split('\n'):
            if not paragraph.strip():
                formatted_lines.append('')
                continue
            current_line = ''
            for word in paragraph.split():
                if not current_line:
                    current_line = word
                else:
                    max_line_length = random.randint(5, 25)
                    if len(current_line) >= max_line_length and any(current_line.endswith(p) for p in ['.', ',', '!', '?', ':', ';']):
                        formatted_lines.append(current_line)
                        current_line = word
                    elif len(current_line + ' ' + word) > 25:
                        formatted_lines.append(current_line)
                        current_line = word
                    else:
                        current_line += ' ' + word
            if current_line:
                formatted_lines.append(current_line)
            formatted_lines.append('')
        return '\n'.join(formatted_lines)

    def _enhance_formatting(self, content):
        emoji_map = {
            '도입': '[도입]', '소개': '[메모]', '장점': '[장점]', '특징': '[확인]',
            '방법': '📌', '팁': '[팁]', '주의': '⚠️', '결론': '[결론]',
            '요약': '📋', '제안': '[제안]'
        }
        formatted_content = content
        for key, emoji in emoji_map.items():
            formatted_content = formatted_content.replace(f"- {key}", f"{emoji} {key}")
        paragraphs = formatted_content.split('\n\n')
        formatted_paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return '\n\n'.join(formatted_paragraphs)

    def _apply_readability_filter(self, text: str) -> str:
        if not text: return text
        
        # 0. 기형적인 '첫\n번째', '두\n번째' 등 순차식 표현의 줄바꿈 복원 및 공백 복구 (단어 잘림 방어)
        clean_patterns = [
            (r'첫\s*\n+\s*번째', '첫 번째'),
            (r'두\s*\n+\s*번째', '두 번째'),
            (r'세\s*\n+\s*번째', '세 번째'),
            (r'네\s*\n+\s*번째', '네 번째'),
            (r'다섯\s*\n+\s*번째', '다섯 번째'),
            (r'첫\s*\n+\s*째', '첫째'),
            (r'둘\s*\n+\s*째', '둘째'),
            (r'셋\s*\n+\s*째', '셋째'),
            (r'넷\s*\n+\s*째', '넷째'),
            (r'다섯\s*\n+\s*째', '다섯째')
        ]
        for pat, rep in clean_patterns:
            text = re.sub(pat, rep, text)
            
        # 1. 명언/인용구 구조 분석 기반 병합 (강화형)
        lines = text.split('\n')
        processed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                processed_lines.append("")
                i += 1
                continue
                
            if (line == '-' or line.startswith('-')) and len(processed_lines) > 0:
                prev_idx = len(processed_lines) - 1
                while prev_idx >= 0 and not processed_lines[prev_idx].strip():
                    prev_idx -= 1
                
                if prev_idx >= 0:
                    prev_content = processed_lines[prev_idx].strip().strip("'")
                    author_content = line.strip('-').strip()
                    if not author_content:
                        next_i = i + 1
                        while next_i < len(lines) and not lines[next_i].strip():
                            next_i += 1
                        if next_i < len(lines):
                            author_content = lines[next_i].strip()
                            i = next_i
                    
                    processed_lines[prev_idx] = f"'{prev_content} - {author_content}'"
                    i += 1
                    continue
            
            processed_lines.append(line)
            i += 1
        
        text = '\n'.join(processed_lines)
        
        # 2. 모바일 최적화: 1~2문장 단위로 문단 묶기 (가독성 극대화)
        paragraphs = text.split('\n')
        new_paragraphs = []
        
        for p in paragraphs:
            p = p.strip()
            if not p: continue
            
            # 명언이나 슬로건(특수기호 포함)은 건드리지 않음
            if p.startswith("'") or p.startswith("🥋") or p.startswith("✅"):
                new_paragraphs.append(p)
                continue
                
            sentences = re.split(r'(?<=[.!?])\s+', p)
            
            # 2~3문장씩 묶어서 문단 구성 (지능형 가독성 극대화)
            current_batch = []
            for s in sentences:
                s_strip = s.strip()
                if s_strip:
                    # '첫 번째', '첫째', '두 번째', '둘째' 등의 나열식 문맥으로 시작하는 경우 
                    # 기존 배치를 먼저 발행하여 완벽하게 문단을 격리 및 줄바꿈 두 번 보장
                    is_sequential_start = any(s_strip.startswith(prefix) for prefix in [
                        "첫 번째", "첫째", "두 번째", "둘째", "세 번째", "셋째", "네 번째", "넷째", "다섯 번째", "다섯째",
                        "하나.", "둘.", "셋.", "넷.", "다섯.", "첫번째", "두번째", "세번째", "네번째", "다섯번째",
                        "첫 째", "둘 째", "셋 째", "넷 째", "다섯 째"
                    ])
                    
                    if is_sequential_start and current_batch:
                        new_paragraphs.append(' '.join(current_batch))
                        current_batch = []
                        
                    current_batch.append(s_strip)
                    # 2~3문장 단위로 구성하되, 2문장의 누적 글자 수가 80자 이상으로 길면 즉시 문단 분리
                    if len(current_batch) >= 3 or (len(current_batch) >= 2 and sum(len(sent) for sent in current_batch) >= 80):
                        new_paragraphs.append(' '.join(current_batch))
                        current_batch = []
            
            if current_batch:
                new_paragraphs.append(' '.join(current_batch))
        
        # 3. 최종 결과 조인 및 중복 여백 정리 (1문단 단위로 확실하게 엔터 2번 분리)
        final_text = '\n\n'.join(new_paragraphs).strip()
        
        # Ensure two line breaks (one blank line) before '[홈 케어 팁]' or '[홈케어]'
        final_text = re.sub(r'([^\n])\s*(\[(?:홈\s*케어(?:\s*팁)?|홈케어)\])', r'\1\n\n\2', final_text)
        
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        
        return final_text

    def _get_kma_weather(self, location="서울", delta_days=0, target_hour=None):
        """기상청 API를 사용하여 상세 날씨 정보 추출 (예약 시각 맞춤형)"""
        api_key = self.settings.get('kma_api_key', '')
        if not api_key: return None
        
        # 단기예보 범위를 초과하는 예약 일자(오늘+3일 이상)인 경우 날씨 조회를 생략합니다.
        if delta_days >= 3:
            logger.info(f"기상청 예보 범위를 초과하는 예약 일자(오늘+{delta_days}일)이므로 날씨 조회를 생략합니다.")
            return None
        
        # 좌표 매핑
        nx, ny = None, None
        for key, coords in self.KMA_GRID_MAP.items():
            if key in location or location in key:
                nx, ny = coords
                break
        if nx is None: return None

        try:
            now = datetime.now()
            # 타겟 시간 설정 (입력된 target_hour가 있으면 사용, 없으면 현재 시각)
            if target_hour is not None:
                t_hour = int(target_hour)
            else:
                t_hour = now.hour
            
            # 기상청 단기예보는 02시부터 3시간 간격 (02, 05, 08, 11, 14, 17, 20, 23)
            base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
            
            # 발표 시각 결정
            valid_base_time = "2300"
            base_date = now.strftime("%Y%m%d")
            
            real_now_time = int(now.strftime("%H%M"))
            for bt in reversed(base_times):
                if real_now_time >= int(bt) + 10: 
                    valid_base_time = bt
                    break
            else: 
                base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
                valid_base_time = "2300"

            api_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
            params = {
                "serviceKey": api_key,
                "numOfRows": 1000,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": valid_base_time,
                "nx": nx,
                "ny": ny
            }
            
            req_url = f"{api_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if not items: return None

            target_fcst_date = (now + timedelta(days=delta_days)).strftime("%Y%m%d")
            target_fcst_time = f"{t_hour:02d}00"
            
            tmp, sky, pty, wsd = None, None, None, None
            # 1. 정확한 시간대 찾기 시도
            for item in items:
                if item.get('fcstDate') == target_fcst_date and item.get('fcstTime') == target_fcst_time:
                    cat = item.get('category')
                    val = item.get('fcstValue')
                    if cat == 'TMP': tmp = val
                    elif cat == 'SKY': sky = val
                    elif cat == 'PTY': pty = val
                    elif cat == 'WSD': wsd = val
            
            # 2. 정확한 시간대가 없으면 가장 가까운 시간대 찾기
            if not tmp:
                for item in items:
                    if item.get('fcstDate') == target_fcst_date:
                        cat = item.get('category')
                        val = item.get('fcstValue')
                        if cat == 'TMP' and not tmp: tmp = val
                        if cat == 'SKY' and not sky: sky = val
                        if cat == 'PTY' and not pty: pty = val
                        if cat == 'WSD' and not wsd: wsd = val
                        if tmp and sky and pty and wsd: break
            
            if not tmp: return None
            
            sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
            pty_map = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
            
            sky_str = sky_map.get(sky, "정보없음")
            pty_str = pty_map.get(pty, "")
            weather_desc = f"{pty_str}({sky_str})" if pty_str else sky_str
            
            # 풍속 정보 해석 (m/s)
            wind_str = ""
            if wsd:
                try:
                    w_val = float(wsd)
                    if w_val >= 9: wind_str = f", 바람 매우 강함({wsd}m/s)"
                    elif w_val >= 4: wind_str = f", 바람 강함({wsd}m/s)"
                    elif w_val >= 1.5: wind_str = f", 바람 약간({wsd}m/s)"
                except: pass
            
            # 당일 예약 시간대 이후(혹은 당일 전체) 비 예보 감지 (지능형 강수 사전 경고 시스템)
            rain_hours = []
            for item in items:
                if item.get('fcstDate') == target_fcst_date:
                    cat = item.get('category')
                    val = item.get('fcstValue')
                    time_str = item.get('fcstTime', '0000')
                    try:
                        h_val = int(time_str[:2])
                    except:
                        continue
                    
                    # 예약 시간(t_hour) 또는 그 이후의 시간대에 강수/소나기/높은 강수확률 확인
                    if h_val >= t_hour:
                        if cat == 'PTY' and val in ['1', '2', '4']:
                            rain_hours.append(h_val)
                        elif cat == 'POP':
                            try:
                                pop_val = int(val)
                                if pop_val >= 60:  # 강수확률 60% 이상
                                    rain_hours.append(h_val)
                            except:
                                pass
            
            rain_alert = ""
            if rain_hours:
                first_rain_hour = min(rain_hours)
                if first_rain_hour == t_hour:
                    rain_alert = "현재 비나 소나기가 내리거나 시작될 예보가 있습니다."
                else:
                    rain_alert = f"오늘 {first_rain_hour}시경부터 비나 소나기 소식이 예보되어 있습니다."
            
            # 미세먼지 정보 하이브리드 결합 (KMA 날씨 정보에 미세먼지 추가 보강)
            dust_info = ""
            try:
                # 네이버 미세먼지 가볍게 스크래핑
                refined_loc = self._refine_location(location)
                encoded = urllib.parse.quote(f"{refined_loc} 날씨")
                n_url = f"https://search.naver.com/search.naver?query={encoded}"
                n_req = urllib.request.Request(n_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(n_req, timeout=3) as n_resp:
                    n_html = n_resp.read().decode('utf-8', errors='replace')
                dust_patterns = [
                    r'미세먼지</span>\s*<span class="txt">(.*?)</span>',
                    r'미세먼지.*?<span class="txt">(.*?)</span>',
                    r'<dt class="term">미세먼지</dt>\s*<dd class="desc">(.*?)</dd>'
                ]
                for p in dust_patterns:
                    dust_match = re.search(p, n_html, re.DOTALL)
                    if dust_match:
                        val = dust_match.group(1).strip()
                        if val and len(val) < 10:
                            dust_info = f", 미세먼지: {val}"
                            break
            except Exception as dust_err:
                logger.warning(f"KMA 하이브리드 미세먼지 조회 실패: {dust_err}")

            advice = self._get_weather_advice(tmp, wsd, rain_alert=rain_alert, weather_desc=weather_desc)
            label_map = {0: "현재", 1: "내일", 2: "모레"}
            day_label = label_map.get(delta_days, f"{delta_days}일 뒤")
            label = f"{day_label} {t_hour}시 예보" if delta_days > 0 else f"현재({t_hour}시)"
            
            # 기온, 하늘상태, 바람, 미세먼지 전체가 완벽하게 결합된 포맷 반환
            return f"[{location} {label}] 기온: {tmp}도, 하늘: {weather_desc}{wind_str}{dust_info}. ({advice})"
        except Exception as e:
            logger.error(f"기상청 API 연동 실패: {e}")
            return None
 
    def _refine_location(self, location):
        """주소를 읍/면/동/구/시/군 단위로 단순화하여 날씨 조회 성공률 극대화"""
        if not location:
            return "서울"
        location = re.sub(r'\(.*?\)', '', location).strip()
        parts = location.split()
        for p in reversed(parts):
            p_clean = p.strip()
            if p_clean.endswith(('읍', '면', '동', '구', '시', '군')):
                return p_clean
        return parts[-1] if parts else "서울"

    def _get_weather_advice(self, temp_val, wsd_val=None, rain_alert="", weather_desc=""):
        """온도에 따른 심플하고 다정한 체감 기상 묘사"""
        try:
            temp = float(temp_val)
            if temp < 5:
                return "매우 쌀쌀하고 추운 날씨"
            elif temp < 12:
                return "쌀쌀함이 느껴지는 날씨"
            elif temp < 18:
                return "선선한 바람이 부는 날씨"
            elif temp < 25:
                return "포근하고 활동하기 좋은 날씨"
            else:
                return "조금 더운 기운이 느껴지는 날씨"
        except:
            return "편안하고 기분 좋은 날씨"

    def _get_time_of_day_name(self, hour):
        """시간대에 따른 자연스러운 한국어 명칭 반환"""
        if hour < 6: return "새벽"
        elif hour < 11: return "오전"
        elif hour < 14: return "점심 시간"
        elif hour < 17: return "오후"
        elif hour < 21: return "저녁"
        else: return "밤"

    def _get_naver_weather(self, location, delta_days=0):
        """네이버 검색을 통해 실시간/예보 기상 정보 파싱 추출"""
        
        refined = self._refine_location(location)
        query = f"{refined} 날씨"
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?query={encoded_query}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='replace')
            
            # 날씨 전용 블록 추출
            weather_block = html
            if delta_days == 0:
                m_block = re.search(r'class="blind">오늘의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)
            elif delta_days == 1:
                m_block = re.search(r'class="blind">내일의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)
            elif delta_days == 2:
                m_block = re.search(r'class="blind">모레의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                if m_block:
                    weather_block = m_block.group(0)

            # 온도 추출
            temp = "?"
            if delta_days in [1, 2]:
                am_temp = None
                pm_temp = None
                m_am = re.search(r'오전.*?class="temperature_text">.*?예측 온도</span>\s*(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                if m_am:
                    am_temp = m_am.group(1).strip()
                else:
                    m_am_alt = re.search(r'오전.*?class="temperature_text">.*?(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if m_am_alt:
                        am_temp = m_am_alt.group(1).strip()
                        
                m_pm = re.search(r'오후.*?class="temperature_text">.*?예측 온도</span>\s*(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                if m_pm:
                    pm_temp = m_pm.group(1).strip()
                else:
                    m_pm_alt = re.search(r'오후.*?class="temperature_text">.*?(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if m_pm_alt:
                        pm_temp = m_pm_alt.group(1).strip()
                
                if am_temp:
                    temp = am_temp
                elif pm_temp:
                    temp = pm_temp
            else:
                patterns = [
                    r'class="temperature_text">.*?현재 온도</span>\s*(-?\d+(?:\.\d+)?)(?:\xb0|<span)',
                    r'class="temperature_text">.*?(-?\d+(?:\.\d+)?)(?:\xb0|<span)',
                    r'class="todaytemp">(-?\d+(?:\.\d+)?)',
                    r'class="current">(-?\d+(?:\.\d+)?)(?:\xb0|<span)'
                ]
                for p in patterns:
                    m = re.search(p, weather_block, re.DOTALL)
                    if m:
                        temp = m.group(1).strip()
                        break

            # 미세먼지 정보 추출
            dust_info = ""
            if delta_days == 0:
                dust_patterns = [
                    r'미세먼지</span>\s*<span class="txt">(.*?)</span>',
                    r'미세먼지.*?<span class="txt">(.*?)</span>',
                    r'<dt class="term">미세먼지</dt>\s*<dd class="desc">(.*?)</dd>'
                ]
                for p in dust_patterns:
                    dust_match = re.search(p, html, re.DOTALL)
                    if dust_match:
                        val = dust_match.group(1).strip()
                        if val and len(val) < 10:
                            dust_info = f", 미세먼지: {val}"
                            break

            # 날씨 상태 추출
            weather_desc = ""
            desc_patterns = [
                r'class="weather before_slash">(.*?)</span>',
                r'class="weather">(.*?)</span>',
                r'<p class="summary">.*?<span class="weather[^>]*">(.*?)</span>'
            ]
            for p in desc_patterns:
                desc_match = re.search(p, weather_block, re.DOTALL)
                if desc_match:
                    val = desc_match.group(1).strip()
                    if val and len(val) < 15:
                        weather_desc = val
                        break

            # 바람 정보 추출 (네이버 날씨 스크래핑 전용 풍속 정보 보강)
            wind_str = ""
            wind_match = re.search(r'풍속\s*<\/span>\s*<span class="txt">([^<]+)<\/span>', html, re.IGNORECASE)
            if not wind_match:
                wind_match = re.search(r'바람\s*<\/span>\s*<span class="txt">([^<]+)<\/span>', html, re.IGNORECASE)
            if not wind_match:
                wind_match = re.search(r'풍향/풍속.*?<span class="txt">([^<]+)</span>', html, re.DOTALL)
            if wind_match:
                w_val = wind_match.group(1).strip()
                if w_val:
                    wind_str = f", 바람: {w_val}"

            if temp == "?": return None
            
            advice = self._get_weather_advice(temp, weather_desc=weather_desc)
            label_map = {0: "현재", 1: "내일 예보", 2: "모레 예보"}
            time_label = label_map.get(delta_days, "예보")
            
            # 기온, 하늘, 바람, 미세먼지 전체가 완벽하게 포함되도록 수집 포맷 개선
            sky_info = f", 하늘: {weather_desc}" if weather_desc else ""
            return f"[{refined} {time_label}] 기온: {temp}도{sky_info}{wind_str}{dust_info}. ({advice})"
        except Exception as e:
            print(f"네이버 날씨 스크래핑 실패: {e}")
            return None

    def _build_weather_hook_message(self, location, is_forecast, platform='blog', target_time=None, delta_days=0):
        """AI에게 전달할 날씨 훅 메시지 생성 (특정 시간 날씨 인사 생략 락 & 1~2문장 극단적 초간단 팩트 락)"""
        from datetime import datetime, timedelta
        import logging
        from modules.weather_cache_manager import WeatherCacheManager
        logger = logging.getLogger("BaseExpert")
        
        now = datetime.now()
        target_hour = now.hour
        
        # 1. 예약 시간이 유효하게 있는지 파악
        has_reservation = False
        if target_time:
            try:
                if isinstance(target_time, str):
                    cleaned_str = str(target_time).strip()
                    if len(cleaned_str) > 10 and ':' in cleaned_str:
                        import re
                        h_match = re.search(r'\s(\d{1,2}):', cleaned_str)
                        if h_match:
                            target_hour = int(h_match.group(1))
                            has_reservation = True
                    else:
                        target_hour = int(cleaned_str.split(':')[0])
                        has_reservation = True
                elif hasattr(target_time, 'hour'):
                    target_hour = target_time.hour
                    has_reservation = True
            except Exception as e:
                logger.error(f"_build_weather_hook_message target_time ({target_time}) 파싱 중 오류: {e}")
                target_hour = now.hour
        
        # 2. [미래 예약 발행 조건 판별]
        # 예약 시간과 현재 시간의 차이가 크거나 다음날 이후인 경우 (실시간과 3시간 이상 차이 나는 미래 시점)
        # 이 경우에는 네이버 실시간 날씨 검색결과(현재 시각 기온)를 대입하면 모순이 일어나므로,
        # 기상청 예보 API가 실패할 경우 네이버 날씨 스크래핑으로 Fallback하지 않고 바로 "날씨 없이 시작"으로 우회합니다.
        is_future_reservation = False
        if has_reservation:
            target_dt = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if delta_days > 0 or (target_dt - now).total_seconds() >= 3 * 3600:
                is_future_reservation = True
        
        # 3. [날씨 수집 정책]
        # - 예약 시간 유무와 관계없이, 모든 포스팅에서 날씨 수집을 시도합니다.
        # - 단, 미래 예약(3시간 이상 차이)의 경우 기상청 API 실패 시 네이버 실시간 기온으로
        #   Fallback하지 않습니다. (현재 시각 기온이 예약 시각 기온과 다르므로 가짜 수치 날조 위험)
        should_skip_weather = False  # 모든 시간대 날씨 수집 허용

        # 4. 주소 단순화 전처리 적용
        refined_location = self._refine_location(location)
        
        # 5. 날씨 수집 시도 (모든 시간대 공통)
        weather_info = None
        
        # (1) [우선순위 1] 백그라운드 로컬 위젯 캐시 조회 (0.00초 극속도 복원)
        try:
            weather_info = WeatherCacheManager.get_cached_weather(refined_location, delta_days=delta_days, target_hour=target_hour)
            if weather_info:
                # 🛑 [핵심 버그 수정] 예약(is_forecast=True) 포스팅의 경우 데이터에 '내일/모레/예보'가 있으면
                # AI가 무조건 '오늘'로 작성하라는 블로그 지침과 충돌하여 오류(날씨 생략 또는 오작동)를 일으키므로 '현재/오늘'로 치환
                if is_forecast:
                    weather_info = weather_info.replace('내일', '오늘').replace('모레', '오늘').replace('예보', '현재')
                logger.info(f"🎉 로컬 날씨 캐시 히트 성공! 대기시간 0.00초: {weather_info}")
        except Exception as cache_err:
            logger.error(f"Weather cache lookup error (skipped): {cache_err}")
            
        # (2) [우선순위 2] 캐시 미스 시 기상청 API 직접 호출 (최대 3회 재시도)
        if not weather_info:
            logger.info(f"💾 캐시 미스 또는 만료: {refined_location}에 대해 기상청 API 호출을 시도합니다.")
            for attempt in range(1, 4):
                try:
                    weather_info = self._get_kma_weather(refined_location, delta_days=delta_days, target_hour=target_hour)
                    if weather_info:
                        break
                except Exception as kma_err:
                    logger.warning(f"KMA Weather attempt {attempt} failed: {kma_err}")
                if attempt < 3:
                    import time
                    time.sleep(0.5)
        
        # (3) [우선순위 3] 기상청 API 실패 시 → 네이버 실시간/예보 스크래핑으로 Fallback 시도 (미래 예약이 아닐 때만 허용)
        if not weather_info:
            if is_future_reservation:
                logger.warning("⚠️ 미래 예약 포스팅입니다. 기상청 API 실패로 인해 실시간 기온과 불일치하는 네이버 날씨 Fallback 조회를 차단하고 '날씨 없이 시작' 모드로 우회합니다.")
            else:
                logger.info("💾 기상청 API 실패: 네이버 날씨 스크래핑 Fallback 조회를 시도합니다.")
                for attempt in range(1, 4):
                    try:
                        weather_info = self._get_naver_weather(refined_location, delta_days=delta_days)
                        if weather_info:
                            break
                    except Exception as scrap_err:
                        logger.error(f"Naver Weather Scraping attempt {attempt} failed: {scrap_err}")
                    if attempt < 3:
                        import time
                        time.sleep(0.5)

        # 6. 날씨 수집 정보가 없을 때: "날씨 없이 시작" 지침 주입
        # (날씨 API/스크래핑 전부 실패 시에만 해당 — 시간대 정책 생략 아님)
        if not weather_info:
            return """
[System: 날씨 정보 미제공 - 날씨 인사 생략 지침 ⭐⭐⭐⭐⭐]
⚠️ 중요: 기상청 API 및 날씨 수집이 모두 실패하여 정확한 날씨 정보를 제공할 수 없습니다.
1. **[도입부 날씨 언급 절대 금지]**: 첫 도입부에서 기온(도수), 미세먼지, 하늘 상태(구름, 맑음, 비 등), 혹은 날씨나 안부와 관련된 어떠한 표현(예: "비가 오네요", "쌀쌀하네요", "선선하네요", "따뜻하네요" 등)도 **100% 절대 쓰지 마십시오**.
   (정확한 데이터 없이 임의의 기온/날씨를 지어내는 행위는 100% 금지입니다.)
2. **[고정된 단 한 문장의 깔끔한 인사말]**: 포스팅의 맨 첫 도입부는 반드시 오직 다음의 정확히 지정된 다정한 한 문장으로만 시작하고 마침표를 찍으세요.
   👉 "안녕하세요! 오늘도 기분 좋은 하루 보내고 계신가요?"
3. **[첫 문단 단독 구성 및 전환]**: 위의 한 문장으로 첫 도입부 문단을 깔끔하게 마치고, 즉시 줄바꿈(엔터)을 하여 새로운 문단에서 오늘의 본문 지식/정보 콘텐츠를 신선하게 열어가십시오.
4. **[억지 전개 완전 금지]**: 본문 활동 묘사나 억지스러운 건강 훈화 멘트 등을 도입부와 엮어서 작성하는 어색한 결합 문장을 첫머리에 **100% 쓰지 마십시오**.
"""


        # 7. 날씨가 필요한 시간대이고 기상 수집에 완벽히 성공했을 때: "초간단 날씨 인사말" 지침 주입
        target_date_str = (now + timedelta(days=delta_days)).strftime("%m월 %d일")
        time_of_day = self._get_time_of_day_name(target_hour)
        
        return f"""
[System: 독자 시점의 당일({target_date_str}) 날씨 및 시간 정보]
- 지역명(위치): {refined_location}
- 시간대: {time_of_day}
- 상세 데이터: {weather_info}
 
⚠️ [초간단 날씨 인사말 강제 가이드라인 - 매우 엄격 ⭐⭐⭐⭐⭐]
🚨 [포스팅 출력 레이아웃 강제 규칙 - 매우 엄격 ⭐⭐⭐⭐⭐]
- 당신이 출력하는 전체 포스팅 텍스트는 반드시 다음의 **[제목]**과 **[본문]** 마커 형식을 100% 준수해야 하며, 절대로 다른 곳에 글이나 텍스트를 배치해서는 안 됩니다:
  
  [제목]
  오늘의 주제와 관련된 클릭 유발형 제목 1줄 작성 (⚠️ 날씨나 안부는 절대로 제목에 적지 마십시오. 100% 원천 전면 금지)
  
  [본문]
  오늘 {refined_location}은 기온이 [상세 데이터 속 기온]도에 미세먼지는 [미세먼지 상태], 하늘이 [날씨 상태]이고 바람이 [풍속 수치를 배제한 체감적인 자연스러운 묘사(예: 살랑살랑/다소 강하게)] 부는 {time_of_day}이라 [날씨에 따른 짧은 체감/조언]네요. (⚠️ 날씨 안부는 오직 여기에만, 본문 첫 문단 딱 1문장으로 작성되어야 합니다.)
  
  (여기에 빈 줄을 두고 두 번째 문단부터 독립적인 주제 시작...)

1. **[첫 문단 - 구체적이고 자연스러운 날씨 정보 1문장 완성]**: 제공된 날씨 데이터 속의 실제 기온, 하늘상태, 미세먼지, 바람 정보를 모두 활용하되, 풍속이나 수치 등은 기계적으로 숫자를 그대로 노출하지 말고 실생활에서 느껴지는 자연스러운 감각적 묘사(예: "살랑살랑 부는", "선선한 바람이 부는", "조금 강하게 부는" 등)로 반드시 변환하여 자연스럽게 이어진 딱 1문장으로 깔끔하게 작성하십시오. 문장의 끝에는 날씨 데이터에 어울리는 매우 짧고 자연스러운 체감 느낌이나 조언을 덧붙여 마침표와 함께 첫 문단을 즉시 종결하십시오.
   - 작성 예시: "오늘 {refined_location}은 기온이 [상세 데이터 속 기온]도에 미세먼지는 [미세먼지 상태], 하늘이 [상세 데이터 속 날씨 상태]이고 바람이 [기분 좋게 선선히/다소 강하게 등] 부는 {time_of_day}이라 살짝 추울수도 있어요."
   - 🚨 [날씨 인사의 본문 강제 종속 락(Lock)]: 날씨 인사는 무조건 **`[본문]` 마커 바로 아래 첫 줄**에만 배치되어야 하며, `[제목]` 마커 안이나 제목보다 먼저(글의 맨 첫머리에) 작성되는 행위를 **100% 절대 원천 금지**합니다. (날씨 팩트가 제목이 되는 즉시 심각한 블로그 품질 훼손입니다.)
   - 🚨 [감성적 안부 및 상투어 100% 절대 금지]: 날씨에 대한 짧은 체감(예: 춥다, 덥다 등) 외에 "기분 좋은 하루 보내시길 바랍니다...", "건강 유의하시고...", "행복한 하루 되세요" 등 억지스러운 안부나 행복 기원 멘트는 **100% 원천 배제**하십시오. 오직 날씨 팩트와 그에 따른 체감 정보 1문장으로만 도입부를 종결하십시오.
   - 🚨 [가짜 수치 날조 금지 및 자연스러운 묘사]: 기온 등의 수치는 실제 제공된 데이터를 사용하되, 풍속(m/s)과 같은 수치는 절대 그대로 쓰지 말고 인간적인 체감 언어로 바꾸세요. 임의로 가짜 데이터를 지어내는 행위는 금지합니다. 데이터에 특정 정보(바람 등)가 없다면 해당 부분만 자연스럽게 생략하십시오.
2. **[어색한 전개 및 억지 결합 원천 배제]**: 날씨 문단 내에서 혹은 본문 첫머리에서 특정 업종이나 활동 공간, 거창한 건강 멘트, 혹은 점퍼를 챙기라는 등의 상투적이고 인위적인 멘트를 작성하여 본문과 엮는 행위를 **100% 원천 전면 금지**합니다. 날씨 인사는 순수한 팩트 날씨 묘사와 짧은 체감으로만 짧게 문단을 끝내야 합니다.
3. **[날씨-본문 완벽 분리 및 연결 단어/맥락 100% 완전 전면 금지 ⭐⭐⭐⭐⭐]**: 
   - 날씨 인사가 끝난 뒤 새로운 문단(본문)이 시작될 때, 이전의 날씨 인사와 본문을 자연스럽게 연결하려는 어떠한 징검다리 전개나 억지 맥락(예: "맑은 하늘 아래 가볍게 산책하기 참 좋은 날이네요. 오늘의 주제인..." 과 같은 인과관계식 전개)을 **100% 철저히 전면 차단 금지**합니다.
   - 날씨 문단과 본문 문단은 **어떠한 연관성도 가지지 않는 완벽하게 독립된 정보 영역**이어야 합니다. 
   - 날씨 인사를 마치고 새로운 문단(본문)이 시작될 때는 툭 자르듯이 어떠한 연결 단어(예: "이런 날씨 속에서", "선선한 날씨 속에", "이런 기온에도" 등) 없이 오직 오늘의 본론 주제(예: "인간의 신체 밸런스를 향상시키는 핵심 코어 근육은...")로 즉시 곧바로 정직하게 시작하십시오.
4. **[호칭 언급 절대 금지]**: 첫 도입부에서 특정 호칭(예: 부모님, 학부모님 등)을 불러 대화하듯 독자를 지칭하는 자동화 AI 말투를 100% 원천 금지합니다. 호칭을 완전히 생략하고 반갑고 신선한 인간적인 말투로만 작성하세요.

"""
    def _search_brave(self, query: str, count: int = 3) -> str:
        """Brave Search API를 이용한 실시간 정보 검색"""
        api_key = self.settings.get('brave_key')
        if not api_key: return ""
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            params = urllib.parse.urlencode({"q": query, "count": count})
            req = urllib.request.Request(f"{url}?{params}", headers={"X-Subscription-Token": api_key, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            results = [f"- **{i.get('title')}**: {i.get('description')}" for i in data.get('web', {}).get('results', [])]
            return "\n".join(results)
        except: return ""

    def _filter_news_content(self, text: str) -> bool:
        """뉴스 내용에 금칙어가 포함되어 있는지 확인"""
        forbidden_keywords = [
            '정치', '여당', '야당', '대통령', '의원', '선거', '투표', '탄핵', '시위', 
            '종교', '교회', '성당', '불교', '기독교', '목사', '스님', '사이비',
            '살인', '성범죄', '마약', '도박', '자살', '충격', '경악', '속보', '19금', '성인'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in text:
                return True
        return False

    def _get_trending_topics(self, count=3, force_refresh=False):
        # 오후/저녁용: 최신 뉴스/이슈/트렌드 정보 수집
        # count: 가져올 뉴스 수 (기본 3, 배치 분배용 6)
        
        # 0순위: 로컬 캐시 확인
        cache_file = os.path.join("config", "news_cache.json")
        try:
            if not force_refresh and os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                last_updated_str = cache_data.get('last_updated', '')
                if last_updated_str:
                    last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - last_updated < timedelta(hours=6):
                        news_lines = cache_data.get('news', [])
                        if news_lines:
                            logger.info("로컬 뉴스 캐시를 사용합니다.")
                            return "\n".join(news_lines[:count])
        except Exception as e:
            logger.warning(f"뉴스 캐시 읽기 실패 (무시됨): {e}")

        try:
            fetched_news = []
            
            # 1순위: Brave Search로 오늘의 핫이슈 검색
            brave_result = self._search_brave("오늘 뉴스 이슈 트렌드", count=count * 2) # 필터링 고려해 더 많이 검색
            if brave_result:
                # 🟢 코드 레벨 필터링 적용
                lines = brave_result.split('\n')
                for line in lines:
                    if line.strip() and not self._filter_news_content(line):
                        fetched_news.append(line.strip())
            
            # 2순위: 네이버 실시간 검색어/인기 검색어 크롤링
            if not fetched_news:
                try:
                    url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote("오늘 뉴스")
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                        html = response.read().decode('utf-8')
                    
                    # 뉴스 제목 추출
                    news_titles = re.findall(r'class="news_tit"[^>]*>(.*?)<', html)
                    if news_titles:
                        idx = 1
                        for title in news_titles:
                            if not self._filter_news_content(title):
                                fetched_news.append(f"{idx}. {title}")
                                idx += 1
                except Exception:
                    pass
            
            # 검색 결과를 캐시에 저장
            if fetched_news:
                try:
                    os.makedirs("config", exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "news": fetched_news
                        }, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.warning(f"뉴스 캐시 저장 실패: {e}")
                
                return "\n".join(fetched_news[:count])
                
            # 3순위: 기본 안내 (검색 실패 시)
            return (
                "[최신 이슈를 찾지 못했습니다]\n"
                "최근 뉴스, 유행어, 생활 꿀팁, 재미있는 상식 중에서\n"
                "하나를 선택하여 자유롭게 글을 시작해주세요."
            )
        except Exception as e:
            logger.warning(f"트렌드 정보 수집 실패: {e}")
            return None

    def _build_evening_hook_message(self):
        """저녁 포스팅용 훅 메시지 생성"""
        return """
[System: 저녁 마감 지침 - 밴드 전용]
1. **[본문 구성]**: 오늘 하루를 정성껏 마무리하며 학부모님께 건네는 따뜻한 '마감 인사'와 함께, 실생활에 유익한 교육/생활 정보나 공감되는 글을 본문에 자연스럽게 녹여내세요.
2. **[내일 예보]**: 글의 마지막 부분(홈케어 팁 직전)에는 반드시 **'내일 기상 정보'**를 상세히 안내하여, 부모님들이 내일을 실질적으로 대비하실 수 있도록 다정하고 정확하게 챙겨주세요.
⚠️ **[주의]**: 체육관 일상 등 단순 나열보다는, 학부모님과 교감하고 '유익한 정보 공유' 및 '공감'에 집중하여 작성하세요.
⚠️ 할루시네이션 방지: 날씨 수치는 반드시 제공된 [실시간 날씨 상세 정보]를 절대적으로 따르세요.
"""

    def _build_news_hook_message(self, platform='blog'):
        """AI에게 전달할 뉴스/트렌드 훅 메시지 생성 (Strict Fact Only)"""
        search_query = "실시간 스포츠 교육 건강 뉴스"
        news_info = self._search_brave(search_query, count=3)
        
        if not news_info:
            return ""
            
        return f"""
[System: 실시간 뉴스/트렌드 정보]
- 검색 결과: 
{news_info}

⚠️ [뉴스 활용 지침]
1. 위 '검색 결과'에 있는 정보만 오늘의 주제와 '자연스럽게' 연결하여 언급하세요.
2. 만약 검색 결과가 없거나 주제와 관련이 없다면 뉴스를 절대로 언급하지 마세요. (상상해서 작성 금지)
3. 정치, 경제, 부정적인 사건사고 뉴스는 절대 언급하지 마세요.
4. 오직 위 제공된 팩트(Fact)에 기반해서만 작성하세요.
"""

    def _check_is_forecast(self, target_time: str = None) -> bool:
        """예약 시간이 현재보다 미래(내일)인지 판별"""
        if not target_time: return False
        try:
            now = datetime.now()
            t_hour = None
            t_min = 0
            if isinstance(target_time, str):
                cleaned_str = str(target_time).strip()
                if len(cleaned_str) > 10 and ':' in cleaned_str:
                    import re
                    h_match = re.search(r'\s(\d{1,2}):(\d{2})', cleaned_str)
                    if h_match:
                        t_hour = int(h_match.group(1))
                        t_min = int(h_match.group(2))
                else:
                    t_hour, t_min = map(int, cleaned_str.split(':'))
            elif hasattr(target_time, 'hour'):
                t_hour = target_time.hour
                t_min = target_time.minute
                
            if t_hour is not None:
                target_dt = now.replace(hour=t_hour, minute=t_min, second=0, microsecond=0)
                if target_dt < now:
                    return True
            return False
        except: 
            return False

    def _get_semester_context(self):
        month = datetime.now().month
        if month in [1, 2, 7, 8]: return {"period_name": "방학", "instruction": "방학 기간입니다."}
        return None
