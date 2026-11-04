# -*- coding: utf-8 -*-
"""用户 / 登录接口封装（对应 Mock 服务）"""
from api.base_api import BaseApi


class UserApi(BaseApi):
    site = "mock"

    # ---------- 认证 ----------
    def login(self, username=None, password=None):
        """POST /api/login
        成功: 200 {"token", "user", "expires_in"}
        缺参数: 400 / 账号错误: 401
        """
        payload = {}
        if username is not None:
            payload["username"] = username
        if password is not None:
            payload["password"] = password
        return self.post("/api/login", json=payload)

    def logout(self):
        """POST /api/logout"""
        return self.post("/api/logout")

    def me(self):
        """GET /api/me  需要 token"""
        return self.get("/api/me")

    # ---------- 用户 CRUD ----------
    def list_users(self, page=1, size=2):
        """GET /api/users?page=&size="""
        return self.get("/api/users", params={"page": page, "size": size})

    def get_user(self, user_id):
        """GET /api/users/{id}"""
        return self.get(f"/api/users/{user_id}")

    def create_user(self, username, email, role=None):
        """POST /api/users  需要管理员 token"""
        payload = {"username": username, "email": email}
        if role:
            payload["role"] = role
        return self.post("/api/users", json=payload)

    def update_user(self, user_id, **fields):
        """PUT /api/users/{id}  全量更新"""
        return self.put(f"/api/users/{user_id}", json=fields)

    def patch_user(self, user_id, **fields):
        """PATCH /api/users/{id}  局部更新"""
        return self.patch(f"/api/users/{user_id}", json=fields)

    def delete_user(self, user_id):
        """DELETE /api/users/{id}"""
        return self.delete(f"/api/users/{user_id}")

    # ---------- 健康检查 ----------
    def health(self):
        """GET /health  确认被测服务存活"""
        return self.get("/health")
