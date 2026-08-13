import re

with open("naver_blog_auto.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add user_data_dir to __init__
text = re.sub(r"self\.base_dir = os\.path\.dirname\(os\.path\.abspath\(__file__\)\)",
              "self.base_dir = os.path.dirname(os.path.abspath(__file__))\n        self.user_data_dir = getattr(self, 'user_data_dir', self.base_dir)",
              text)

# Replace config loading to use user_data_dir
text = re.sub(r"os\.path\.join\(self\.base_dir, 'config', 'user_settings\.txt'\)",
              r"os.path.join(self.user_data_dir, 'config', 'user_settings.txt')", text)
text = re.sub(r"os\.path\.join\(self\.base_dir, 'config', 'app_settings\.json'\)",
              r"os.path.join(self.user_data_dir, 'config', 'app_settings.json')", text)

# For default_images, it's safer to use user_data_dir too if we moved them
text = re.sub(r"self\.default_images_folder = os\.path\.join\(self\.base_dir, \"default_images\"\)",
              r"self.default_images_folder = os.path.join(self.user_data_dir, \"default_images\")", text)

with open("naver_blog_auto.py", "w", encoding="utf-8") as f:
    f.write(text)
print("naver_blog_auto patched!")
