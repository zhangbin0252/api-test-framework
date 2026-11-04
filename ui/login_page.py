# -*- coding: utf-8 -*-
"""登录页（Page Object）

页面地址：/  （即 login.html）
"""
from ui.base_page import BasePage


class LoginPage(BasePage):
    path = "/"

    # ---------- 元素定位器（集中管理，页面改版只改这里）----------
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#loginBtn"
    MESSAGE = "#msg"
    TITLE = "h1"

    # ---------- 操作 ----------
    def input_username(self, username):
        self.fill(self.USERNAME_INPUT, username, "用户名输入框")

    def input_password(self, password):
        self.fill(self.PASSWORD_INPUT, password, "密码输入框")

    def click_login(self):
        self.click(self.LOGIN_BUTTON, "登录按钮")

    def login(self, username, password):
        """完整登录动作：填账号 → 填密码 → 点登录"""
        self.input_username(username)
        self.input_password(password)
        self.click_login()
        return self

    def login_expect_success(self, username, password):
        """登录并等待跳转到用户列表页"""
        self.login(username, password)
        self.wait_for_url("**/app")
        return self

    # ---------- 获取状态 ----------
    def get_message(self):
        """获取提示信息（成功 / 失败提示）"""
        return self.text_of(self.MESSAGE).strip()

    def get_page_title(self):
        return self.text_of(self.TITLE).strip()

    def is_message_error(self):
        """提示是否为错误样式（红色）"""
        return "err" in (self.page.get_attribute(self.MESSAGE, "class") or "")

    def is_message_success(self):
        """提示是否为成功样式（绿色）"""
        return "ok" in (self.page.get_attribute(self.MESSAGE, "class") or "")
