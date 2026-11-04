# -*- coding: utf-8 -*-
"""业务流用例：跨接口串联（4 条）

对应真实工作中的「端到端」测试：验证的不是单接口对不对，
而是「创建后能查到吗」「登录后能访问吗」这类跨接口一致性。
"""
import allure

from utils.assert_util import AssertUtil as A


@allure.feature("业务流串联")
class TestBusinessFlow:

    @allure.story("登录鉴权链路")
    @allure.title("业务流 - 登录 → 带 token 访问受保护接口")
    def test_login_then_access(self, user_business, cfg):
        acc = cfg["accounts"]["admin"]
        login_resp, me_resp = user_business.login_then_access_protected(
            acc["username"], acc["password"])

        A.status_code(login_resp, 200, "登录应成功")
        A.status_code(me_resp, 200, "带 token 应能访问受保护接口")
        A.nested(me_resp, "data.username", acc["username"], "返回的应是当前登录用户")

    @allure.story("写后读一致性")
    @allure.title("业务流 - 创建用户后按 id 查询")
    def test_create_then_query(self, admin_api, user_business):
        import time
        uname = f"flow_{int(time.time() * 1000) % 100000}"

        created, queried = user_business.create_then_query(uname, f"{uname}@example.com")

        A.status_code(created, 201, "创建应返回 201")
        new_id = created.json()["data"]["id"]
        A.status_code(queried, 200, "用新 id 应能查到")
        A.nested(queried, "data.id", new_id, "查到的应是刚创建的用户")
        A.nested(queried, "data.username", uname)

    @allure.story("幂等性")
    @allure.title("业务流 - GET 幂等，连续两次查询结果一致")
    def test_get_idempotent(self, admin_api):
        first = admin_api.get_user(1)
        second = admin_api.get_user(1)

        A.status_code(first, 200)
        A.status_code(second, 200)
        assert first.json() == second.json(), "GET 幂等：两次请求应返回完全相同的数据"

    @allure.story("数据隔离")
    @allure.title("业务流 - 删除后查询应返回 404")
    def test_delete_then_query(self, admin_api):
        import time
        uname = f"del_{int(time.time() * 1000) % 100000}"

        created = admin_api.create_user(uname, f"{uname}@example.com")
        A.status_code(created, 201)
        new_id = created.json()["data"]["id"]

        deleted = admin_api.delete_user(new_id)
        A.status_code(deleted, 204, "删除应返回 204 且无响应体")

        queried = admin_api.get_user(new_id)
        A.status_code(queried, 404, "删除后再查询应返回 404")
