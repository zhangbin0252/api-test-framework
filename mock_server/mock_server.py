# -*- coding: utf-8 -*-
"""本地 Mock 服务：一个可完全掌控的被测系统

为什么要自建 Mock？
1. 外部公开测试站不稳定——黑马商城已下线（410）、reqres.in 有每日 40 次匿名限流、
   jsonplaceholder/dummyjson 会随机超时。依赖它们，测试结果就不可复现。
2. 真实工作中，接口测试要么对着公司测试环境跑，要么用 Mock 隔离第三方依赖。
   自己写一个 Mock 服务，等于把「被测系统」也掌握在手里，用例可以稳定复现。
3. 这个 Mock 是故意留了 Bug 的——这样「发现缺陷」才是真的发现，不是编的。

启动方式：
    python mock_server/mock_server.py
    默认 http://127.0.0.1:8899
"""
import json
import re
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8899

# ---------------- 内存数据 ----------------
USERS = {
    1: {"id": 1, "username": "alice", "email": "alice@example.com", "role": "admin", "status": "active"},
    2: {"id": 2, "username": "bob", "email": "bob@example.com", "role": "user", "status": "active"},
    3: {"id": 3, "username": "carol", "email": "carol@example.com", "role": "user", "status": "disabled"},
}
TOKENS = {}          # token -> user_id
NEXT_ID = [4]
LOCK = threading.Lock()

# 预置账号
ACCOUNTS = {
    "alice": "Alice@123",
    "bob": "Bob@12345",
}


def now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------- 工具方法 ----------
    def _send(self, code, payload=None, extra_headers=None):
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"__invalid_json__": raw.decode("utf-8", "ignore")}

    def _drain_body(self):
        """把请求体读完再返回响应

        HTTP/1.1 keep-alive 下，如果服务端没读完请求体就返回响应，
        残留的字节会被当成下一个请求的起始行，导致
        「Bad request syntax」——这是自研服务里非常典型的一个坑。
        所有会提前返回（401/403/400）的分支都必须先调用本方法。
        """
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            try:
                self.rfile.read(length)
            except Exception:
                pass

    def _auth_user(self):
        """从 Authorization 头解析当前用户；无效返回 None"""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:].strip()
        uid = TOKENS.get(token)
        if uid is None:
            return None
        return USERS.get(uid)

    def _serve_static(self, filename, content_type):
        """返回 static 目录下的静态页面（前端 UI）"""
        import os
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        full = os.path.join(base, filename)
        if not os.path.exists(full):
            return self._send(404, {"error": "page not found", "file": filename})
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # 静默，避免污染测试输出

    # ---------- 路由 ----------
    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        # ---- 前端页面（UI 自动化测试的对象）----
        if path in ("/", "/login.html", "/index.html"):
            return self._serve_static("login.html", "text/html; charset=utf-8")
        if path == "/app":
            return self._serve_static("index.html", "text/html; charset=utf-8")

        if path == "/health":
            return self._send(200, {"status": "ok", "time": now()})

        if path == "/api/login":
            return self._send(405, {"error": "Method Not Allowed", "hint": "登录请用 POST"})

        if path == "/api/users":
            return self._list_users(query)

        m = re.fullmatch(r"/api/users/(\d+)", path)
        if m:
            return self._get_user(int(m.group(1)))

        if path == "/api/me":
            user = self._auth_user()
            if user is None:
                return self._send(401, {"error": "unauthorized", "message": "缺少或无效的 token"})
            return self._send(200, {"data": user})

        return self._send(404, {"error": "not found", "path": path})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/login":
            return self._login()

        if path == "/api/logout":
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                TOKENS.pop(auth[7:].strip(), None)
            return self._send(200, {"message": "logged out"})

        if path == "/api/users":
            return self._create_user()

        return self._send(404, {"error": "not found", "path": path})

    def do_PUT(self):
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/users/(\d+)", path)
        if m:
            return self._update_user(int(m.group(1)), partial=False)
        return self._send(404, {"error": "not found", "path": path})

    def do_PATCH(self):
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/users/(\d+)", path)
        if m:
            return self._update_user(int(m.group(1)), partial=True)
        return self._send(404, {"error": "not found", "path": path})

    def do_DELETE(self):
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/users/(\d+)", path)
        if m:
            return self._delete_user(int(m.group(1)))
        return self._send(404, {"error": "not found", "path": path})

    # ---------- 业务实现 ----------
    def _login(self):
        body = self._read_json()
        username = body.get("username")
        password = body.get("password")

        # 参数校验
        if not username:
            return self._send(400, {"error": "username_required", "message": "用户名不能为空"})
        if not password:
            return self._send(400, {"error": "password_required", "message": "密码不能为空"})

        # 账号存在性
        if username not in ACCOUNTS:
            return self._send(401, {"error": "invalid_credentials", "message": "用户名或密码错误"})

        # ⚠️ 已知缺陷 BUG-001：密码错误时返回 500 而不是 401
        #    真实系统里这是「异常处理缺失」，接口测试应该能抓到
        if ACCOUNTS[username] != password:
            return self._send(500, {"error": "internal_error", "message": "服务器内部错误"})

        # 被禁用的用户（bob 正常，这里演示状态校验）
        for u in USERS.values():
            if u["username"] == username and u["status"] == "disabled":
                return self._send(403, {"error": "account_disabled", "message": "账号已被禁用"})

        token = "tok_" + uuid.uuid4().hex[:16]
        uid = next((u["id"] for u in USERS.values() if u["username"] == username), None)
        TOKENS[token] = uid
        return self._send(200, {
            "token": token,
            "user": {"id": uid, "username": username},
            "expires_in": 7200,
        })

    def _list_users(self, query):
        page = int(query.get("page", ["1"])[0])
        size = int(query.get("size", ["2"])[0])
        if page < 1:
            return self._send(400, {"error": "invalid_page", "message": "页码必须大于等于 1"})
        if size < 1 or size > 100:
            return self._send(400, {"error": "invalid_size", "message": "每页条数必须在 1-100 之间"})

        all_users = sorted(USERS.values(), key=lambda u: u["id"])
        total = len(all_users)
        start = (page - 1) * size
        items = all_users[start:start + size]
        return self._send(200, {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": (total + size - 1) // size,
            "data": items,
        })

    def _get_user(self, uid):
        user = USERS.get(uid)
        if user is None:
            return self._send(404, {"error": "user_not_found", "message": f"用户 {uid} 不存在"})

        # ⚠️ 已知缺陷 BUG-002：未做鉴权，未登录也能查询任意用户（越权）
        #    真实系统里这是水平越权漏洞，属于安全类缺陷
        return self._send(200, {"data": user})

    def _create_user(self):
        user = self._auth_user()
        if user is None:
            self._drain_body()
            return self._send(401, {"error": "unauthorized", "message": "请先登录"})
        if user["role"] != "admin":
            self._drain_body()
            return self._send(403, {"error": "forbidden", "message": "只有管理员可以创建用户"})

        body = self._read_json()
        username = (body.get("username") or "").strip()
        email = (body.get("email") or "").strip()

        if not username:
            return self._send(400, {"error": "username_required", "message": "用户名不能为空"})
        if not email:
            return self._send(400, {"error": "email_required", "message": "邮箱不能为空"})
        if "@" not in email:
            return self._send(400, {"error": "invalid_email", "message": "邮箱格式不正确"})
        if any(u["username"] == username for u in USERS.values()):
            return self._send(409, {"error": "duplicate_username", "message": "用户名已存在"})

        with LOCK:
            uid = NEXT_ID[0]
            NEXT_ID[0] += 1
            USERS[uid] = {
                "id": uid, "username": username, "email": email,
                "role": body.get("role", "user"), "status": "active",
            }
        return self._send(201, {"data": USERS[uid], "createdAt": now()})

    def _update_user(self, uid, partial):
        user = self._auth_user()
        if user is None:
            self._drain_body()
            return self._send(401, {"error": "unauthorized", "message": "请先登录"})

        target = USERS.get(uid)
        if target is None:
            self._drain_body()
            return self._send(404, {"error": "user_not_found", "message": f"用户 {uid} 不存在"})

        body = self._read_json()
        if not partial:
            # PUT 要求全量字段
            for f in ("username", "email"):
                if not body.get(f):
                    return self._send(400, {"error": "missing_field", "message": f"PUT 需要完整字段，缺少 {f}"})

        if "email" in body and "@" not in body["email"]:
            return self._send(400, {"error": "invalid_email", "message": "邮箱格式不正确"})

        for k in ("username", "email", "role", "status"):
            if k in body:
                target[k] = body[k]
        return self._send(200, {"data": target, "updatedAt": now()})

    def _delete_user(self, uid):
        user = self._auth_user()
        if user is None:
            self._drain_body()
            return self._send(401, {"error": "unauthorized", "message": "请先登录"})
        if user["role"] != "admin":
            self._drain_body()
            return self._send(403, {"error": "forbidden", "message": "只有管理员可以删除用户"})
        if uid not in USERS:
            self._drain_body()
            return self._send(404, {"error": "user_not_found", "message": f"用户 {uid} 不存在"})
        if uid == user["id"]:
            return self._send(400, {"error": "cannot_delete_self", "message": "不能删除自己"})

        del USERS[uid]
        return self._send(204, None)


def start_server(host=HOST, port=PORT):
    """在后台线程启动 Mock 服务，返回 server 对象"""
    server = ThreadingHTTPServer((host, port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


if __name__ == "__main__":
    srv = start_server()
    print(f"Mock 服务已启动: http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()
        print("\n已停止")

