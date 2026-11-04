# -*- coding: utf-8 -*-
"""浏览器驱动管理：统一创建 / 复用 / 关闭浏览器

为什么单独抽出来？
1. 浏览器启动慢（约 1 秒），整个测试会话只启动一次
2. 每个用例用独立的 context（浏览器上下文），实现「Cookie / localStorage 隔离」——
   这是 UI 自动化里最重要的一条：用例之间不能共享登录态，否则会互相污染
3. 失败时自动截图，方便定位
"""
import os
import allure
from playwright.sync_api import sync_playwright
from utils.logger_util import log

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(ROOT, "report", "screenshots")


class BrowserManager:
    """全局浏览器管理（单例，整个测试会话共用）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._playwright = None
        self._browser = None
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ---------- 生命周期 ----------
    def start(self, headless=True):
        """启动浏览器（整个会话只调用一次）"""
        if self._browser is not None:
            return self._browser
        log.info(f"启动浏览器（headless={headless}）")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            args=["--disable-dev-shm-usage"],
        )
        return self._browser

    def stop(self):
        """关闭浏览器，释放资源"""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
            log.info("浏览器已关闭")
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    # ---------- 上下文 ----------
    def new_context(self, viewport=None, base_url=None):
        """创建独立的浏览器上下文（相当于一个全新的浏览器窗口）

        每个上下文有独立的 Cookie、localStorage、缓存，
        所以用例之间不会互相影响登录态。
        """
        if self._browser is None:
            raise RuntimeError("浏览器尚未启动，请先调用 start()")
        ctx = self._browser.new_context(
            viewport=viewport or {"width": 1440, "height": 900},
            base_url=base_url,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        ctx.set_default_timeout(10000)
        return ctx

    # ---------- 失败截图 ----------
    @staticmethod
    def screenshot_on_failure(page, name):
        """用例失败时截图，挂进 Allure 报告"""
        try:
            path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
            page.screenshot(path=path, full_page=True)
            allure.attach.file(
                path, name=f"失败截图 - {name}",
                attachment_type=allure.attachment_type.PNG,
            )
            log.info(f"失败截图已保存：{path}")
        except Exception as e:
            log.warning(f"截图失败：{e}")


browser_manager = BrowserManager()
