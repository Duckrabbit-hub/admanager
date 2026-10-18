#!/bin/bash
cd "$(dirname "$0")"
echo "ติดตั้งโปรแกรมยิงแอด (AdShooter) ..."

if ! command -v python3 &> /dev/null; then
    echo "ไม่พบ Python 3 ในเครื่องนี้ — ไปดาวน์โหลดและติดตั้งจาก https://www.python.org/downloads/ ก่อน"
    read -p "กด Enter เพื่อปิดหน้าต่างนี้..."
    exit 1
fi

if [ ! -d venv ]; then
    echo "สร้าง virtual environment ..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "ติดตั้งไลบรารีที่ต้องใช้ ..."
pip install --disable-pip-version-check -q -r requirements.txt

# ลองติดตั้งไลบรารีสำหรับเปิดเป็นหน้าต่างแอปของตัวเอง — ถ้าติดตั้งไม่สำเร็จ โปรแกรมจะ fallback
# ไปเปิดด้วยเบราว์เซอร์ปกติให้เองอัตโนมัติ ไม่กระทบการใช้งาน
pip install --disable-pip-version-check -q -r requirements-desktop-mac.txt || true

if [ ! -f data/campaigns.json ]; then
    echo "สร้างข้อมูลตัวอย่างให้ดูก่อน ..."
    python3 seed_demo_data.py
fi

echo "ติดตั้งเสร็จแล้ว! เปิดโปรแกรม ..."
python3 desktop.py
read -p "กด Enter เพื่อปิดหน้าต่างนี้..."
