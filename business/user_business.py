# -*- coding: utf-8 -*-
"""业务层：把多个接口组合成一个完整业务动作

用例层只关心「我要测什么业务」，不关心底层要调几个接口、token 怎么传。
"""
from api.user_api import UserApi
from utils.yaml_util import read_yaml
from utils.logger_util import log


class UserBusiness:

    def __init__(self):
        self.api = UserApi()
        cfg = read_yaml("config/config.yaml")
        self.accounts = cfg["accounts"]

    # ---------- 登录 ----------
    def login(self, username, password):
        """执行登录并返回响应（不抛断言，交给用例层判断）"""
        log.info(f"业务流：登录 {username}")
        return self.api.login(username, password)

    def login_success(self, role="admin"):
        """登录成功并返回 token；失败直接抛异常"""
        acc = self.accounts[role]
        resp = self.api.login(acc["username"], acc["password"])
        assert resp.status_code == 200, f"登录失败：{resp.status_code} {resp.text}"
        token = resp.json().get("token")
        assert token, f"登录响应中没有 token：{resp.text}"
        return token

    def login_and_hold(self, role="admin"):
        """登录并把 token 写入会话头（会话保持），返回 token"""
        token = self.login_success(role)
        self.api.set_token(token)
        return token

    # ---------- 跨接口业务流 ----------
    def create_then_query(self, username, email):
        """创建用户 → 用返回 id 查询，验证「写后能读」的一致性"""
        created = self.api.create_user(username, email)
        assert created.status_code == 201, f"创建失败：{created.status_code} {created.text}"
        new_id = created.json()["data"]["id"]
        log.info(f"业务流：创建用户 id={new_id}，开始查询")
        queried = self.api.get_user(new_id)
        return created, queried

    def login_then_access_protected(self, username, password):
        """登录 → 带 token 访问受保护接口，验证鉴权链路"""
        login_resp = self.api.login(username, password)
        if login_resp.status_code != 200:
            return login_resp, None
        token = login_resp.json()["token"]
        self.api.set_token(token)
        me_resp = self.api.me()
        return login_resp, me_resp
