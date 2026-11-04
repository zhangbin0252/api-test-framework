# -*- coding: utf-8 -*-
"""用户列表页（Page Object）

页面地址：/app  （即 index.html）
"""
from ui.base_page import BasePage


class UserListPage(BasePage):
    path = "/app"

    # ---------- 元素定位器 ----------
    CURRENT_USER = "#currentUser"
    CURRENT_ROLE = "#currentRole"
    LOGOUT_BTN = "#logoutBtn"
    REFRESH_BTN = "#refreshBtn"
    ADD_USER_BTN = "#addUserBtn"

    TABLE = "#userTable"
    TABLE_BODY = "#userTbody"
    TABLE_ROWS = "#userTbody tr"

    PREV_BTN = "#prevBtn"
    NEXT_BTN = "#nextBtn"
    PAGE_INFO = "#pageInfo"

    # 新建用户弹窗
    ADD_MODAL = "#addModal"
    NEW_USERNAME = "#newUsername"
    NEW_EMAIL = "#newEmail"
    NEW_ROLE = "#newRole"
    CONFIRM_ADD = "#confirmAdd"
    CANCEL_ADD = "#cancelAdd"
    MODAL_MSG = "#modalMsg"

    TOAST = "#toast"

    # ---------- 状态查询 ----------
    def get_current_user(self):
        return self.text_of(self.CURRENT_USER).strip()

    def get_current_role(self):
        return self.text_of(self.CURRENT_ROLE).strip()

    def get_page_info(self):
        return self.text_of(self.PAGE_INFO).strip()

    def get_row_count(self):
        """表格当前页的行数"""
        # 空状态时 tbody 里只有一行提示，需要排除
        rows = self.page.locator(self.TABLE_ROWS)
        n = rows.count()
        if n == 1:
            text = rows.nth(0).inner_text()
            if "暂无数据" in text or "加载" in text:
                return 0
        return n

    def get_usernames(self):
        """当前页所有用户名（第 2 列）"""
        return self.page.eval_on_selector_all(
            f"{self.TABLE_ROWS} td:nth-child(2)",
            "els => els.map(e => e.innerText.trim())",
        )

    def get_toast(self):
        """获取 toast 提示文本"""
        return self.text_of(self.TOAST).strip()

    # ---------- 操作 ----------
    def wait_loaded(self):
        """等待列表加载完成（表格里出现数据行或空提示）"""
        self.page.wait_for_function(
            """() => {
                const tbody = document.querySelector('#userTbody');
                if (!tbody) return false;
                const txt = tbody.innerText || '';
                return !txt.includes('加载中');
            }""",
            timeout=8000,
        )
        return self

    def click_next_page(self):
        self.click(self.NEXT_BTN, "下一页")
        self.wait_loaded()

    def click_prev_page(self):
        self.click(self.PREV_BTN, "上一页")
        self.wait_loaded()

    def click_refresh(self):
        self.click(self.REFRESH_BTN, "刷新")
        self.wait_loaded()

    def click_logout(self):
        self.click(self.LOGOUT_BTN, "退出登录")

    # ---------- 新建用户 ----------
    def open_add_modal(self):
        self.click(self.ADD_USER_BTN, "新建用户按钮")
        self.page.wait_for_selector(self.ADD_MODAL, state="visible", timeout=5000)

    def fill_new_user(self, username, email, role=None):
        if username is not None:
            self.fill(self.NEW_USERNAME, username, "新用户名输入框")
        if email is not None:
            self.fill(self.NEW_EMAIL, email, "新用户邮箱输入框")
        if role is not None:
            self.page.select_option(self.NEW_ROLE, role)

    def confirm_add(self):
        self.click(self.CONFIRM_ADD, "确定按钮")

    def cancel_add(self):
        self.click(self.CANCEL_ADD, "取消按钮")

    def get_modal_message(self):
        return self.text_of(self.MODAL_MSG).strip()

    def is_modal_open(self):
        return self.is_visible(self.ADD_MODAL, timeout=1000)

    # ---------- 行内操作 ----------
    def click_edit(self, user_id):
        self.click(f'tr[data-user-id="{user_id}"] .link-btn', f"编辑用户 {user_id}")

    def click_delete(self, user_id):
        self.click(f'tr[data-user-id="{user_id}"] .link-btn.danger', f"删除用户 {user_id}")
