import sys
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

def load_settings():
    settings_path = os.path.join(os.path.expanduser('~/.blog_automation/config/user_settings.txt'))
    if not os.path.exists(settings_path):
        print("❌ 설정 파일을 찾을 수 없습니다.")
        return None
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_kma_weather_full(settings):
    """실제 _get_kma_weather 로직과 동일하게 실행"""
    api_key = settings.get('kma_api_key', '')
    location = settings.get('weather_location', '서울')
    
    if not api_key:
        print("❌ KMA API Key 미설정")
        return

    KMA_GRID_MAP = {
        "서울": (60, 127), "인천": (55, 124), "부평구": (55, 124), 
        "인천 부평구": (55, 124), "부산": (98, 76), "대구": (89, 90)
    }
    
    nx, ny = None, None
    for key, coords in KMA_GRID_MAP.items():
        if key in location or location in key:
            nx, ny = coords
            break
    if nx is None:
        for part in location.split():
            if part in KMA_GRID_MAP:
                nx, ny = KMA_GRID_MAP[part]
                break
    if nx is None: nx, ny = 60, 127
    
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    current_hhmm = now.strftime("%H%M")
    
    base_time = "2300"
    for bt in reversed(base_times):
        adjusted_bt = str(int(bt) + 10).zfill(4)
        if current_hhmm >= adjusted_bt:
            base_time = bt
            break
    else:
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        base_time = "2300"
    
    fcst_date = now.strftime("%Y%m%d")
    
    api_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": api_key, "numOfRows": 300, "pageNo": 1, "dataType": "JSON",
        "base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny
    }
    
    req = urllib.request.Request(f"{api_url}?{urllib.parse.urlencode(params)}")
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
    
    sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
    pty_map = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
    
    weather_data = {}
    for item in items:
        cat = item.get('category', '')
        fdate = item.get('fcstDate', '')
        ftime = item.get('fcstTime', '')
        fvalue = item.get('fcstValue', '')
        key = f"{fdate}_{ftime}"
        if key not in weather_data:
            weather_data[key] = {}
        weather_data[key][cat] = fvalue
    
    # Today
    today_temps = []
    current_sky = ""
    current_temp = ""
    current_pop = ""
    current_hour = now.strftime("%H00")
    closest_key = None
    
    for key in sorted(weather_data.keys()):
        if key.startswith(fcst_date):
            ftime = key.split('_')[1]
            if ftime <= current_hour:
                closest_key = key
            tmp = weather_data[key].get('TMP', weather_data[key].get('T1H', ''))
            if tmp:
                try: today_temps.append(float(tmp))
                except: pass
    
    if closest_key and closest_key in weather_data:
        vals = weather_data[closest_key]
        current_temp = vals.get('TMP', vals.get('T1H', '?'))
        sky_code = vals.get('SKY', '')
        current_sky = sky_map.get(sky_code, sky_code) if sky_code else ""
        pty_code = vals.get('PTY', '0')
        if pty_code and pty_code != '0':
            current_sky = pty_map.get(pty_code, current_sky)
        current_pop = vals.get('POP', '')
    
    min_temp = min(today_temps) if today_temps else "?"
    max_temp = max(today_temps) if today_temps else "?"
    
    # Yesterday comparison
    yesterday_temp = None
    try:
        yesterday = now - timedelta(days=1)
        yday_date = yesterday.strftime("%Y%m%d")
        yday_params = {
            "serviceKey": api_key, "numOfRows": 300, "pageNo": 1, "dataType": "JSON",
            "base_date": yday_date, "base_time": "0500", "nx": nx, "ny": ny
        }
        yday_req = urllib.request.Request(f"{api_url}?{urllib.parse.urlencode(yday_params)}")
        with urllib.request.urlopen(yday_req, timeout=8) as yday_response:
            yday_data = json.loads(yday_response.read().decode('utf-8'))
        
        yday_items = yday_data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        target_hour = now.strftime("%H00")
        for item in yday_items:
            if (item.get('fcstDate') == yday_date and 
                item.get('fcstTime') == target_hour and 
                item.get('category') == 'TMP'):
                yesterday_temp = float(item.get('fcstValue', ''))
                break
        
        if yesterday_temp is None:
            hour_int = int(now.strftime("%H"))
            for offset in [-1, 1, -2, 2]:
                check_hour = f"{(hour_int + offset) % 24:02d}00"
                for item in yday_items:
                    if (item.get('fcstDate') == yday_date and 
                        item.get('fcstTime') == check_hour and 
                        item.get('category') == 'TMP'):
                        yesterday_temp = float(item.get('fcstValue', ''))
                        break
                if yesterday_temp is not None:
                    break
    except Exception as e:
        print(f"⚠️ 어제 기온 조회 실패: {e}")
    
    # Result
    result_text = (
        f"[{location} 현재 날씨 (기상청 단기예보)]\n"
        f"지역: {location}\n"
        f"현재 기온: {current_temp}도 ({current_sky})\n"
        f"최저/최고: {min_temp if isinstance(min_temp, str) else f'{min_temp:.0f}'}"
        f"/{max_temp if isinstance(max_temp, str) else f'{max_temp:.0f}'}도"
    )
    if current_pop:
        result_text += f"\n강수확률: {current_pop}%"
    
    if yesterday_temp is not None and current_temp != '?':
        try:
            today_val = float(current_temp)
            diff = today_val - yesterday_temp
            if diff > 0:
                result_text += f"\n어제 같은 시간({yesterday_temp:.0f}도)보다 {abs(diff):.1f}도 높습니다 (↑상승)"
            elif diff < 0:
                result_text += f"\n어제 같은 시간({yesterday_temp:.0f}도)보다 {abs(diff):.1f}도 낮습니다 (↓하강)"
            else:
                result_text += f"\n어제 같은 시간과 동일한 기온입니다"
        except (ValueError, TypeError):
            pass
    
    print("=" * 50)
    print("📋 AI에게 전달될 날씨 텍스트:")
    print("=" * 50)
    print(result_text)
    print("=" * 50)

if __name__ == "__main__":
    settings = load_settings()
    if settings:
        test_kma_weather_full(settings)
