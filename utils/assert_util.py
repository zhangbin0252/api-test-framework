# -*- coding: utf-8 -*-
"""断言工具：四重校验

1. 状态码断言
2. 业务字段断言
3. 响应结构 / 类型断言
4. 响应时间断言
"""
import allure
from utils.logger_util import log


class AssertUtil:

    @staticmethod
    def status_code(resp, expected, desc=""):
        """断言 HTTP 状态码"""
        with allure.step(f"断言状态码 {expected}  {desc}"):
            actual = resp.status_code
            log.debug(f"[断言] status_code 期望={expected} 实际={actual}")
            assert actual == expected, (
                f"状态码不符：期望 {expected}，实际 {actual}\n"
                f"响应内容：{resp.text[:500]}"
            )

    @staticmethod
    def field(resp, field, expected, desc=""):
        """断言响应 JSON 中某个字段的值"""
        with allure.step(f"断言字段 {field} == {expected!r}  {desc}"):
            body = resp.json()
            assert field in body, f"响应中不存在字段 {field}，实际响应：{body}"
            actual = body[field]
            log.debug(f"[断言] 字段 {field} 期望={expected!r} 实际={actual!r}")
            assert actual == expected, f"字段 {field} 不符：期望 {expected!r}，实际 {actual!r}"

    @staticmethod
    def contains(resp, text, desc=""):
        """断言响应文本包含某段内容（用于非 JSON 响应）"""
        with allure.step(f"断言响应包含 {text!r}  {desc}"):
            assert text in resp.text, f"响应未包含 {text!r}，实际：{resp.text[:300]}"

    @staticmethod
    def nested(resp, path, expected, desc=""):
        """断言嵌套字段，path 用点号分隔，如 data.id / _meta.powered_by"""
        with allure.step(f"断言 {path} == {expected!r}  {desc}"):
            body = resp.json()
            actual = body
            for key in path.split("."):
                if not isinstance(actual, dict) or key not in actual:
                    raise AssertionError(f"路径 {path} 在第 {key} 段中断，实际响应：{body}")
                actual = actual[key]
            assert actual == expected, f"{path} 不符：期望 {expected!r}，实际 {actual!r}"

    @staticmethod
    def not_empty(resp, field, desc=""):
        """断言字段存在且非空"""
        with allure.step(f"断言字段 {field} 非空  {desc}"):
            body = resp.json()
            assert field in body, f"响应中不存在字段 {field}"
            assert body[field], f"字段 {field} 为空：{body[field]!r}"

    @staticmethod
    def key_absent(resp, field, desc=""):
        """断言响应中不存在某字段（用于越权 / 敏感信息泄露检查）"""
        with allure.step(f"断言字段 {field} 不存在  {desc}"):
            body = resp.json()
            assert field not in body, f"不应出现的字段 {field} 出现在响应中：{body}"

    @staticmethod
    def type_is(resp, field, expected_type, desc=""):
        """断言字段类型"""
        with allure.step(f"断言 {field} 类型为 {expected_type.__name__}  {desc}"):
            body = resp.json()
            assert field in body, f"响应中不存在字段 {field}"
            assert isinstance(body[field], expected_type), (
                f"字段 {field} 类型不符：期望 {expected_type.__name__}，"
                f"实际 {type(body[field]).__name__}"
            )

    @staticmethod
    def response_time(resp, max_ms, desc=""):
        """断言响应时间不超过阈值（毫秒）"""
        with allure.step(f"断言响应时间 <= {max_ms}ms  {desc}"):
            elapsed_ms = resp.elapsed.total_seconds() * 1000
            log.debug(f"[断言] 响应时间 {elapsed_ms:.0f}ms（上限 {max_ms}ms）")
            assert elapsed_ms <= max_ms, f"响应超时：{elapsed_ms:.0f}ms > {max_ms}ms"
