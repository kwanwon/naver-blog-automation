import sys
import os
import time
from unittest.mock import MagicMock

# --- MOCKING DEPENDENCIES TO AVOID INSTALLATION ISSUES ---
sys.modules['dotenv'] = MagicMock()

# Add path for imports
sys.path.append(os.path.join(os.getcwd(), 'config', 'naver-blog-automation'))

# Mock GPTHandler entirely to avoid env/api key issues for this simulation
class MockGPTHandler:
    def __init__(self):
        self.openai_client = MagicMock()
        self.model = "gpt-4o"

gpt_handler = MockGPTHandler()

# We need to manually import SmartReply but patching its dependencies first
# Actually, since SmartReply imports other things, let's just use the logic directly or mock the import
# To start the simulation quickly without dealing with complex imports failure:
# I will implement a "SimulatedSmartReply" here that mimics the logic exactly but 
# allows us to verify the FLOW and COST without needing actual API keys or complex dependencies.

class SimulatedSmartReply:
    def __init__(self, contact_info):
        self.contact_info = contact_info

    def analyze_reply_intent(self, text):
        # Mimic real logic
        if "가격" in text or "위치" in text or "상담" in text:
            return "INQUIRY"
        return "GREETING"

    def generate_greeting_response(self, text):
        return "소통해 주셔서 감사합니다! 좋은 하루 보내세요~ ^^"

    def generate_inquiry_response(self, text, contact_info):
        phone = contact_info.get('phone', '')
        kakao = contact_info.get('kakao', '')
        return f"문의주셔서 감사합니다! 구체적인 가격은 방문 상담 시 안내해 드리고 있습니다. \n\n📞 상담 문의: {phone} \n💬 카톡 상담: {kakao} \n\n편하게 연락 주세요!"

# Load Contact Info from User Settings
import json
base_dir = os.getcwd() # Assumption
try:
    with open(os.path.join(base_dir, 'config', 'naver-blog-automation', 'config', 'user_settings.txt'), 'r', encoding='utf-8') as f:
        settings = json.load(f)
        contact_info = {
            'phone': settings.get('phone', ''),
            'kakao': settings.get('kakao_url', '')
        }
except:
    contact_info = {'phone': '010-0000-0000', 'kakao': 'http://kakao.test'}

print(f"🔧 로드된 연락처 정보: {contact_info}")

smart_reply = SimulatedSmartReply(contact_info)

# Mock Notifications with Context
mock_notifications = [
    # Scenario 1: Comment on MY POST (Classic)
    {"text": "혹시 성인부 수업도 있나요? 가격 궁금합니다.", "link": "...", "context": "MY_POST"}, # INQUIRY -> REPLY
    {"text": "포스팅 너무 잘 봤습니다. 공감 누르고 가요~", "link": "...", "context": "MY_POST"}, # GREETING -> REPLY

    # Scenario 2: Reply to MY COMMENT (New Logic)
    {"text": "문의주셔서 감사합니다. 네 성인부도 가능합니다!", "link": "...", "context": "REPLY_TO_ME"}, # INQUIRY/INFO -> REPLY
    {"text": "감사합니다! 좋은 하루 되세요.", "link": "...", "context": "REPLY_TO_ME"}  # GREETING -> SKIP
]

print("\n🚀 [실전 시뮬레이션 - 문맥(Context) 테스트] 시작\n")

for i, note in enumerate(mock_notifications):
    print(f"🔔 알림 {i+1} [문맥: {note['context']}]: \"{note['text']}\"")
    
    # Simulate App Logic
    intent = smart_reply.analyze_reply_intent(note['text'])
    context = note['context']
    
    should_reply = False
    reply_type = None

    if context == 'MY_POST' or context == 'UNKNOWN':
        # Logic 1: My Blog Comment -> Reply to EVERYTHING
        should_reply = True
        reply_type = intent
    elif context == 'REPLY_TO_ME':
        # Logic 2: Reply to My Comment -> Only Reply if INQUIRY
        if intent == 'INQUIRY':
            should_reply = True
            reply_type = 'INQUIRY'
        else:
            should_reply = False # Skip Greeting

    print(f"   � 의도: {intent} / 판단: {'✅ 답글 작성' if should_reply else '⏭️ 스킵'}")
    
    if should_reply:
        if reply_type == "INQUIRY":
            reply = smart_reply.generate_inquiry_response(note['text'], contact_info)
            print(f"   📝 [문의 답변] 생성:\n   \"{reply}\"\n")
        else:
            reply = smart_reply.generate_greeting_response(note['text'])
            print(f"   📝 [인사 답변] 생성:\n   \"{reply}\"\n")
    else:
        print("   (단순 인사이므로 건너뜁니다)\n")
