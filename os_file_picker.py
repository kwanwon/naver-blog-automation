import sys
import os
import time
import subprocess
import traceback

class OSFilePicker:
    """
    OS standard file selection dialog controller.
    Uses AppleScript on macOS and (placeholder) for Windows.
    """
    def __init__(self):
        self.is_mac = sys.platform == "darwin"
        print(f"OSFilePicker initialized (Platform: {sys.platform})")

    def select_file(self, file_path, timeout=15):
        """
        Wait for a file selection dialog to appear and select the specified file.
        """
        if not os.path.exists(file_path):
            print(f"❌ Error: File not found - {file_path}")
            return False

        abs_path = os.path.abspath(file_path)
        folder_path = os.path.dirname(abs_path)
        file_name = os.path.basename(abs_path)

        if self.is_mac:
            return self._select_file_mac(folder_path, file_name, timeout)
        else:
            print("⚠️ OSFilePicker: Windows is not yet implemented.")
            return False

    def _select_file_mac(self, folder_path, file_name, timeout):
        """macOS: Control Finder's Open Dialog using AppleScript."""
        print(f"🍎 macOS Finder control starting... (Path: {folder_path}/{file_name})")
        
        # AppleScript logic:
        # 1. Wait for "Open" or "열기" or similar dialog in the frontmost browser.
        # 2. Cmd+Shift+G to open "Go to folder" sheet.
        # 3. Type the folder path and press Enter.
        # 4. Type the filename and press Enter.
        
        script = f"""
        set max_wait to {timeout}
        set wait_count to 0
        set success to false

        tell application "System Events"
            -- 1. Wait for dialong in frontmost application (typically Chrome)
            repeat while wait_count < max_wait
                set front_app to name of first process whose frontmost is true
                tell process front_app
                    -- Check for Open/열기 dialog
                    set dialog_found to (exists window 1) 
                    -- On Mac, file pickers are often sheets or modal windows title "Open"
                    if dialog_found then
                        -- Try Cmd+Shift+G
                        keystroke "g" using {{command down, shift down}}
                        delay 0.5
                        
                        -- Enter folder path
                        keystroke "{folder_path}"
                        delay 0.5
                        keystroke return
                        delay 0.8
                        
                        -- Enter filename
                        keystroke "{file_name}"
                        delay 0.5
                        keystroke return
                        
                        set success to true
                        exit repeat
                    end if
                end tell
                delay 1
                set wait_count to wait_count + 1
            end repeat
        end tell
        return success
        """
        
        try:
            result = subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if result == "true":
                print("✅ AppleScript: File selection successful!")
                return True
            else:
                print("❌ AppleScript: Timed out or dialog not found.")
                return False
        except Exception as e:
            print(f"❌ AppleScript Error: {str(e)}")
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Simple test (requires an open file dialog to work)
    picker = OSFilePicker()
    # Replace with a real path for manual testing
    # picker.select_file("/Users/gm2hapkido/Desktop/test.mp4")
