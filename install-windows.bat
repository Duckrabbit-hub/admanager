@echo off
cd /d "%~dp0"
echo ติดตั้งโปรแกรมยิงแอด (AdShooter) ...

where python >nul 2>nul
if errorlevel 1 (
    echo ไม่พบ Python ในเครื่องนี้ — ไปดาวน์โหลดและติดตั้งจาก https://www.python.org/downloads/ ก่อน
    echo ตอนติดตั้ง อย่าลืมติ๊กช่อง "Add Python to PATH" ด้วย
    pause
    exit /b 1
)

if not exist venv (
    echo สร้าง virtual environment ...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo ติดตั้งไลบรารีที่ต้องใช้ ...
pip install --disable-pip-version-check -q -r requirements.txt

if not exist data\campaigns.json (
    echo สร้างข้อมูลตัวอย่างให้ดูก่อน ...
    python seed_demo_data.py
)

echo ติดตั้งเสร็จแล้ว! เปิดโปรแกรม ...
python desktop.py
pause
