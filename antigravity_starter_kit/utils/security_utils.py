import os
import base64
import uuid
import hashlib
import json

def get_machine_id():
    """Returns a unique ID for the current machine."""
    # Try to get MAC address or other unique identifier
    try:
        node = uuid.getnode()
        return str(node)
    except:
        return "default-machine-id"

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
