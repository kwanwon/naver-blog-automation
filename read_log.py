import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(encoding='utf-8')

try:
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        local_app_data = os.path.expanduser('~\\AppData\\Local')
    
    log_path = os.path.join(local_app_data, 'BlogAutomation', 'logs', 'debug.log')
    print(f"Reading log from: {log_path}")
    
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            print("--- Last 20 lines of log ---")
            for line in lines[-20:]:
                print(line.strip())
            print("----------------------------")
    else:
        print("Log file not found.")

except Exception as e:
    print(f"Error reading log: {e}")
