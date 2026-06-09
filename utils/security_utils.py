import os
import base64
import uuid
import hashlib
import json

import platform
import subprocess
from utils.path_utils import get_config_dir

def get_machine_id():
    """Returns a unique ID for the current machine."""
    config_dir = get_config_dir()
    machine_id_file = os.path.join(config_dir, ".machine_id")
    
    # 1. 파일에서 읽기 (가장 안정적, 네트워크 변경에 영향 안 받음)
    if os.path.exists(machine_id_file):
        try:
            with open(machine_id_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass
            
    # 2. macOS 고유 식별자 또는 uuid.getnode()로 생성
    machine_id = "default-machine-id"
    try:
        if platform.system() == "Darwin":
            output = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
            ).decode("utf-8")
            for line in output.split('\n'):
                if "IOPlatformUUID" in line:
                    machine_id = line.split('"')[3]
                    break
        
        if machine_id == "default-machine-id":
            machine_id = str(uuid.getnode())
    except Exception:
        machine_id = str(uuid.uuid4())
        
    # 3. 변경되지 않도록 파일에 영구 저장
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(machine_id_file, "w") as f:
            f.write(machine_id)
    except Exception:
        pass
        
    return machine_id

def _get_secret_key():
    """Generates a secret key based on the machine ID."""
    machine_id = get_machine_id()
    return hashlib.sha256(machine_id.encode()).digest()

def obfuscate(data: str) -> str:
    """Obfuscates a string using a machine-specific key."""
    if not data:
        return ""
    key = _get_secret_key()
    data_bytes = data.encode()
    # Simple XOR obfuscation
    obfuscated = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
    return base64.b64encode(obfuscated).decode()

def deobfuscate(obfuscated_data: str) -> str:
    """Deobfuscates a string using a machine-specific key."""
    if not obfuscated_data:
        return ""
    try:
        key = _get_secret_key()
        obfuscated_bytes = base64.b64decode(obfuscated_data)
        deobfuscated = bytes([b ^ key[i % len(key)] for i, b in enumerate(obfuscated_bytes)])
        return deobfuscated.decode()
    except Exception:
        # If deobfuscation fails, it might not be obfuscated (fallback)
        return ""

def obfuscate_dict_fields(d: dict, fields: list) -> dict:
    """Obfuscates specific fields in a dictionary."""
    new_dict = d.copy()
    for field in fields:
        if field in new_dict and new_dict[field]:
            new_dict[field] = f"OBF:{obfuscate(str(new_dict[field]))}"
    return new_dict

def deobfuscate_dict_fields(d: dict) -> dict:
    """Deobfuscates fields starting with 'OBF:' in a dictionary."""
    new_dict = d.copy()
    for key, value in new_dict.items():
        if isinstance(value, str) and value.startswith("OBF:"):
            new_dict[key] = deobfuscate(value[4:])
    return new_dict
