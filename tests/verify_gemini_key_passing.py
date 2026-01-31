
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.gpt_handler import GPTHandler

# Mock Config
class MockConfig:
    GPT_MODEL = "gpt-4o-mini"
    AI_MODELS = {
        "gemini-2.5-flash-lite": {"provider": "gemini"},
        "gpt-4o-mini": {"provider": "openai"}
    }
    GEMINI_API_KEY = "" # Intentionally empty

import modules.gpt_handler
modules.gpt_handler.Config = MockConfig

def test_api_key_passing():
    print("🧪 API Key passing test start...")
    
    # Initialize handler without key
    handler = GPTHandler(use_dummy=True)
    handler.gemini_api_key = "" # Ensure it's empty
    
    # Mock _generate_with_gemini to just check the key
    original_method = handler._generate_with_gemini
    
    def mock_generate(model_name, system_message, user_prompt, api_key=None):
        print(f"   Using API Key: '{api_key}'")
        if api_key == "TEST_KEY_12345":
            return "SUCCESS: Key passed correctly"
        else:
            raise ValueError(f"Wrong key used: {api_key}")
            
    handler._generate_with_gemini = mock_generate
    
    # Test valid key provided in config
    print("\n1. Testing with valid key in post_type_config...")
    post_type_config = {
        "selected_models": ["gemini-2.5-flash-lite"],
        "gemini_api_key": "TEST_KEY_12345"
    }
    
    try:
        # We expect this to call mock_generate and return the success message (wrapped in title/body parsing)
        # Since _parse_content expects formats, we might get empty title/body but the call itself happens
        handler._parse_content = lambda x: ("Title", x) # Mock parser
        handler._validate_content = lambda x: True # Mock validator
        
        handler.generate_content("Test Topic", post_type_config=post_type_config)
        print("✅ Test 1 Passed: API key argument reached generate method.")
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")

    # Test missing key
    print("\n2. Testing with NO key...")
    post_type_config_no_key = {
        "selected_models": ["gemini-2.5-flash-lite"],
        "gemini_api_key": ""
    }
    
    try:
        handler.generate_content("Test Topic", post_type_config=post_type_config_no_key)
        print("❌ Test 2 Failed: Should have raised error but didn't.")
    except ValueError as e:
        print(f"✅ Test 2 Passed: Correctly raised error: {e}")
    except Exception as e:
        print(f"❓ Test 2 Unexpected error: {e}")

if __name__ == "__main__":
    test_api_key_passing()
