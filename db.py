"""db.py — ที่เก็บข้อมูลถาวรแบบ key-value บน Postgres (Supabase) สำหรับโหมดเว็บ/deploy

ปัญหาที่แก้: เดิมโปรแกรมเก็บข้อมูลเป็นไฟล์ JSON บนดิสก์ของเซิร์ฟเวอร์ (data/*.json) ซึ่งถ้า deploy
บน Render แพลนฟรี ดิสก์ไม่ถาวร -> ข้อมูลหายทุกครั้งที่ redeploy/restart ไฟล์นี้เปลี่ยนที่เก็บจากดิสก์
มาเป็นฐานข้อมูล Postgres ถาวรแทน โดยใช้วิธีง่ายที่สุดที่ปลอดภัยและพอกับขนาดงานนี้: เก็บทั้งไฟล์ (list/dict)
เป็น "1 แถว" ต่อ "1 คีย์" ในตาราง kv_store คอลัมน์ value เป็น JSONB เก็บข้อมูลทั้งก้อนเหมือนไฟล์ JSON เดิม
ทำให้โค้ดส่วน business logic ที่จัดการ list/dict ในหน่วยความจำ (storage.py, config.py, inbox.py,
automation.py) ไม่ต้องแก้โครงสร้างเลย — เปลี่ยนแค่ "load/save" ให้อ่าน-เขียนฐานข้อมูลแทนไฟล์

ถ้าไม่ได้ตั้งค่า DATABASE_URL ไว้ (เช่นตอนรันโหมด desktop ในเครื่องผู้ใช้เอง) available() จะเป็น False
แล้วโค้ดที่เรียกใช้จะ fallback ไปใช้ไฟล์ JSON ในเครื่องเหมือนเดิมทุกจุด — โหมด desktop จึงยังทำงานได้
โดยไม่ต้องพึ่งอินเทอร์เน็ต/ฐานข้อมูลภายนอกเลย
"""
import os
import threading

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

_pool = None
_pool_lock = threading.Lock()
_schema_ready = False
_schema_lock = threading.Lock()


def available():
    """มี DATABASE_URL ตั้งไว้ไหม (ถ้าไม่มี แปลว่าใช้โหมดไฟล์ JSON ในเครื่องแทน)"""
    return bool(DATABASE_URL)


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                import psycopg2.pool
                # เว็บรัน gunicorn --workers 1 --threads 4 ดังนั้น connection แค่ไม่กี่ตัวก็พอ
                # ไม่ fix sslmode ตรงนี้ — ปล่อยให้ psycopg2 "prefer" ตามค่า default (ใช้ SSL เองถ้าเซิร์ฟเวอร์รองรับ
                # เช่น Supabase, และต่อแบบไม่เข้ารหัสได้ถ้าเป็น Postgres ในเครื่องตอนทดสอบ)
                _pool = psycopg2.pool.ThreadedConnectionPool(1, 5, DATABASE_URL)
    return _pool


def _ensure_schema(conn):
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        conn.commit()
        _schema_ready = True


def get(key, default=None):
    """อ่านค่า (list/dict) ที่เก็บไว้ภายใต้ key นี้ คืนค่า default ถ้ายังไม่มี"""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM kv_store WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row is not None else default
    finally:
        pool.putconn(conn)


def set(key, value):
    """บันทึกค่า (list/dict) ทับของเดิมทั้งก้อนภายใต้ key นี้ (เหมือนเขียนไฟล์ JSON ทับ)"""
    from psycopg2.extras import Json

    pool = _get_pool()
    conn = pool.getconn()
    try:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO kv_store (key, value, updated_at) VALUES (%s, %s, now())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                """,
                (key, Json(value)),
            )
        conn.commit()
    finally:
        pool.putconn(conn)


def exists(key):
    """มีแถวนี้อยู่ในฐานข้อมูลแล้วหรือยัง (ใช้แยกแยะ 'ยังไม่เคยสร้าง' กับ 'สร้างแล้วแต่เป็น list ว่าง')"""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM kv_store WHERE key = %s", (key,))
            return cur.fetchone() is not None
    finally:
        pool.putconn(conn)
