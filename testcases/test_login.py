# -*- coding: utf-8 -*-
"""登录模块接口用例（数据驱动，10 条）"""
import allure
import pytest

from utils.yaml_util import read_yaml
from utils.assert_util import AssertUtil as A

LOGIN_DATA = read_yaml("data/login.yaml")["login"]


def _login_param(case):
    """把 YAML 里标了 known_bug 的用例转成 xfail

    为什么这么做：
    - 这条用例断言的是「正确行为」（密码错应回 401），而服务端当前有缺陷，
      所以它必然失败。这不是用例写错了，是被测系统的问题。
    - 如果让它一直报红，团队会习惯性忽略红色失败，告警就形同虚设。
    - 用 strict=True 的 xfail：缺陷还在 → 报告为 xfailed；
      缺陷被修复 → 变成 XPASS 并直接报错，提醒你把标记删掉。
      这样既不掩盖缺陷，也不让流水线常红。
    """
    marks = []
    bug = case.get("known_bug")
    if bug:
        marks.append(
            pytest.mark.xfail(reason=f"已知缺陷 {bug}：{case['desc']}", strict=True)
        )
    return pytest.param(case, marks=marks)


LOGIN_PARAMS = [_login_param(c) for c in LOGIN_DATA]
LOGIN_IDS = [c["desc"] for c in LOGIN_DATA]


@allure.feature("登录模块")
class TestLogin:

    @allure.story("登录")
    @allure.title("登录 - {case[desc]}")
    @pytest.mark.parametrize("case", LOGIN_PARAMS, ids=LOGIN_IDS)
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
