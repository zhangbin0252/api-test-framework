# -*- coding: utf-8 -*-
"""登录模块接口用例（数据驱动，10 条）"""
import allure
import pytest

from utils.yaml_util import read_yaml
from utils.assert_util import AssertUtil as A

LOGIN_DATA = read_yaml("data/login.yaml")["login"]


@allure.feature("登录模块")
class TestLogin:

    @allure.story("登录")
    @allure.title("登录 - {case[desc]}")
    @pytest.mark.parametrize("case", LOGIN_DATA, ids=[c["desc"] for c in LOGIN_DATA])
    def test_login(self, clean_api, case):
        resp = clean_api.login(case["username"], case["password"])

        A.status_code(resp, case["expect_status"], case["desc"])

        if case.get("expect_token"):
            A.not_empty(resp, "token", "登录成功应返回 token")
            A.type_is(resp, "token", str)

        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"], "错误码应与预期一致")

        # 安全校验：响应里绝不能出现密码
        if case.get("assert_password_hidden"):
            A.contains(resp, "token", "响应应包含 token")
            assert case["password"] not in resp.text, (
                "响应中出现了明文密码，属于敏感信息泄露"
            )

    @allure.story("登录")
    @allure.title("登录 - 返回 token 长度与格式校验")
    def test_login_token_format(self, clean_api, cfg):
        acc = cfg["accounts"]["admin"]
        resp = clean_api.login(acc["username"], acc["password"])

        A.status_code(resp, 200)
        token = resp.json()["token"]
        assert token.startswith("tok_"), f"token 应以 tok_ 开头，实际：{token[:10]}"
        assert len(token) > 12, f"token 长度异常：{token}"

    @allure.story("登录")
    @allure.title("登录 - 响应时间不超过 3 秒")
    def test_login_response_time(self, clean_api, cfg):
        acc = cfg["accounts"]["admin"]
        resp = clean_api.login(acc["username"], acc["password"])
        A.status_code(resp, 200)
        A.response_time(resp, cfg["perf"]["max_response_ms"])

    @allure.story("登出")
    @allure.title("登出 - token 失效后再访问受保护接口应返回 401")
    def test_logout_invalidates_token(self, clean_api, cfg):
        acc = cfg["accounts"]["admin"]
        resp = clean_api.login(acc["username"], acc["password"])
        A.status_code(resp, 200)
        token = resp.json()["token"]

        # 带 token 访问，应成功
        clean_api.set_token(token)
        A.status_code(clean_api.me(), 200, "带有效 token 应能访问 /api/me")

        # 登出后 token 应失效
        clean_api.logout()
        A.status_code(clean_api.me(), 401, "登出后 token 应失效")
