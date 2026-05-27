import os, sys
sys.path.append(os.path.abspath('.'))
from modules.ai_experts.base_expert import BaseAIExpert
expert = BaseAIExpert()
print("KMA Key present:", bool(expert.settings.get('kma_api_key')))
print("Weather at 14:00 tomorrow:", expert._get_kma_weather("양양", delta_days=1, target_hour=14))
print("Weather at 07:00 tomorrow:", expert._get_kma_weather("양양", delta_days=1, target_hour=7))
print("Weather at 21:00 today:", expert._get_kma_weather("양양", delta_days=0, target_hour=21))

print("Naver Fallback at 14:00 tomorrow:", expert._get_naver_weather("양양", delta_days=1))
print("Naver Fallback at 07:00 tomorrow:", expert._get_naver_weather("양양", delta_days=1))
print("Naver Fallback at 21:00 today:", expert._get_naver_weather("양양", delta_days=0))
