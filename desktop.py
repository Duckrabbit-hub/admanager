"""desktop.py — ตัวเปิดโปรแกรมแบบเดสก์ท็อป (ใช้งานบนเครื่องตัวเองได้โดยไม่ต้อง deploy)

รัน Flask server ใน background thread -> รอจนตอบ HTTP จริง (`_http_ready`, เช็คด้วยการยิง request จริง
ไม่ใช่แค่เช็คว่า port เปิด) -> เปิดหน้าต่างให้ผู้ใช้ (เบราว์เซอร์ปกติ หรือหน้าต่างแอปของตัวเองถ้าทำได้)

**ข้อจำกัดสำคัญ**: ฟีเจอร์ "กล่องข้อความ" แบบเรียลไทม์ผ่าน Facebook webhook ใช้ไม่ได้ตอนรันแบบเดสก์ท็อปล้วน ๆ
แบบนี้ เพราะ Facebook ต้องส่งข้อมูลเข้ามาที่ URL ที่เป็นสาธารณะผ่าน HTTPS (เครื่องส่วนตัวไม่มี URL แบบนั้น)
ส่วนฟังก์ชันยิงแอด/วิเคราะห์ประสิทธิภาพ/ระบบอัตโนมัติ และกล่องข้อความแบบดูข้อมูลที่มีอยู่ ใช้งานได้ตามปกติทุกอย่าง
ถ้าต้องการกล่องข้อความเรียลไทม์ด้วย ให้ deploy ขึ้นที่มี public HTTPS URL ตาม README.md/DEPLOY.md/
DEPLOY-FREE.md แทน

บังคับโหมดหน้าต่างได้ด้วย env var ADSHOOTER_NATIVE_WINDOW=1 (บังคับหน้าต่างแอปของตัวเอง ต้องมี pywebview
ติดตั้งไว้) หรือ =0 (บังคับเปิดด้วยเบราว์เซอร์ปกติ) — ถ้าไม่ตั้งไว้ ค่าเริ่มต้นคือ: Windows/Linux ใช้เบราว์เซอร์
ปกติ (Chrome/Edge) เพราะ native window engine บางเครื่องมีปัญหากับซอฟต์แวร์ความปลอดภัย/proxy ขององค์กร
(ขึ้น ERR_EMPTY_RESPONSE), Mac ลองเปิดเป็นหน้าต่างแอปของตัวเองก่อน ถ้าไม่สำเร็จ fallback เป็นเบราว์เซอร์
ปกติให้อัตโนมัติ
"""
import logging
import os
import platform
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", 5000))
URL = f"http://{HOST}:{PORT}/"

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "adshooter.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("desktop")


def _http_ready(timeout=0.8):
    try:
        urllib.request.urlopen(URL, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True  # ตอบกลับมาแล้ว (ต่อให้เป็น redirect ไปหน้า login ก็ถือว่า server พร้อมใช้งานแล้ว)
    except Exception:
        return False


def _port_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, PORT)) == 0


def _run_server():
    sys.path.insert(0, BASE_DIR)
    try:
        import app as appmod  # นำเข้าตอนนี้ (ไม่ใช่ตอน import module) เพื่อให้ error ตอน import ถูก log ไว้แน่ ๆ
        appmod.app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    except Exception:
        log.exception("เซิร์ฟเวอร์หยุดทำงานเพราะ error")


def _wait_until_ready(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if _http_ready():
            return True
        time.sleep(0.3)
    return False


def _open_window():
    """เปิดหน้าต่างให้ผู้ใช้ คืนค่า True ถ้าเปิดเป็นหน้าต่างแอปของตัวเอง (ซึ่ง block จนกว่าผู้ใช้จะปิดหน้าต่าง)"""
    mode_env = os.environ.get("ADSHOOTER_NATIVE_WINDOW")
    if mode_env == "1":
        use_native = True
    elif mode_env == "0":
        use_native = False
    else:
        use_native = platform.system() == "Darwin"

    if use_native:
        try:
            import webview
            log.info("เปิดหน้าต่างแอปของตัวเอง (pywebview)")
            webview.create_window("โปรแกรมยิงแอด — AdShooter", URL, width=1280, height=820, min_size=(900, 600))
            webview.start()
            return True
        except Exception as e:
            log.warning("เปิดหน้าต่างแอปของตัวเองไม่สำเร็จ (%s) — เปลี่ยนไปใช้เบราว์เซอร์ปกติแทน", e)

    log.info("เปิดด้วยเบราว์เซอร์ปกติ: %s", URL)
    webbrowser.open(URL)
    return False


def main():
    log.info("=== เริ่มเปิดโปรแกรม (PID %s, platform %s) ===", os.getpid(), platform.platform())

    if _port_in_use() and _http_ready():
        log.info(
            "พบเซิร์ฟเวอร์เดิมที่พอร์ต %s อยู่แล้ว ใช้ตัวเดิมต่อเพื่อความเร็ว "
            "(ถ้าพึ่งอัปเดตโปรแกรมมาใหม่แล้วไม่เห็นเมนู/ฟีเจอร์ใหม่ ให้ปิดโปรเซส python ค้างเดิมผ่าน "
            "Task Manager (Windows) หรือ Activity Monitor (Mac) ก่อน แล้วเปิดโปรแกรมนี้ใหม่อีกครั้ง)",
            PORT,
        )
        already_running = True
    else:
        already_running = False
        threading.Thread(target=_run_server, name="flask-server", daemon=True).start()
        if not _wait_until_ready():
            msg = "เปิดโปรแกรมไม่สำเร็จ — ดูรายละเอียด error ได้ในไฟล์ adshooter.log ที่อยู่ข้าง ๆ โปรแกรมนี้"
            log.error(msg)
            print(msg)
            return

    print(f"โปรแกรมพร้อมใช้งานที่ {URL}")
    opened_native = _open_window()

    if opened_native:
        return  # webview.start() block จนผู้ใช้ปิดหน้าต่างไปแล้ว ไม่ต้องรออะไรเพิ่ม

    if already_running:
        return  # ใช้ server เดิมที่มีคนอื่น (หรือรอบก่อน) เปิดไว้อยู่แล้ว ไม่ต้องคุม lifecycle ของมัน

    print("กด Ctrl+C ในหน้าต่างนี้เพื่อหยุดโปรแกรม (ปิดแค่แท็บเบราว์เซอร์ โปรแกรมจะยังรันอยู่เบื้องหลัง)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("ผู้ใช้ปิดโปรแกรม (Ctrl+C)")
        print("ปิดโปรแกรมแล้ว")


if __name__ == "__main__":
    main()
