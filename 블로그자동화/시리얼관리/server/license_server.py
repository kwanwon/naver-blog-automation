from flask import Flask, request, jsonify
import hashlib
import datetime
import sqlite3
import os
import secrets

app = Flask(__name__)

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS licenses
    (serial_key TEXT PRIMARY KEY, 
     activation_date TEXT,
     expiry_date TEXT,
     is_activated INTEGER,
     machine_id TEXT,
     last_check TEXT)
    ''')
    conn.commit()
    conn.close()

# 시리얼 키 생성
def generate_serial_key():
    """5-5-5-5-5 형식의 시리얼 키 생성"""
    key = secrets.token_hex(12)
    chunks = [key[i:i+5] for i in range(0, len(key), 5)]
    return '-'.join(chunks[:5]).upper()

# 새 라이선스 생성
@app.route('/api/create_license', methods=['POST'])
def create_license():
    data = request.json
    if 'admin_key' not in data or data['admin_key'] != os.environ.get('ADMIN_KEY', 'admin_secret'):
        return jsonify({'success': False, 'message': '관리자 인증 실패'}), 403
        
    # 유효기간 (기본 1년)
    days = data.get('days', 365)
    expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    
    serial_key = generate_serial_key()
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO licenses VALUES (?, ?, ?, ?, ?, ?)", 
        (serial_key, datetime.datetime.now().isoformat(), expiry, 0, None, None)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'serial_key': serial_key,
        'expiry': expiry
    })

# 라이선스 검증
@app.route('/api/validate', methods=['POST'])
def validate_license():
    data = request.json
    if 'serial_key' not in data or 'machine_id' not in data:
        return jsonify({'valid': False, 'message': '요청 데이터 불완전'}), 400
        
    serial_key = data['serial_key']
    machine_id = data['machine_id']
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date, is_activated, machine_id FROM licenses WHERE serial_key = ?", (serial_key,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'valid': False, 'message': '잘못된 시리얼 키'})
        
    expiry_date, is_activated, stored_machine_id = result
    
    # 만료 확인
    expiry = datetime.datetime.fromisoformat(expiry_date)
    if expiry < datetime.datetime.now():
        conn.close()
        return jsonify({'valid': False, 'message': '라이선스가 만료되었습니다'})
    
    # 기기 등록 확인
    if is_activated:
        if stored_machine_id != machine_id:
            conn.close()
            return jsonify({'valid': False, 'message': '이 라이선스는 다른 기기에 등록되어 있습니다'})
    else:
        # 새 기기 등록
        c.execute(
            "UPDATE licenses SET is_activated = 1, machine_id = ? WHERE serial_key = ?", 
            (machine_id, serial_key)
        )
        
    # 마지막 확인 시간 업데이트
    c.execute(
        "UPDATE licenses SET last_check = ? WHERE serial_key = ?", 
        (datetime.datetime.now().isoformat(), serial_key)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'valid': True,
        'message': '라이선스가 유효합니다',
        'expiry': expiry_date
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True) 