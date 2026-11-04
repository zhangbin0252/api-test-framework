# -*- coding: utf-8 -*-
"""请求基类：所有接口类的父类

职责：
- 统一拼接 base_url、统一超时、统一重试
- 统一日志（请求 / 响应），失败时可直接从日志定位
- 统一会话保持（requests.Session），token 写入后全模块复用
- 自动把请求与响应挂到 Allure 报告
"""
import time
import allure
import requests
from utils.yaml_util import read_yaml
from utils.logger_util import log


class BaseApi:

    # 子类覆盖该属性即可切换被测站点
    site = "mock"
    max_retry = 2          # 网络异常重试次数
    retry_interval = 0.5   # 重试间隔（秒）

    def __init__(self):
        cfg = read_yaml("config/config.yaml")
        node = cfg[self.site]
        self.base_url = node["base_url"].rstrip("/")
        self.timeout = node["timeout"]
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ---------- 核心请求方法 ----------
    def send(self, method, url, **kwargs):
        """统一发请求：拼 URL、超时、重试、日志、Allure 附件

        :param method: GET / POST / PUT / PATCH / DELETE
        :param url:    以 / 开头的相对路径
        :return: requests.Response
        """
        full_url = self.base_url + url if url.startswith("/") else url
        kwargs.setdefault("timeout", self.timeout)

        log.info(f"--> {method} {full_url}  params={kwargs.get('params')}  json={kwargs.get('json')}")

        last_exc = None
        for attempt in range(1, self.max_retry + 1):
            try:
                start = time.time()
                resp = self.session.request(method, full_url, **kwargs)
                cost = (time.time() - start) * 1000
                log.info(f"<-- {resp.status_code} {full_url}  {cost:.0f}ms")
                log.debug(f"    响应体: {resp.text[:800]}")
                self._attach(method, full_url, kwargs, resp)
                return resp
            except requests.exceptions.RequestException as e:
                last_exc = e
                log.warning(f"请求异常（第 {attempt}/{self.max_retry} 次）：{e}")
                if attempt < self.max_retry:
                    time.sleep(self.retry_interval)
        raise last_exc

    def _attach(self, method, url, kwargs, resp):
        """把请求与响应挂进 Allure 报告，失败时可点开看原始报文"""
        try:
            allure.attach(
                f"{method} {url}\n"
                f"params: {kwargs.get('params')}\n"
                f"json:   {kwargs.get('json')}\n"
                f"headers: {dict(self.session.headers)}",
                name="请求",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                f"HTTP {resp.status_code}\n"
                f"耗时 {resp.elapsed.total_seconds() * 1000:.0f}ms\n\n{resp.text[:2000]}",
                name="响应",
                attachment_type=allure.attachment_type.TEXT,
            )
        except Exception:
            # Allure 附件失败不应影响用例执行
            pass

    # ---------- 便捷方法 ----------
    def get(self, url, **kwargs):
        return self.send("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.send("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.send("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.send("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.send("DELETE", url, **kwargs)

    # ---------- 会话辅助 ----------
    def set_token(self, token):
        """把 token 写入会话头，后续请求自动携带"""
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        log.info("token 已写入会话头，后续请求自动携带")

    def clear_token(self):
        self.session.headers.pop("Authorization", None)
