"""messaging/base.py — คลาสฐานสำหรับ connector กล่องข้อความ (แยกจาก connector ยิงแอด
เพราะใช้สิทธิ์/permission scope คนละชุด — pages_messaging แทน ads_management)

รูปแบบเดียวกับ connectors/base.py: live-with-fallback — ถ้า connector ไม่ได้ตั้งค่าไว้จริง
(ไม่มี token) การ "ส่งข้อความ" จะเป็นแค่การจำลอง (simulated) ไม่ได้ส่งไปหาลูกค้าจริง
ต้องบอกผู้ใช้ให้ชัดเจนเสมอว่าข้อความไหนส่งจริง/ข้อความไหนจำลอง กันเข้าใจผิดว่าตอบลูกค้าจริงไปแล้ว
"""


class MessagingConnector:
    platform = "base"

    def __init__(self, account=None):
        self.account = account or {}
        self.configured = False

    def _send_live(self, conversation, text):
        raise NotImplementedError

    def send_message(self, conversation, text):
        """คืน dict {"sent": True/False, "mode": "live"/"mock", "error": str|None}"""
        if self.configured:
            try:
                self._send_live(conversation, text)
                return {"sent": True, "mode": "live", "error": None}
            except Exception as e:
                return {"sent": False, "mode": "live_failed", "error": str(e)}
        return {"sent": False, "mode": "mock", "error": None}
