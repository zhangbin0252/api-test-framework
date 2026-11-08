# -*- coding: utf-8 -*-
"""鉴权与越权用例（安全测试视角，6 条）

这一组是接口测试最有价值的部分——页面点不出来，只能靠接口测。
注意：本模块会切换 token（普通用户 / 伪造 token），因此每个用例
都使用独立的 UserApi 实例，避免污染其它模块的会话头。
"""
import allure
import pytest

from api.user_api import UserApi
from utils.assert_util import AssertUtil as A


@pytest.fixture()
def isolated_api():
    """独立的接口实例，用例结束后自动丢弃，不影响全局会话"""
    return UserApi()


@allure.feature("鉴权与安全")
class TestAuth:

    @allure.story("未认证访问")
    @allure.title("未登录访问 /api/me 应返回 401")
    def test_me_without_token(self, isolated_api):
        resp = isolated_api.me()
        A.status_code(resp, 401, "未携带 token 应返回 401")
        A.field(resp, "error", "unauthorized")

    @allure.story("未认证访问")
    @allure.title("未登录创建用户应返回 401")
    def test_create_without_token(self, isolated_api):
        resp = isolated_api.create_user("hacker", "hacker@example.com")
        A.status_code(resp, 401, "未登录不应能创建用户")

    @allure.story("无效凭证")
    @allure.title("伪造 token 访问应返回 401")
    def test_fake_token(self, isolated_api):
        isolated_api.set_token("tok_fake_token_123456")
        resp = isolated_api.me()
        A.status_code(resp, 401, "伪造 token 应被拒绝")

    @allure.story("越权访问")
    @allure.title("越权检查 - 未登录查询用户详情（BUG-002：应 401，实际 200）")
    @pytest.mark.xfail(
        reason="已知缺陷 BUG-002：用户详情接口未做鉴权，未登录可查任意用户（水平越权）",
        strict=True,
    )
    def test_unauthorized_read_user(self, isolated_api):
        """对应服务端已知缺陷 BUG-002

        用户详情接口未做鉴权，未登录也能拿到任意用户数据，
        属于「水平越权」，真实项目里是安全缺陷。

        标 xfail 的原因：这条用例断言的是正确行为，缺陷在服务端，
        所以它必然失败。保留它反而是价值——缺陷一修，这里就会变成
        XPASS 并报错，逼着人来删标记，保证缺陷修复不会无人察觉。
        """
        resp = isolated_api.get_user(1)
        A.status_code(resp, 401, "未登录不应能查询用户详情")

    @allure.story("权限控制")
    @allure.title("普通用户不能创建用户（应返回 403）")
    def test_normal_user_cannot_create(self, isolated_api, cfg):
        acc = cfg["accounts"]["normal"]
        login = isolated_api.login(acc["username"], acc["password"])
        A.status_code(login, 200, "普通用户应能登录")
        isolated_api.set_token(login.json()["token"])

        resp = isolated_api.create_user("by_normal", "normal@example.com")
        A.status_code(resp, 403, "普通用户创建用户应被拒绝")
        A.field(resp, "error", "forbidden")

    @allure.story("敏感信息")
    @allure.title("用户详情不应返回密码字段")
    def test_no_password_leak(self, isolated_api):
        resp = isolated_api.get_user(1)
        A.status_code(resp, 200)
        body = resp.text.lower()
        assert "password" not in body, f"响应中出现了 password 字段：{resp.text[:200]}"
