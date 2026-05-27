import os
import json
import shutil

class MockApp:
    def __init__(self):
        self.is_windows = False
        self.is_macos = True
        self.base_dir = os.getcwd()
        self.settings = self.load_settings()

    def _get_app_data_dir(self):
        home = os.path.expanduser("~")
        return os.path.join(home, '.blog_automation_test')

    def load_settings(self):
        app_data_dir = self._get_app_data_dir()
        settings_path = os.path.join(app_data_dir, 'config', 'app_settings.json')
        print(f"Loading settings from: {settings_path}")
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}

    def save_settings(self):
        app_data_dir = self._get_app_data_dir()
        settings_path = os.path.join(app_data_dir, 'config', 'app_settings.json')
        print(f"Saving settings to: {settings_path}")
        try:
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _save_setting(self, key, value):
        print(f"Setting '{key}' to '{value}'")
        self.settings[key] = value
        self.save_settings()

def main():
    print("--- Test Start ---")
    app = MockApp()
    
    # Clean up previous test
    app_data_dir = app._get_app_data_dir()
    if os.path.exists(app_data_dir):
        shutil.rmtree(app_data_dir)
        print("Cleaned up test directory")
    
    # 1. Initial State
    app = MockApp() # Re-init to load empty
    print(f"Initial settings: {app.settings}")
    
    # 2. Save Setting
    app._save_setting('google_sheet_url', 'https://test.google.com/sheet')
    
    # 3. Simulate Restart
    print("\n--- Simulating Restart ---")
    new_app = MockApp()
    print(f"Loaded settings: {new_app.settings}")
    
    # 4. Verification
    if new_app.settings.get('google_sheet_url') == 'https://test.google.com/sheet':
        print("✅ SUCCESS: Setting persisted.")
    else:
        print("❌ FAILURE: Setting lost.")

if __name__ == "__main__":
    main()
