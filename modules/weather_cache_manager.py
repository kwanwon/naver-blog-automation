import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import logging
import re
from modules.ai_experts.base_expert import BaseAIExpert

logger = logging.getLogger("WeatherCacheManager")

class WeatherCacheManager:
    """
    Manages local caching of Korea Meteorological Administration (KMA) weather data
    and Naver fine dust data to prevent API downtime and eliminate latency (0.00s loading).
    """
    
    @staticmethod
    def get_cache_file_path():
        """Returns the absolute path to the weather cache file."""
        # Locate the config directory in the project structure
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(base_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "weather_cache.json")

    @classmethod
    def load_cache(cls):
        """Loads weather data from local JSON cache."""
        path = cls.get_cache_file_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load weather cache JSON: {e}")
            return {}

    @classmethod
    def save_cache(cls, data):
        """Saves weather data to local JSON cache."""
        path = cls.get_cache_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Successfully updated weather cache JSON on disk.")
        except Exception as e:
            logger.error(f"Failed to write weather cache JSON: {e}")

    @classmethod
    def refine_location(cls, location):
        """Simplifies the address to gu, dong, eup, myeon, or city unit."""
        if not location:
            return "서울"
        location = re.sub(r'\(.*?\)', '', location).strip()
        parts = location.split()
        for p in reversed(parts):
            p_clean = p.strip()
            if p_clean.endswith(('읍', '면', '동', '구', '시', '군')):
                return p_clean
        return parts[-1] if parts else "서울"

    @classmethod
    def get_grid_coords(cls, location):
        """Retrieves grid coordinates nx, ny for the given location using BaseAIExpert mapping."""
        refined = cls.refine_location(location)
        nx, ny = None, None
        for key, coords in BaseAIExpert.KMA_GRID_MAP.items():
            if key in location or location in key:
                nx, ny = coords
                break
        return nx, ny, refined

    @classmethod
    def fetch_dust_info(cls, location):
        """Fetches fine dust info from Naver weather search."""
        refined_loc = cls.refine_location(location)
        try:
            encoded = urllib.parse.quote(f"{refined_loc} 날씨")
            url = f"https://search.naver.com/search.naver?query={encoded}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            
            dust_patterns = [
                r'미세먼지</span>\s*<span class="txt">(.*?)</span>',
                r'미세먼지.*?<span class="txt">(.*?)</span>',
                r'<dt class="term">미세먼지</dt>\s*<dd class="desc">(.*?)</dd>'
            ]
            for p in dust_patterns:
                match = re.search(p, html, re.DOTALL)
                if match:
                    val = match.group(1).strip()
                    if val and len(val) < 10:
                        return val
        except Exception as e:
            logger.warning(f"Failed to fetch fine dust info for {location}: {e}")
        return None

    @classmethod
    def update_weather_cache(cls, location, api_key):
        """
        Background worker that queries the KMA Short-term Forecast API
        and updates the local cache config/weather_cache.json with 3 days of forecasts.
        """
        if not api_key:
            logger.warning("KMA API Key is missing. Falling back to Naver scraping for cache update.")
            return cls.update_weather_cache_via_naver(location)
            
        # [Fix] Decode KMA key first (to remove previous encoding) and then quote it properly.
        decoded_key = urllib.parse.unquote(api_key).strip()
        safe_key = urllib.parse.quote(decoded_key, safe='')
            
        nx, ny, refined_loc = cls.get_grid_coords(location)
        if nx is None:
            logger.warning(f"Grid coordinates not found for location: {location}")
            return False
            
        try:
            now = datetime.now()
            # KMA 3-hour interval announcements: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
            base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
            
            # Select announcement based on current time (with +15 min buffer to prevent 502)
            valid_base_time = "2300"
            base_date = now.strftime("%Y%m%d")
            real_now_time = int(now.strftime("%H%M"))
            
            for bt in reversed(base_times):
                if real_now_time >= int(bt) + 40:  # 40 minutes cushion to prevent 502 Bad Gateway
                    valid_base_time = bt
                    break
            else:
                base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
                valid_base_time = "2300"
                
            api_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
            params = {
                "numOfRows": 1000,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": valid_base_time,
                "nx": nx,
                "ny": ny
            }
            
            # [Fix] Keep serviceKey raw and unencoded, then join with other parameters
            req_url = f"{api_url}?serviceKey={safe_key}&{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(req_url)
            
            logger.info(f"Querying KMA API for {refined_loc} ({nx},{ny}) at base time {base_date} {valid_base_time}")
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
            items = response_data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if not items:
                logger.warning("Empty weather items returned from KMA API.")
                return False
                
            # Parse weather data into structured dictionary grouped by YYYYMMDD and Hour
            temp_cache = {}
            for item in items:
                f_date = item.get('fcstDate')
                f_time = item.get('fcstTime')  # e.g., '1400'
                if not f_date or not f_time:
                    continue
                    
                hour_key = f_time[:2]  # e.g., '14'
                date_key = f_date      # e.g., '20260524'
                
                if date_key not in temp_cache:
                    temp_cache[date_key] = {}
                if hour_key not in temp_cache[date_key]:
                    temp_cache[date_key][hour_key] = {}
                    
                cat = item.get('category')
                val = item.get('fcstValue')
                
                if cat == 'TMP':
                    temp_cache[date_key][hour_key]['temp'] = val
                elif cat == 'SKY':
                    temp_cache[date_key][hour_key]['sky'] = val
                elif cat == 'PTY':
                    temp_cache[date_key][hour_key]['pty'] = val
                elif cat == 'WSD':
                    temp_cache[date_key][hour_key]['wsd'] = val
                elif cat == 'POP':
                    temp_cache[date_key][hour_key]['pop'] = val
            
            # Fetch fine dust dynamically
            dust = cls.fetch_dust_info(location) or "보통"
            
            # Update cache file structure (Clear old forecasts completely to prevent stale data residual)
            cache_data = {
                'last_updated': now.strftime("%Y-%m-%d %H:%M:%S"),
                'location': location,
                'refined_location': refined_loc,
                'forecasts': {}
            }
                
            # Populate cache structure
            for d_key, hours in temp_cache.items():
                if d_key not in cache_data['forecasts']:
                    cache_data['forecasts'][d_key] = {}
                for h_key, metrics in hours.items():
                    # Calculate sky status string
                    sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
                    pty_map = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
                    
                    sky = metrics.get('sky', '1')
                    pty = metrics.get('pty', '0')
                    
                    sky_str = sky_map.get(sky, "정보없음")
                    pty_str = pty_map.get(pty, "")
                    weather_desc = f"{pty_str}({sky_str})" if pty_str else sky_str
                    
                    # Wind info
                    wsd = metrics.get('wsd', '')
                    wind_str = ""
                    if wsd:
                        try:
                            w_val = float(wsd)
                            if w_val >= 9: wind_str = f", 바람 매우 강함({wsd}m/s)"
                            elif w_val >= 4: wind_str = f", 바람 강함({wsd}m/s)"
                            elif w_val >= 1.5: wind_str = f", 바람 약간({wsd}m/s)"
                        except: pass
                        
                    cache_data['forecasts'][d_key][h_key] = {
                        "temp": metrics.get('temp', '?'),
                        "weather_desc": weather_desc,
                        "wind": wind_str,
                        "dust": dust,
                        "pop": metrics.get('pop', '0'),
                        "pty": pty
                    }
                    
            cls.save_cache(cache_data)
            logger.info("Successfully fetched KMA weather forecast and updated local cache!")
            return True
            
        except Exception as e:
            logger.error(f"Error during KMA API background update: {e}")
            logger.info("⚠️ 기상청 API 장애 또는 오류가 발생했습니다. 네이버 실시간 날씨 검색을 이용한 캐시 업데이트 폴백을 실행합니다...")
            return cls.update_weather_cache_via_naver(location)

    @classmethod
    def update_weather_cache_via_naver(cls, location):
        """
        Fallback worker that scrapes Naver weather and builds the local weather cache.
        Extracts today, tomorrow, and day-after-tomorrow weather metrics and structures them.
        """
        logger.info(f"🌐 [Naver Scraper Fallback] Scraping Naver weather for {location}...")
        refined = cls.refine_location(location)
        query = f"{refined} 날씨"
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?query={encoded_query}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='replace')
            
            # Fetch fine dust
            dust_patterns = [
                r'미세먼지</span>\s*<span class="txt">(.*?)</span>',
                r'미세먼지.*?<span class="txt">(.*?)</span>',
                r'<dt class="term">미세먼지</dt>\s*<dd class="desc">(.*?)</dd>'
            ]
            dust = "보통"
            for p in dust_patterns:
                match = re.search(p, html, re.DOTALL)
                if match:
                    val = match.group(1).strip()
                    if val and len(val) < 10:
                        dust = val
                        break
            
            now = datetime.now()
            # Update cache file structure (Clear old forecasts completely to prevent stale data residual)
            cache_data = {
                'last_updated': now.strftime("%Y-%m-%d %H:%M:%S"),
                'location': location,
                'refined_location': refined,
                'forecasts': {}
            }
                
            for d in [0, 1, 2]:
                target_date = (now + timedelta(days=d)).strftime("%Y%m%d")
                if target_date not in cache_data['forecasts']:
                    cache_data['forecasts'][target_date] = {}
                
                # Extract weather block for this day
                weather_block = html
                if d == 0:
                    m_block = re.search(r'class="blind">오늘의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                    if m_block: weather_block = m_block.group(0)
                elif d == 1:
                    m_block = re.search(r'class="blind">내일의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                    if m_block: weather_block = m_block.group(0)
                elif d == 2:
                    m_block = re.search(r'class="blind">모레의 날씨</h3>.*?(?:<div class="weather_info|<div class="sc_new|$)', html, re.DOTALL)
                    if m_block: weather_block = m_block.group(0)
                
                # Extract temperature
                temp = "18"
                if d in [1, 2]:
                    # Extract morning and afternoon forecast temperatures
                    am_temp = None
                    pm_temp = None
                    m_am = re.search(r'오전.*?class="temperature_text">.*?예측 온도</span>\s*(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if not m_am:
                        m_am = re.search(r'오전.*?class="temperature_text">.*?(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if m_am: am_temp = m_am.group(1).strip()
                    
                    m_pm = re.search(r'오후.*?class="temperature_text">.*?예측 온도</span>\s*(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if not m_pm:
                        m_pm = re.search(r'오후.*?class="temperature_text">.*?(-?\d+(?:\.\d+)?)(?:\xb0|<span)', weather_block, re.DOTALL)
                    if m_pm: pm_temp = m_pm.group(1).strip()
                    
                    # Store AM forecast for 08 AM, PM forecast for 14, 20 PM
                    for h_str, t_val in [("08", am_temp or pm_temp or "18"), ("14", pm_temp or am_temp or "22"), ("20", pm_temp or am_temp or "20")]:
                        cache_data['forecasts'][target_date][h_str] = {
                            "temp": t_val,
                            "weather_desc": "맑음" if "맑음" in weather_block or "태양" in weather_block else "구름많음",
                            "wind": "",
                            "dust": dust,
                            "pop": "0",
                            "pty": "0"
                        }
                else:
                    # Today forecast parsing
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
                    
                    # Extract weather description
                    weather_desc = "맑음"
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
                    
                    # Wind info
                    wind_str = ""
                    wind_match = re.search(r'풍속\s*<\/span>\s*<span class="txt">([^<]+)<\/span>', html, re.IGNORECASE)
                    if wind_match:
                        wind_str = f", 바람: {wind_match.group(1).strip()}"
                    
                    # Populate general day entries (08h, 11h, 14h, 17h, 20h, 23h)
                    for h_str in ["02", "05", "08", "11", "14", "17", "20", "23"]:
                        cache_data['forecasts'][target_date][h_str] = {
                            "temp": temp,
                            "weather_desc": weather_desc,
                            "wind": wind_str,
                            "dust": dust,
                            "pop": "0",
                            "pty": "1" if "비" in weather_desc or "소나기" in weather_desc else "0"
                        }
            
            cls.save_cache(cache_data)
            logger.info("🟢 SUCCESS: Local weather cache successfully created from Naver Weather!")
            return True
        except Exception as naver_err:
            logger.error(f"Failed to scrape Naver weather fallback: {naver_err}")
            return False

    @classmethod
    def get_cached_weather(cls, location, delta_days=0, target_hour=None):
        """
        Retrieves formatted weather string from the local cache database.
        Returns None if cache is outdated (e.g., location mismatch, older than 6 hours, or missing target).
        """
        cache = cls.load_cache()
        if not cache or 'forecasts' not in cache:
            return None
            
        # 1. Location match verification
        cached_loc = cache.get('location', '')
        if cls.refine_location(location) != cls.refine_location(cached_loc):
            logger.info(f"Cache miss: Location mismatch (Cached: {cached_loc}, Requested: {location})")
            return None
            
        # 2. Freshness check: older than 24 hours? (Extended for maximum availability)
        last_updated_str = cache.get('last_updated', '')
        if last_updated_str:
            try:
                last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_updated > timedelta(hours=24):
                    logger.info("Cache miss: Weather cache is older than 24 hours.")
                    return None
            except:
                pass
                
        # 3. Calculate target date string
        now = datetime.now()
        target_date = (now + timedelta(days=delta_days)).strftime("%Y%m%d")
        
        # 4. Determine target hour with 50-minute rounding rule
        if target_hour is not None:
            t_hour = int(target_hour)
        else:
            if now.minute >= 50:
                t_hour = (now.hour + 1) % 24
                if t_hour == 0:
                    now = now + timedelta(days=1)
                    target_date = (now + timedelta(days=delta_days)).strftime("%Y%m%d")
            else:
                t_hour = now.hour
            
        target_hour_str = f"{t_hour:02d}"
        
        day_forecasts = cache['forecasts'].get(target_date, {})
        if not day_forecasts:
            logger.info(f"Cache miss: Date {target_date} not found in forecasts.")
            return None
            
        # Try matching the exact target hour
        data = day_forecasts.get(target_hour_str)
        if not data:
            # Fallback to the nearest hour available in this date
            available_hours = sorted([int(h) for h in day_forecasts.keys()])
            if available_hours:
                nearest = min(available_hours, key=lambda x: abs(x - t_hour))
                data = day_forecasts.get(f"{nearest:02d}")
                t_hour = nearest
                
        if not data:
            return None
            
        # Format the advice block
        temp = data.get('temp', '?')
        weather_desc = data.get('weather_desc', '')
        wind_str = data.get('wind', '')
        dust = data.get('dust', '')
        pty = data.get('pty', '0')
        pop = data.get('pop', '0')
        
        # Georeferencing
        refined_loc = cache.get('refined_location', location)
        
        # Advice based on temperature
        advice = "편안하고 기분 좋은 날씨"
        try:
            t_val = float(temp)
            if t_val < 5: advice = "매우 쌀쌀하고 추운 날씨"
            elif t_val < 12: advice = "쌀쌀함이 느껴지는 날씨"
            elif t_val < 18: advice = "선선한 바람이 부는 날씨"
            elif t_val < 25: advice = "포근하고 활동하기 좋은 날씨"
            else: advice = "조금 더운 기운이 느껴지는 날씨"
        except:
            pass
            
        # Precipitation pre-warning detection logic
        rain_alert = ""
        # Check if rain is forecasted in future hours of the target day
        rain_hours = []
        for h_str, metrics in day_forecasts.items():
            try:
                h_val = int(h_str)
                if h_val >= t_hour:
                    if metrics.get('pty') in ['1', '2', '4']:
                        rain_hours.append(h_val)
                    elif int(metrics.get('pop', '0')) >= 60:
                        rain_hours.append(h_val)
            except:
                pass
                
        # Final output structure matching the expected format exactly
        label_map = {0: "현재", 1: "내일", 2: "모레"}
        day_label = label_map.get(delta_days, f"{delta_days}일 뒤")
        label = f"{day_label} {t_hour}시 예보" if delta_days > 0 else f"현재({t_hour}시)"
        
        dust_info = f", 미세먼지: {dust}" if dust else ""
        pop_info = f", 강수확률: {pop}%" if pop else ""
        advice_section = f" ({rain_alert} {advice})" if rain_alert else f" ({advice})"
        
        # [Location label] 기온: XX도, 하늘: XX, 바람: XX, 미세먼지: XX, 강수확률: XX%. (Advice)
        return f"[{refined_loc} {label}] 기온: {temp}도, 하늘: {weather_desc}{wind_str}{dust_info}{pop_info}.{advice_section}"

    @classmethod
    def generate_posting_weather_text(cls, location, target_datetime=None) -> str:
        """
        즉시/예약 발행용 지능형 날씨 문구 생성기.
        target_datetime: datetime 객체 혹은 YYYY-MM-DD HH:MM 형식의 문자열 (예약 발행 시점)
        """
        if not location:
            return ""
            
        now = datetime.now()
        target_dt = now
        
        if target_datetime:
            if isinstance(target_datetime, str):
                try:
                    # Try parsing 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS'
                    cleaned_str = target_datetime.strip()
                    if len(cleaned_str) > 16:
                        target_dt = datetime.strptime(cleaned_str[:16], "%Y-%m-%d %H:%M")
                    else:
                        target_dt = datetime.strptime(cleaned_str, "%Y-%m-%d %H:%M")
                except Exception as e:
                    logger.warning(f"Failed to parse target_datetime string '{target_datetime}': {e}")
                    target_dt = now
            elif isinstance(target_datetime, datetime):
                target_dt = target_datetime

        # Apply 50-minute rounding rule to match the nearest forecast hour
        if target_dt.minute >= 50:
            target_dt = target_dt + timedelta(hours=1)

        # 예보 제공 대상: 현재로부터 최대 3일(72시간) 이내
        diff = target_dt - now
        diff_days = diff.days
        
        # 날짜 차이(delta_days) 계산
        # 당일(0), 내일(1), 모레(2)
        target_date_str = target_dt.strftime("%Y-%m-%d")
        now_date_str = now.strftime("%Y-%m-%d")
        
        if target_date_str == now_date_str:
            delta_days = 0
        elif target_date_str == (now + timedelta(days=1)).strftime("%Y-%m-%d"):
            delta_days = 1
        elif target_date_str == (now + timedelta(days=2)).strftime("%Y-%m-%d"):
            delta_days = 2
        else:
            delta_days = -1 # 3일 이후 예보 불가능 영역
            
        refined_loc = cls.refine_location(location)
        
        if delta_days == -1:
            # 3일 초과 예약 날씨 처리
            return (
                f"\n\n---\n"
                f"📢 [실시간 안내] 본 포스팅은 {target_dt.strftime('%m월 %d일 %H시 %M분')}에 예약 발행된 정보글입니다. "
                f"포스팅 시점의 {refined_loc} 상세 기상 정보(온도, 강수확률 등)는 당일 기상청 실시간 예보를 통해 확인하실 수 있습니다. "
                f"늘 건강하고 행복한 하루 보내세요! ☀️"
            )
            
        # 3일 이내인 경우 캐시 데이터에서 정확한 시간 매칭 시도
        weather_str = cls.get_cached_weather(location, delta_days=delta_days, target_hour=target_dt.hour)
        
        if not weather_str:
            # 캐시 미스 시 네이버 scraping으로 시도
            cls.update_weather_cache_via_naver(location)
            weather_str = cls.get_cached_weather(location, delta_days=delta_days, target_hour=target_dt.hour)
            
        if not weather_str:
            return ""
            
        # 생성된 날씨 정보를 담은 고품격 문장 결합
        label_map = {0: "현재", 1: "내일", 2: "모레"}
        day_label = label_map.get(delta_days, "예약일")
        
        # 포스팅 매칭에 맞는 완벽한 문장 가다듬기
        info_sentence = (
            f"\n\n---\n"
            f"⛅ [실시간 날씨 정보] 본 글은 {refined_loc} 지역 기상 정보와 함께합니다.\n"
            f"포스팅 시점({day_label} {target_dt.hour}시)의 {weather_str}\n"
            f"오늘 하루도 기분 좋게 시작하시길 바라며, 건강 관리에 유의하세요! 🍀"
        )
        return info_sentence

