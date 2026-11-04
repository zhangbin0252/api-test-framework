# -*- coding: utf-8 -*-
"""HTTP 协议层用例（httpbin.org）：参数回显、鉴权、状态码、重定向

为什么保留这一组？
Mock 服务验证的是「业务逻辑对不对」，httpbin 验证的是「HTTP 协议本身对不对」——
比如中文参数有没有正确 URL 编码、Content-Type 有没有传对、302 会不会被自动跟随。
这些页面点不出来，只能靠接口测。

注意：httpbin 是外部服务，网络不通时整组用例会 skip 而不是 fail，
避免因为网络问题导致流水线变红。
"""
import allure
import pytest
import requests

from utils.assert_util import AssertUtil as A

BASE = "https://httpbin.org"


@pytest.fixture(scope="module")
def httpbin():
    """httpbin 会话；网络不通则整组 skip"""
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    try:
        s.get(f"{BASE}/get", timeout=10)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"httpbin.org 不可达，跳过协议层用例：{e}")
    yield s
    s.close()


@allure.feature("HTTP 协议层")
class TestHttpBin:

    @allure.story("参数回显")
    @allure.title("GET 请求 - query 参数应原样回显")
    def test_get_params_echo(self, httpbin):
        resp = httpbin.get(f"{BASE}/get", params={"page": "2", "keyword": "手机"})

        A.status_code(resp, 200)
        A.nested(resp, "args.page", "2", "query 参数应回显")
        A.nested(resp, "args.keyword", "手机", "中文参数应正确编码")
        A.nested(resp, "method", "GET")

    @allure.story("参数回显")
    @allure.title("POST JSON - 请求体应原样回显")
    def test_post_json_echo(self, httpbin):
        payload = {"name": "morpheus", "job": "leader"}
        resp = httpbin.post(f"{BASE}/post", json=payload)

        A.status_code(resp, 200)
        A.nested(resp, "json.name", "morpheus")
        A.nested(resp, "method", "POST")
        A.contains(resp, "application/json", "Content-Type 应为 application/json")

    @allure.story("参数回显")
    @allure.title("POST 表单 - form 数据应正确解析")
    def test_post_form_echo(self, httpbin):
        resp = httpbin.post(f"{BASE}/post", data={"user": "tom", "age": "18"})

        A.status_code(resp, 200)
        A.nested(resp, "form.user", "tom")
        A.nested(resp, "form.age", "18")

    # ---------- 鉴权 ----------
    @allure.story("鉴权")
    @allure.title("Basic Auth - 正确凭据返回 200")
    def test_basic_auth_success(self, httpbin):
        resp = httpbin.get(f"{BASE}/basic-auth/tom/123", auth=("tom", "123"))

        A.status_code(resp, 200)
        A.field(resp, "authenticated", True)
        A.field(resp, "user", "tom")

    @allure.story("鉴权")
    @allure.title("Basic Auth - 不带凭据返回 401")
    def test_basic_auth_unauthorized(self, httpbin):
        resp = httpbin.get(f"{BASE}/basic-auth/tom/123")

        A.status_code(resp, 401, "未认证应返回 401")

    @allure.story("鉴权")
    @allure.title("Bearer Token - 正确 token 返回 200")
    def test_bearer_success(self, httpbin):
        resp = httpbin.get(f"{BASE}/bearer",
                           headers={"Authorization": "Bearer my_test_token_123"})

        A.status_code(resp, 200)
        A.field(resp, "authenticated", True)
        A.field(resp, "token", "my_test_token_123")

    @allure.story("鉴权")
    @allure.title("Bearer Token - 缺失 token 返回 401")
    def test_bearer_missing(self, httpbin):
        resp = httpbin.get(f"{BASE}/bearer")

        A.status_code(resp, 401, "缺失 token 应返回 401")

    # ---------- 状态码 ----------
    @allure.story("状态码")
    @allure.title("状态码 - 服务端应返回请求的状态码")
    @pytest.mark.parametrize("code", [200, 201, 400, 401, 403, 404, 500, 502, 503])
    def test_status_codes(self, httpbin, code):
        resp = httpbin.get(f"{BASE}/status/{code}")
        A.status_code(resp, code, f"应返回 {code}")

    # ---------- 重定向 ----------
    @allure.story("重定向")
    @allure.title("重定向 - 默认自动跟随到 200")
    def test_redirect_followed(self, httpbin):
        resp = httpbin.get(f"{BASE}/redirect/2")

        A.status_code(resp, 200, "requests 默认跟随重定向，最终应为 200")
        A.contains(resp, "httpbin", "最终响应应来自 httpbin")

    @allure.story("重定向")
    @allure.title("重定向 - 禁用跟随时应停留在 302")
    def test_redirect_not_followed(self, httpbin):
        resp = httpbin.get(f"{BASE}/redirect/1", allow_redirects=False)

        A.status_code(resp, 302, "allow_redirects=False 时应停留在 302")

    # ---------- 响应时间 ----------
    @allure.story("性能")
    @allure.title("响应时间 - delay/1 接口耗时应在 1~5 秒之间")
    def test_delay_endpoint(self, httpbin):
        resp = httpbin.get(f"{BASE}/delay/1", timeout=15)

        A.status_code(resp, 200)
        elapsed = resp.elapsed.total_seconds()
        assert 0.9 <= elapsed <= 5.0, f"delay/1 应耗时约 1 秒，实际 {elapsed:.2f}s"

    @allure.story("数据格式")
    @allure.title("UUID 接口 - 返回 36 位标准格式")
    def test_uuid_format(self, httpbin):
        resp = httpbin.get(f"{BASE}/uuid")

        A.status_code(resp, 200)
        A.not_empty(resp, "uuid")
        uuid_str = resp.json()["uuid"]
        assert len(uuid_str) == 36, f"UUID 长度应为 36，实际 {len(uuid_str)}"
        assert uuid_str.count("-") == 4, f"UUID 应含 4 个连字符，实际：{uuid_str}"
