# -*- coding: utf-8 -*-
"""页面对象基类（Page Object 模式）

为什么要 PO 模式？
如果把「选择器」和「断言」混在用例里，页面一改，所有用例都要改。
PO 模式把「页面长什么样、怎么操作」封装在页面类里，用例只写业务逻辑：
    login_page.login("alice", "Alice@123")
页面改版时只改页面类，用例不用动——这就是 UI 自动化的可维护性。
"""
import allure
from utils.logger_util import log


class BasePage:
    """所有页面对象的父类，提供通用操作"""

    # 子类覆盖：页面路径（相对 base_url）
    path = "/"

    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url.rstrip("/")

    # ---------- 导航 ----------
    def open(self):
        """打开页面并等待加载完成"""
        url = self.base_url + self.path
        log.info(f"打开页面：{url}")
        self.page.goto(url, wait_until="domcontentloaded")
        return self

    def current_url(self):
        return self.page.url

    def title(self):
        return self.page.title()

    # ---------- 元素操作 ----------
    def click(self, selector, desc=""):
        """点击元素，带步骤记录"""
        with allure.step(f"点击 {desc or selector}"):
            log.debug(f"click: {selector}")
            self.page.click(selector)

    def fill(self, selector, text, desc=""):
        """输入文本（会先清空）"""
        with allure.step(f"在 {desc or selector} 输入 {text!r}"):
            log.debug(f"fill: {selector} = {text!r}")
            self.page.fill(selector, text)

    def text_of(self, selector):
        """获取元素文本"""
        return self.page.inner_text(selector)

    def is_visible(self, selector, timeout=3000):
        """元素是否可见（不抛异常，返回布尔值）"""
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def count(self, selector):
        """元素个数"""
        return self.page.locator(selector).count()

    def wait_for_url(self, pattern, timeout=8000):
        """等待 URL 变化（用于断言跳转）"""
        with allure.step(f"等待 URL 匹配 {pattern}"):
            self.page.wait_for_url(pattern, timeout=timeout)

    def wait_for_text(self, selector, text, timeout=5000):
        """等待元素出现指定文本"""
        with allure.step(f"等待 {selector} 出现文本 {text!r}"):
            self.page.wait_for_function(
                """([sel, txt]) => {
                    const el = document.querySelector(sel);
                    return el && el.innerText.includes(txt);
                }""",
                arg=[selector, text],
                timeout=timeout,
            )

    # ---------- 断言辅助 ----------
    def assert_text(self, selector, expected, desc=""):
        """断言元素文本等于期望值"""
        with allure.step(f"断言 {desc or selector} == {expected!r}"):
            actual = self.text_of(selector).strip()
            assert actual == expected, (
                f"{desc or selector} 文本不符：期望 {expected!r}，实际 {actual!r}"
            )

    def assert_contains(self, selector, expected, desc=""):
        """断言元素文本包含期望内容"""
        with allure.step(f"断言 {desc or selector} 包含 {expected!r}"):
            actual = self.text_of(selector)
            assert expected in actual, (
                f"{desc or selector} 未包含 {expected!r}，实际：{actual!r}"
            )

    def assert_visible(self, selector, desc=""):
        """断言元素可见"""
        with allure.step(f"断言 {desc or selector} 可见"):
            assert self.is_visible(selector), f"{desc or selector} 不可见"

    def assert_not_visible(self, selector, desc=""):
        """断言元素不可见"""
        with allure.step(f"断言 {desc or selector} 不可见"):
            assert not self.is_visible(selector, timeout=1500), f"{desc or selector} 仍然可见"

    def assert_url_contains(self, fragment, desc=""):
        """断言当前 URL 包含指定片段"""
        with allure.step(f"断言 URL 包含 {fragment!r}"):
            assert fragment in self.page.url, (
                f"URL 不符：期望包含 {fragment!r}，实际 {self.page.url!r}"
            )

    # ---------- 截图 ----------
    def screenshot(self, name):
        """截图并挂到 Allure 报告"""
        try:
            import os
            from ui.browser import SCREENSHOT_DIR
            path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
            self.page.screenshot(path=path, full_page=True)
            allure.attach.file(
                path, name=f"截图 - {name}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as e:
            log.warning(f"截图失败：{e}")
