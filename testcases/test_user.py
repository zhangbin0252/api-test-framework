# -*- coding: utf-8 -*-
"""用户管理模块接口用例（数据驱动，17 条）"""
import allure
import pytest

from utils.yaml_util import read_yaml
from utils.assert_util import AssertUtil as A

DATA = read_yaml("data/user.yaml")


@allure.feature("用户管理模块")
class TestUser:

    # ---------- 列表查询 ----------
    @allure.story("用户列表")
    @allure.title("用户列表 - {case[desc]}")
    @pytest.mark.parametrize("case", DATA["list_users"], ids=[c["desc"] for c in DATA["list_users"]])
    def test_list_users(self, admin_api, case):
        resp = admin_api.list_users(page=case["page"], size=case["size"])

        A.status_code(resp, case["expect_status"], case["desc"])

        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"])
        if case.get("expect_count") is not None:
            data = resp.json()["data"]
            assert len(data) == case["expect_count"], (
                f"返回条数不符：期望 {case['expect_count']}，实际 {len(data)}"
            )
            # 分页元信息完整性
            for key in ("page", "size", "total", "total_pages"):
                A.not_empty(resp, key, f"分页字段 {key} 应存在")

    # ---------- 详情查询 ----------
    @allure.story("用户详情")
    @allure.title("用户详情 - {case[desc]}")
    @pytest.mark.parametrize("case", DATA["get_user"], ids=[c["desc"] for c in DATA["get_user"]])
    def test_get_user(self, admin_api, case):
        resp = admin_api.get_user(case["user_id"])

        A.status_code(resp, case["expect_status"], case["desc"])

        if case.get("expect_username"):
            A.nested(resp, "data.id", case["user_id"], "返回 id 应与请求一致")
            A.nested(resp, "data.username", case["expect_username"])
        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"])

    # ---------- 创建 ----------
    @allure.story("创建用户")
    @allure.title("创建用户 - {case[desc]}")
    @pytest.mark.parametrize("case", DATA["create_user"], ids=[c["desc"] for c in DATA["create_user"]])
    def test_create_user(self, admin_api, case):
        # 用时间戳保证用户名唯一，避免重复执行时撞 409
        import time
        uname = case["username"] if case["expect_status"] != 201 else f"{case['username']}_{int(time.time()*1000)%100000}"

        resp = admin_api.create_user(uname, case["email"])

        A.status_code(resp, case["expect_status"], case["desc"])

        if case["expect_status"] == 201:
            A.nested(resp, "data.username", uname, "返回的用户名应与提交一致")
            A.not_empty(resp, "createdAt", "创建成功应返回创建时间")
        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"])

    # ---------- 更新 ----------
    @allure.story("更新用户")
    @allure.title("更新用户 - {case[desc]}")
    @pytest.mark.parametrize("case", DATA["update_user"], ids=[c["desc"] for c in DATA["update_user"]])
    def test_update_user(self, admin_api, case):
        if "patch" in case:
            resp = admin_api.patch_user(case["user_id"], **case["patch"])
        else:
            resp = admin_api.update_user(case["user_id"], **case["put"])

        A.status_code(resp, case["expect_status"], case["desc"])

        if case["expect_status"] == 200:
            A.not_empty(resp, "updatedAt", "更新成功应返回更新时间")
        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"])

    # ---------- 删除 ----------
    @allure.story("删除用户")
    @allure.title("删除用户 - {case[desc]}")
    @pytest.mark.parametrize("case", DATA["delete_user"], ids=[c["desc"] for c in DATA["delete_user"]])
    def test_delete_user(self, admin_api, case):
        resp = admin_api.delete_user(case["user_id"])

        A.status_code(resp, case["expect_status"], case["desc"])
        if case.get("expect_error"):
            A.field(resp, "error", case["expect_error"])

    @allure.story("删除用户")
    @allure.title("删除用户 - 不能删除自己")
    def test_cannot_delete_self(self, admin_api, cfg):
        # 先查到自己 id
        me = admin_api.me()
        A.status_code(me, 200)
        my_id = me.json()["data"]["id"]

        resp = admin_api.delete_user(my_id)
        A.status_code(resp, 400, "删除自己应被拒绝")
        A.field(resp, "error", "cannot_delete_self")
