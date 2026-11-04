# -*- coding: utf-8 -*-
"""用户列表页 UI 用例

覆盖：列表渲染、分页、新建用户、表单校验、退出登录、越权访问
"""
import allure
import pytest

from ui.login_page import LoginPage
from ui.user_list_page import UserListPage


@allure.feature("UI - 用户列表页")
class TestUserListUI:

    @allure.story("页面渲染")
    @allure.title("用户列表 - 登录后应显示当前用户与数据表格")
    def test_list_rendered(self, logged_in_page, ui_config):
        acc = ui_config["accounts"]["admin"]
        assert logged_in_page.get_current_user() == acc["username"]
        assert logged_in_page.get_current_role() == "管理员"
        assert logged_in_page.get_row_count() > 0, "表格应有数据行"

    @allure.story("页面渲染")
    @allure.title("用户列表 - 表头包含 ID / 用户名 / 邮箱 / 角色 / 状态 / 操作")
    def test_table_headers(self, logged_in_page):
        headers = logged_in_page.page.eval_on_selector_all(
            "#userTable thead th", "els => els.map(e => e.innerText.trim())"
        )
        for expected in ["ID", "用户名", "邮箱", "角色", "状态", "操作"]:
            assert expected in headers, f"表头缺少 {expected}，实际：{headers}"

    @allure.story("分页")
    @allure.title("用户列表 - 分页信息与翻页按钮状态正确")
    def test_pagination(self, logged_in_page):
        info = logged_in_page.get_page_info()
        assert "第 1 /" in info, f"分页信息不符：{info!r}"

        # 第一页时「上一页」应禁用
        assert logged_in_page.page.is_disabled(UserListPage.PREV_BTN), (
            "第 1 页时「上一页」应禁用"
        )

        # 翻到下一页
        logged_in_page.click_next_page()
        info2 = logged_in_page.get_page_info()
        assert "第 2 /" in info2, f"翻页后信息不符：{info2!r}"

    @allure.story("分页")
    @allure.title("用户列表 - 翻页后数据应变化")
    def test_pagination_data_changed(self, logged_in_page):
        first_page = logged_in_page.get_usernames()
        logged_in_page.click_next_page()
        second_page = logged_in_page.get_usernames()

        assert first_page != second_page, (
            f"翻页后数据应不同，两页都是：{first_page}"
        )

    @allure.story("新建用户")
    @allure.title("用户列表 - 新建用户弹窗可正常打开与取消")
    def test_add_modal_open_cancel(self, logged_in_page):
        logged_in_page.open_add_modal()
        assert logged_in_page.is_modal_open(), "弹窗应显示"

        logged_in_page.cancel_add()
        assert not logged_in_page.is_modal_open(), "点击取消后弹窗应关闭"

    @allure.story("新建用户")
    @allure.title("用户列表 - 新建用户时用户名为空，提示「用户名不能为空」")
    def test_add_empty_username(self, logged_in_page):
        logged_in_page.open_add_modal()
        logged_in_page.fill_new_user(None, "test@example.com")
        logged_in_page.confirm_add()
        logged_in_page.page.wait_for_timeout(300)

        msg = logged_in_page.get_modal_message()
        assert msg == "用户名不能为空", f"提示不符：{msg!r}"
        assert logged_in_page.is_modal_open(), "校验失败时弹窗不应关闭"

    @allure.story("新建用户")
    @allure.title("用户列表 - 新建用户时邮箱为空，提示「邮箱不能为空」")
    def test_add_empty_email(self, logged_in_page):
        logged_in_page.open_add_modal()
        logged_in_page.fill_new_user("newuser", "")
        logged_in_page.confirm_add()
        logged_in_page.page.wait_for_timeout(300)

        msg = logged_in_page.get_modal_message()
        assert msg == "邮箱不能为空", f"提示不符：{msg!r}"

    @allure.story("新建用户")
    @allure.title("用户列表 - 成功新建用户后列表应刷新并出现该用户")
    def test_add_user_success(self, logged_in_page):
        """新建用户后验证列表刷新

        注意：每页只显示 2 条，新用户 id 递增会排到最后一页。
        所以不能只断言第 1 页，要翻到最后一页去找——
        这是写 UI 用例时很容易忽略的分页陷阱。
        """
        import time
        uname = f"ui_{int(time.time() * 1000) % 100000}"

        logged_in_page.open_add_modal()
        logged_in_page.fill_new_user(uname, f"{uname}@example.com")
        logged_in_page.confirm_add()

        # 等待弹窗关闭
        logged_in_page.page.wait_for_selector(
            UserListPage.ADD_MODAL, state="hidden", timeout=5000
        )
        logged_in_page.wait_loaded()

        # 翻到最后一页找新用户
        found = False
        for _ in range(10):
            if uname in logged_in_page.get_usernames():
                found = True
                break
            info = logged_in_page.get_page_info()
            if "/" not in info:
                break
            cur, total = info.replace("第", "").replace("页", "").split("/")
            if int(cur.strip()) >= int(total.strip()):
                break
            logged_in_page.click_next_page()

        assert found, (
            f"新建的用户 {uname!r} 在列表所有页中都未找到"
        )

    @allure.story("退出登录")
    @allure.title("用户列表 - 退出登录后应回到登录页")
    def test_logout(self, logged_in_page):
        logged_in_page.click_logout()
        logged_in_page.page.wait_for_url(lambda url: "/app" not in url, timeout=8000)

        assert "/app" not in logged_in_page.page.url, (
            f"退出后应回到登录页，当前 URL：{logged_in_page.page.url}"
        )

    @allure.story("访问控制")
    @allure.title("用户列表 - 未登录直接访问 /app 应被踢回登录页")
    def test_unauthorized_access(self, user_list_page):
        """越权访问检查：未登录直接访问列表页

        前端通过检查 localStorage 里的 token 来拦截，
        但这只是「前端拦截」，真正的安全要靠后端——这正好呼应接口测试里的 BUG-002。
        """
        user_list_page.open()
        user_list_page.page.wait_for_timeout(800)

        assert "/app" not in user_list_page.page.url, (
            f"未登录访问 /app 应被重定向，当前 URL：{user_list_page.page.url}"
        )
