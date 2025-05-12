from flask import Flask, request, jsonify
import hashlib
import datetime
import sqlite3
import os
import secrets
import json
import logging
from flask_cors import CORS

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("blog_automation_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # CORS 허용

# 데이터베이스 이름
DB_NAME = 'blog_serials.db'

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS blog_serials
    (serial_number TEXT PRIMARY KEY, 
     activation_date TEXT,
     expiry_date TEXT,
     status TEXT DEFAULT '사용가능',
     device_info TEXT,
     memo TEXT DEFAULT '',
     activation_count INTEGER DEFAULT 0,
     is_blacklisted INTEGER DEFAULT 0,
     is_deleted INTEGER DEFAULT 0,
     created_date TEXT)
    ''')
    conn.commit()
    conn.close()
    logger.info("데이터베이스 초기화 완료")

# 시리얼 생성 및 등록 엔드포인트
@app.route('/api/serial/register', methods=['POST'])
def register_serial():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "요청 데이터가 없습니다."}), 400
        
        serial_number = data.get('serial_number')
        expiry_date = data.get('expiry_date')
        memo = data.get('memo', '')
        device_info = data.get('device_info', {})
        
        if not serial_number or not expiry_date:
            return jsonify({"success": False, "message": "필수 데이터가 누락되었습니다."}), 400
        
        # 디바이스 정보 JSON 문자열로 변환
        device_info_str = json.dumps(device_info, ensure_ascii=False)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 이미 존재하는 시리얼인지 확인
        c.execute("SELECT serial_number FROM blog_serials WHERE serial_number = ?", (serial_number,))
        if c.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "이미 존재하는 시리얼 번호입니다."}), 409
        
        # 현재 날짜/시간
        now = datetime.datetime.now().isoformat()
        
        # 데이터베이스에 저장
        c.execute('''
            INSERT INTO blog_serials 
            (serial_number, expiry_date, memo, device_info, created_date, activation_date, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (serial_number, expiry_date, memo, device_info_str, now, None, '사용가능'))
        
        conn.commit()
        conn.close()
        
        logger.info(f"새 시리얼 등록: {serial_number}, 만료일: {expiry_date}")
        return jsonify({"success": True, "message": "시리얼이 성공적으로 등록되었습니다."})
    
    except Exception as e:
        logger.error(f"시리얼 등록 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}"}), 500

# 대체 API 엔드포인트 (기존 /api/register와 동일하게 동작)
@app.route('/api/serials', methods=['POST'])
def create_serial():
    return register_serial()

# 특정 시리얼 번호 조회
@app.route('/api/serial/<serial_number>', methods=['GET'])
def get_serial(serial_number):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('''
            SELECT serial_number, status, created_date, expiry_date, 
                  device_info, memo, activation_count, is_blacklisted 
            FROM blog_serials 
            WHERE serial_number = ? AND is_deleted = 0
        ''', (serial_number,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"success": False, "message": "시리얼을 찾을 수 없습니다."}), 404
        
        serial_data = {
            "serial_number": row[0],
            "status": row[1],
            "created_date": row[2],
            "expiry_date": row[3],
            "device_info": json.loads(row[4]) if row[4] else {},
            "memo": row[5],
            "activation_count": row[6],
            "is_blacklisted": bool(row[7])
        }
        
        return jsonify(serial_data)
    
    except Exception as e:
        logger.error(f"시리얼 조회 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}"}), 500

# 모든 시리얼 조회
@app.route('/api/serials', methods=['GET'])
def get_all_serials():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('''
            SELECT serial_number, status, created_date, expiry_date, 
                  device_info, memo, activation_count, is_blacklisted 
            FROM blog_serials 
            WHERE is_deleted = 0
            ORDER BY created_date DESC
        ''')
        
        rows = c.fetchall()
        conn.close()
        
        serials = []
        for row in rows:
            serial_data = {
                "serial_number": row[0],
                "status": row[1],
                "created_date": row[2],
                "expiry_date": row[3],
                "device_info": json.loads(row[4]) if row[4] else {},
                "memo": row[5],
                "activation_count": row[6],
                "is_blacklisted": bool(row[7])
            }
            serials.append(serial_data)
        
        return jsonify({"serials": serials})
    
    except Exception as e:
        logger.error(f"시리얼 목록 조회 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}"}), 500

# 시리얼 상태 업데이트
@app.route('/api/serials/<serial_number>', methods=['PATCH'])
def update_serial(serial_number):
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "요청 데이터가 없습니다."}), 400
        
        status = data.get('status')
        expiry_date = data.get('expiry_date')
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 존재하는 시리얼인지 확인
        c.execute("SELECT serial_number FROM blog_serials WHERE serial_number = ? AND is_deleted = 0", (serial_number,))
        if not c.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "시리얼을 찾을 수 없습니다."}), 404
        
        # 업데이트 쿼리 구성
        update_fields = []
        params = []
        
        if status:
            update_fields.append("status = ?")
            params.append(status)
        
        if expiry_date:
            update_fields.append("expiry_date = ?")
            params.append(expiry_date)
        
        if not update_fields:
            conn.close()
            return jsonify({"success": False, "message": "업데이트할 내용이 없습니다."}), 400
        
        # 쿼리 실행
        query = f"UPDATE blog_serials SET {', '.join(update_fields)} WHERE serial_number = ?"
        params.append(serial_number)
        
        c.execute(query, params)
        conn.commit()
        conn.close()
        
        logger.info(f"시리얼 업데이트: {serial_number}, 상태: {status if status else '변경 없음'}")
        return jsonify({"success": True, "message": "시리얼이 성공적으로 업데이트되었습니다."})
    
    except Exception as e:
        logger.error(f"시리얼 업데이트 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}"}), 500

# 블랙리스트 관리
@app.route('/api/blacklist', methods=['POST'])
def manage_blacklist():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "요청 데이터가 없습니다."}), 400
        
        serial_number = data.get('serial_number')
        action = data.get('action')  # 'add' 또는 'remove'
        
        if not serial_number or not action:
            return jsonify({"success": False, "message": "필수 데이터가 누락되었습니다."}), 400
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 시리얼 존재 확인
        c.execute("SELECT serial_number FROM blog_serials WHERE serial_number = ? AND is_deleted = 0", (serial_number,))
        if not c.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "시리얼을 찾을 수 없습니다."}), 404
        
        if action == 'add':
            # 블랙리스트 추가
            c.execute('''
                UPDATE blog_serials 
                SET is_blacklisted = 1, status = '블랙리스트'
                WHERE serial_number = ?
            ''', (serial_number,))
            message = "시리얼이 블랙리스트에 추가되었습니다."
        elif action == 'remove':
            # 블랙리스트 해제
            c.execute('''
                UPDATE blog_serials 
                SET is_blacklisted = 0
                WHERE serial_number = ?
            ''', (serial_number,))
            
            # 만료일 기준으로 상태 결정
            c.execute('''
                UPDATE blog_serials 
                SET status = CASE 
                    WHEN date(expiry_date) < date('now') THEN '만료됨'
                    WHEN date(expiry_date) <= date('now', '+7 days') THEN '만료 예정'
                    ELSE '사용가능' 
                END
                WHERE serial_number = ?
            ''', (serial_number,))
            
            message = "시리얼이 블랙리스트에서 제거되었습니다."
        else:
            conn.close()
            return jsonify({"success": False, "message": "잘못된 작업입니다. 'add' 또는 'remove'를 사용하세요."}), 400
        
        conn.commit()
        conn.close()
        
        logger.info(f"블랙리스트 {action}: {serial_number}")
        return jsonify({"success": True, "message": message})
    
    except Exception as e:
        logger.error(f"블랙리스트 관리 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}"}), 500

# 서버 상태 확인 엔드포인트
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})

# 시리얼 검증 엔드포인트
@app.route('/api/validate', methods=['POST'])
def validate_serial():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "요청 데이터가 없습니다.", "status": "오류"}), 400
        
        serial_number = data.get('serial_number')
        device_info = data.get('device_info', {})
        
        if not serial_number:
            return jsonify({"success": False, "message": "시리얼 번호가 누락되었습니다.", "status": "오류"}), 400
        
        # 디바이스 정보 JSON 문자열로 변환
        device_info_str = json.dumps(device_info, ensure_ascii=False) if device_info else None
        
        # 디바이스 해시 생성 (장치 식별용)
        device_hash = None
        if device_info:
            try:
                # 장치 고유 식별을 위한 해시 생성
                hash_data = (
                    f"{device_info.get('hostname', '')}|"
                    f"{device_info.get('ip_address', '')}|"
                    f"{device_info.get('system_model', '')}|"
                    f"{device_info.get('processor', '')}|"
                    f"{device_info.get('total_memory', '')}"
                )
                device_hash = hashlib.sha256(hash_data.encode()).hexdigest()
                logger.info(f"생성된 디바이스 해시: {device_hash[:10]}...")
            except Exception as hash_error:
                logger.error(f"디바이스 해시 생성 오류: {str(hash_error)}")
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 시리얼 번호 조회
        c.execute('''
            SELECT serial_number, status, expiry_date, device_info, is_blacklisted 
            FROM blog_serials 
            WHERE serial_number = ? AND is_deleted = 0
        ''', (serial_number,))
        
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "message": "시리얼을 찾을 수 없습니다.", "status": "등록되지 않음"}), 404
        
        db_serial, db_status, db_expiry, db_device_info, is_blacklisted = row
        
        # 블랙리스트 확인
        if is_blacklisted:
            conn.close()
            return jsonify({
                "success": False, 
                "message": "이 시리얼은 블랙리스트 처리되었습니다.", 
                "status": "블랙리스트"
            }), 403
        
        # 만료일 확인
        current_date = datetime.datetime.now().date()
        expiry_date = datetime.datetime.strptime(db_expiry, "%Y-%m-%d").date() if db_expiry else None
        
        if not expiry_date or expiry_date < current_date:
            # 시리얼이 만료되었음
            c.execute(
                "UPDATE blog_serials SET status = ? WHERE serial_number = ?", 
                ("만료됨", serial_number)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": False, 
                "message": "시리얼이 만료되었습니다.", 
                "expiry_date": db_expiry,
                "status": "만료됨"
            }), 403
        
        # 만료 30일 이내인지 확인
        days_until_expiry = (expiry_date - current_date).days
        if days_until_expiry <= 30:
            # 만료 예정 상태 설정 (하지만 여전히 유효함)
            db_status = "만료 예정" 
        
        # 디바이스 정보 비교 및 업데이트
        stored_device_hash = None
        if db_device_info:
            try:
                # 저장된 디바이스 정보에서 해시 추출 또는 계산
                stored_device = json.loads(db_device_info)
                hash_data = (
                    f"{stored_device.get('hostname', '')}|"
                    f"{stored_device.get('ip_address', '')}|"
                    f"{stored_device.get('system_model', '')}|"
                    f"{stored_device.get('processor', '')}|"
                    f"{stored_device.get('total_memory', '')}"
                )
                stored_device_hash = hashlib.sha256(hash_data.encode()).hexdigest()
            except Exception as e:
                logger.error(f"저장된 디바이스 정보 파싱 오류: {str(e)}")
        
        # 디바이스 제한 검사
        if db_status == "사용중" and db_device_info and device_hash and stored_device_hash != device_hash:
            # 다른 디바이스에서 이미 사용 중인 시리얼
            conn.close()
            return jsonify({
                "success": False, 
                "message": "이 시리얼은 다른 디바이스에서 이미 사용 중입니다.", 
                "status": "사용중",
                "expiry_date": db_expiry
            }), 403
        
        # 상태 업데이트 (새 디바이스 등록 또는 상태 유지)
        new_status = "사용중"  # 기본적으로 사용중으로 설정
        
        # 만료 예정 상태 유지
        if days_until_expiry <= 30:
            new_status = "만료 예정"
            
        # 디바이스 정보와 상태 업데이트
        c.execute('''
            UPDATE blog_serials 
            SET status = ?, device_info = ?, activation_count = activation_count + 1 
            WHERE serial_number = ?
        ''', (new_status, device_info_str, serial_number))
        
        conn.commit()
        conn.close()
        
        logger.info(f"시리얼 검증 성공: {serial_number}, 상태: {new_status}")
        
        return jsonify({
            "success": True,
            "message": "시리얼이 성공적으로 검증되었습니다.",
            "serial_number": serial_number,
            "status": new_status,
            "expiry_date": db_expiry
        })
        
    except Exception as e:
        logger.error(f"시리얼 검증 중 오류: {str(e)}")
        return jsonify({"success": False, "message": f"오류가 발생했습니다: {str(e)}", "status": "오류"}), 500

# 메인 실행 코드
if __name__ == '__main__':
    # 데이터베이스 초기화
    init_db()
    # 서버 시작
    app.run(host='0.0.0.0', port=5000, debug=True) 