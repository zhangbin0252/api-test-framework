# -*- coding: utf-8 -*-
"""登录页 UI 用例

覆盖：页面元素、前端校验、登录成功、登录失败、密码错误（BUG-001）、跳转
"""
import allure
import pytest

from ui.login_page import LoginPage
from ui.user_list_page import UserListPage


@allure.feature("UI - 登录页")
class TestLoginUI:

    @allure.story("页面渲染")
    @allure.title("登录页 - 核心元素应正常渲染")
    def test_page_elements(self, login_page):
        assert "用户管理系统" in login_page.title(), "页面标题不符"
        login_page.assert_visible(LoginPage.USERNAME_INPUT, "用户名输入框")
        login_page.assert_visible(LoginPage.PASSWORD_INPUT, "密码输入框")
        login_page.assert_visible(LoginPage.LOGIN_BUTTON, "登录按钮")
        assert login_page.get_page_title() == "用户管理系统"

    @allure.story("前端校验")
    @allure.title("登录页 - 用户名和密码都不填，提示「请输入用户名」")
    def test_empty_form(self, login_page):
        login_page.click_login()
        login_page.page.wait_for_timeout(300)

        msg = login_page.get_message()
        assert msg == "请输入用户名", f"提示不符：{msg!r}"
        assert login_page.is_message_error(), "提示应为错误样式"

    @allure.story("前端校验")
    @allure.title("登录页 - 只填用户名不填密码，提示「请输入密码」")
    def test_only_username(self, login_page):
        login_page.input_username("alice")
        login_page.click_login()
        login_page.page.wait_for_timeout(300)

        msg = login_page.get_message()
        assert msg == "请输入密码", f"提示不符：{msg!r}"

    @allure.story("登录成功")
    @allure.title("登录页 - 管理员账号登录成功并跳转到用户列表")
    def test_login_success(self, login_page, ui_config):
        acc = ui_config["accounts"]["admin"]
        login_page.login_expect_success(acc["username"], acc["password"])

        login_page.assert_url_contains("/app", "应跳转到用户列表页")
        ulp = UserListPage(login_page.page, ui_config["base_url"])
        ulp.wait_loaded()
        assert ulp.get_current_user() == acc["username"], (
            f"当前用户不符：{ulp.get_current_user()!r}"
        )

    @allure.story("登录成功")
    @allure.title("登录页 - 普通用户登录成功，角色显示为「普通用户」")
    def test_login_normal_user(self, login_page, ui_config):
        acc = ui_config["accounts"]["normal"]
        login_page.login_expect_success(acc["username"], acc["password"])

        ulp = UserListPage(login_page.page, ui_config["base_url"])
        ulp.wait_loaded()
        assert ulp.get_current_user() == acc["username"]
        assert ulp.get_current_role() == "普通用户", (
            f"角色不符：{ulp.get_current_role()!r}"
        )

    @allure.story("登录失败")
    @allure.title("登录页 - 用户名不存在，提示登录失败")
    def test_login_wrong_username(self, login_page):
        login_page.login("not_exist_user", "whatever")
        login_page.page.wait_for_timeout(800)

        msg = login_page.get_message()
        assert msg == "用户名或密码错误", f"提示不符：{msg!r}"
        assert login_page.is_message_error()

    @allure.story("登录失败")
    @allure.title("登录页 - 密码错误应提示「用户名或密码错误」（BUG-001：实际显示系统异常）")
    @pytest.mark.xfail(
        reason="已知缺陷 BUG-001：服务端密码错误返回 500，前端提示「系统异常」而非「密码错误」",
        strict=True,
    )
    def test_login_wrong_password_bug001(self, login_page, ui_config):
        """这条用例对应服务端已知缺陷 BUG-001

        服务端在密码错误时返回 500，前端把 500 处理成「系统异常，请稍后重试」。
        用户看到的是系统故障，而不是「密码错了」——这是体验缺陷，也是缺陷单的实证。

        标 xfail 的原因同 test_auth.py::test_unauthorized_read_user：
        断言的是正确行为，缺陷在服务端，用一个 strict xfail 让它不污染流水线，
        同时保证缺陷修复后会立刻暴露。
        """
        acc = ui_config["accounts"]["admin"]
        login_page.login(acc["username"], "wrong_password")
        login_page.page.wait_for_timeout(800)

        msg = login_page.get_message()
        assert msg == "用户名或密码错误", (
            f"密码错误应提示「用户名或密码错误」，实际显示：{msg!r}（对应 BUG-001）"
        )

    @allure.story("登录失败")
    @allure.title("登录页 - 登录失败后不应跳转")
    def test_login_fail_stay_on_page(self, login_page):
        login_page.login("alice", "wrong")
        login_page.page.wait_for_timeout(800)

        assert "/app" not in login_page.page.url, (
            f"登录失败不应跳转，当前 URL：{login_page.page.url}"
        )

    @allure.story("密码安全")
    @allure.title("登录页 - 密码输入框类型为 password（不显示明文）")
    def test_password_masked(self, login_page):
        input_type = login_page.page.get_attribute(LoginPage.PASSWORD_INPUT, "type")
        assert input_type == "password", f"密码框 type 应为 password，实际：{input_type}"
