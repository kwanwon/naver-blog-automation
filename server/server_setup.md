# 네이버 블로그 자동화 도구 서버 구축 가이드

이 문서는 네이버 블로그 자동화 도구의 업데이트 배포 및 사용자 관리를 위한 서버 구축 방법을 설명합니다.

## 목차

1. [서버 요구사항](#서버-요구사항)
2. [웹 서버 설정](#웹-서버-설정)
3. [업데이트 배포 시스템](#업데이트-배포-시스템)
4. [사용자 관리 시스템](#사용자-관리-시스템)
5. [보안 설정](#보안-설정)
6. [백업 및 복구](#백업-및-복구)

## 서버 요구사항

### 최소 사양
- **운영체제**: Ubuntu 22.04 LTS 또는 Debian 11
- **CPU**: 2 코어
- **RAM**: 4GB
- **저장 공간**: 40GB SSD
- **네트워크**: 100Mbps 인터넷 연결, 고정 IP 권장

### 클라우드 서비스 옵션
- **AWS**: EC2 t3.small 인스턴스
- **Google Cloud**: e2-standard-2 인스턴스
- **Oracle Cloud**: VM.Standard.E2.1
- **Azure**: B2s 인스턴스

## 웹 서버 설정

### Nginx 웹 서버 설치

```bash
sudo apt update
sudo apt install nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### SSL 인증서 설정 (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 기본 웹 서버 설정

```
# /etc/nginx/sites-available/naver-blog-automation
server {
    listen 80;
    server_name yourdomain.com;
    
    # HTTP를 HTTPS로 리디렉션
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    
    # 업데이트 파일 서빙
    location /downloads/ {
        alias /var/www/naver-blog-automation/downloads/;
        autoindex off;
    }
    
    # API 엔드포인트로 요청 전달
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 정적 파일 서빙 (관리자 웹 페이지)
    location / {
        root /var/www/naver-blog-automation/admin;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

## 업데이트 배포 시스템

### 1. Flask API 서버 설정

업데이트 확인 및 사용자 인증을 처리할 API 서버를 구축합니다.

**Flask 앱 설치**

```bash
sudo apt install python3-pip python3-venv
cd /var/www/naver-blog-automation
python3 -m venv venv
source venv/bin/activate
pip install flask flask-restful flask-sqlalchemy gunicorn
```

**API 서버 코드 예시 (app.py)**

```python
from flask import Flask, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['DOWNLOAD_FOLDER'] = '/var/www/naver-blog-automation/downloads'
db = SQLAlchemy(app)

# 사용자 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    api_key = db.Column(db.String(40), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 버전 모델
class Version(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    release_notes = db.Column(db.Text)
    is_latest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 업데이트 체크 API
@app.route('/api/check_update', methods=['GET'])
def check_update():
    current_version = request.args.get('version', '0.0.0')
    latest_version = Version.query.filter_by(is_latest=True).first()
    
    if not latest_version:
        return jsonify({'status': 'no_update', 'message': '업데이트 정보가 없습니다.'})
    
    # 버전 비교 로직
    current_parts = [int(p) for p in current_version.split('.')]
    latest_parts = [int(p) for p in latest_version.version.split('.')]
    
    need_update = False
    for i in range(max(len(current_parts), len(latest_parts))):
        current_part = current_parts[i] if i < len(current_parts) else 0
        latest_part = latest_parts[i] if i < len(latest_parts) else 0
        
        if latest_part > current_part:
            need_update = True
            break
        elif latest_part < current_part:
            need_update = False
            break
    
    if need_update:
        return jsonify({
            'status': 'update_available',
            'version': latest_version.version,
            'download_url': f'/api/download/{latest_version.version}',
            'release_notes': latest_version.release_notes
        })
    else:
        return jsonify({'status': 'no_update', 'message': '이미 최신 버전을 사용 중입니다.'})

# 다운로드 API
@app.route('/api/download/<version>', methods=['GET'])
def download(version):
    # API 키 인증 (선택 사항)
    api_key = request.args.get('api_key')
    if api_key:
        user = User.query.filter_by(api_key=api_key, is_active=True).first()
        if not user:
            return jsonify({'error': '잘못된 API 키입니다.'}), 403
    
    version_info = Version.query.filter_by(version=version).first()
    if not version_info:
        return jsonify({'error': '해당 버전을 찾을 수 없습니다.'}), 404
    
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], version_info.filename)
    if not os.path.exists(file_path):
        return jsonify({'error': '다운로드 파일을 찾을 수 없습니다.'}), 404
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
```

**Gunicorn 서비스 설정**

```bash
sudo nano /etc/systemd/system/naver-blog-api.service
```

파일 내용:
```
[Unit]
Description=Naver Blog Automation API Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/naver-blog-automation
Environment="PATH=/var/www/naver-blog-automation/venv/bin"
ExecStart=/var/www/naver-blog-automation/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable naver-blog-api
sudo systemctl start naver-blog-api
```

### 2. GitHub Actions를 통한 자동 배포

`.github/workflows/release.yml` 파일을 만들어 GitHub Actions를 통해 릴리즈를 자동화합니다.

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'  # v로 시작하는 태그 (v1.0.0 등)

jobs:
  build:
    runs-on: macos-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2
        
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller
          
      - name: Build macOS app
        run: |
          python build.py
          python create_installer.py
          
      - name: Create Release
        id: create_release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            installer/네이버블로그자동화-*.dmg
          draft: false
          prerelease: false
          body_path: CHANGELOG.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Upload to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USERNAME }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          source: "installer/네이버블로그자동화-*.dmg"
          target: "/var/www/naver-blog-automation/downloads/"
          strip_components: 1
```

## 사용자 관리 시스템

### 1. 사용자 관리 웹 인터페이스

**관리자 웹 대시보드 설정**

Flask 앱에 추가할 관리자 라우트:

```python
@app.route('/api/admin/users', methods=['GET'])
def list_users():
    # 관리자 인증 필요
    if not is_admin(request):
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    users = User.query.all()
    return jsonify({
        'users': [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat()
            }
            for user in users
        ]
    })

@app.route('/api/admin/users', methods=['POST'])
def create_user():
    # 관리자 인증 필요
    if not is_admin(request):
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not (username and email and password):
        return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
    
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': '이미 존재하는 사용자 이름 또는 이메일입니다.'}), 400
    
    user = User(username=username, email=email)
    user.set_password(password)
    user.api_key = generate_api_key()
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'api_key': user.api_key,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat()
    }), 201
```

### 2. 사용자 인증 및 라이선스 관리

**라이선스 관리 시스템**

```python
# 라이선스 모델
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    license_key = db.Column(db.String(40), unique=True, nullable=False)
    activation_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('licenses', lazy=True))

# 라이선스 확인 API
@app.route('/api/verify_license', methods=['POST'])
def verify_license():
    data = request.json
    license_key = data.get('license_key')
    machine_id = data.get('machine_id')
    
    if not (license_key and machine_id):
        return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
    
    license = License.query.filter_by(license_key=license_key, is_active=True).first()
    if not license:
        return jsonify({'valid': False, 'message': '유효하지 않은 라이선스 키입니다.'}), 200
    
    # 라이선스 만료 확인
    now = datetime.datetime.utcnow()
    if license.expiration_date and now > license.expiration_date:
        return jsonify({'valid': False, 'message': '라이선스가 만료되었습니다.'}), 200
    
    # 기기 인증 처리
    # (실제 구현 시 기기 ID 관리 로직 추가)
    
    return jsonify({
        'valid': True,
        'username': license.user.username,
        'expiration_date': license.expiration_date.isoformat() if license.expiration_date else None
    }), 200
```

## 보안 설정

### 1. 방화벽 설정 (UFW)

```bash
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### 2. 정기 업데이트 설정

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

### 3. Fail2ban 설치

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 백업 및 복구

### 1. 자동 백업 스크립트

`/var/www/naver-blog-automation/scripts/backup.sh` 파일 생성:

```bash
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_DIR="/var/backups/naver-blog-automation"
APP_DIR="/var/www/naver-blog-automation"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
sqlite3 $APP_DIR/app.db .dump > $BACKUP_DIR/app-$TIMESTAMP.sql

# 앱 파일 백업
tar -czf $BACKUP_DIR/app-files-$TIMESTAMP.tar.gz $APP_DIR/downloads $APP_DIR/config

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -name "*.sql" -type f -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -type f -mtime +30 -delete

# 외부 스토리지로 복사 (선택 사항)
# rsync -avz $BACKUP_DIR user@remote-server:/path/to/backup
```

스크립트에 실행 권한 부여:
```bash
sudo chmod +x /var/www/naver-blog-automation/scripts/backup.sh
```

크론 작업 추가:
```bash
sudo crontab -e
```

내용 추가:
```
0 2 * * * /var/www/naver-blog-automation/scripts/backup.sh
```

### 2. 복구 절차

1. 데이터베이스 복원:
```bash
sqlite3 /var/www/naver-blog-automation/app.db < /var/backups/naver-blog-automation/app-XXXXXXXX-XXXXXX.sql
```

2. 파일 복원:
```bash
tar -xzf /var/backups/naver-blog-automation/app-files-XXXXXXXX-XXXXXX.tar.gz -C /var/www/naver-blog-automation/
```

3. 서비스 재시작:
```bash
sudo systemctl restart naver-blog-api
sudo systemctl restart nginx
```

## 모니터링 및 로깅

### 1. Grafana + Prometheus 설정 (선택 사항)

1. Prometheus와 Grafana 설치:
```bash
sudo apt install prometheus grafana
```

2. API 서버 모니터링을 위한 Prometheus 엔드포인트 추가

3. Grafana 대시보드 설정

### 2. 로그 모니터링

로그 모니터링을 위한 Loki 및 Promtail 설정 (선택 사항)

---

이 문서는 기본적인 서버 설정 가이드입니다. 실제 구현 시 환경에 맞게 조정하세요. 