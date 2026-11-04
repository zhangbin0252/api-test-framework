# -*- coding: utf-8 -*-
"""UI 测试专用 fixture

设计要点：
1. 浏览器整个会话只启动一次（启动成本约 1 秒）
2. 每个用例独立的 context —— Cookie / localStorage 完全隔离，互不污染
3. 每个用例结束后自动关闭 context，失败时自动截图
"""
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.browser import browser_manager
from ui.login_page import LoginPage
from ui.user_list_page import UserListPage
from utils.yaml_util import read_yaml
from utils.logger_util import log


@pytest.fixture(scope="session")
def ui_config():
    """UI 测试配置"""
    cfg = read_yaml("config/config.yaml")
    return {
        "base_url": cfg["mock"]["base_url"],
        "headless": cfg.get("ui", {}).get("headless", True),
        "accounts": cfg["accounts"],
    }


@pytest.fixture(scope="session", autouse=True)
def browser(ui_config):
    """会话级：启动浏览器一次"""
    log.info("=" * 60)
    log.info("UI 测试会话开始，启动浏览器")
    browser_manager.start(headless=ui_config["headless"])
    yield browser_manager
    browser_manager.stop()
    log.info("UI 测试会话结束")


@pytest.fixture()
def context(browser, ui_config):
    """用例级：每个用例一个独立的浏览器上下文（登录态隔离）"""
    ctx = browser.new_context(base_url=ui_config["base_url"])
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context):
    """用例级：新标签页"""
    pg = context.new_page()
    yield pg
    pg.close()


@pytest.fixture()
def login_page(page, ui_config):
    """登录页对象，已打开"""
    return LoginPage(page, ui_config["base_url"]).open()


@pytest.fixture()
def user_list_page(page, ui_config):
    """用户列表页对象（未登录状态，用例里按需登录）"""
    return UserListPage(page, ui_config["base_url"])


@pytest.fixture()
def logged_in_page(page, ui_config):
    """已登录状态下的用户列表页

    通过 UI 真实走一遍登录流程（而不是直接塞 localStorage），
    这样才叫 UI 自动化——验证的是用户真实操作路径。
    """
    acc = ui_config["accounts"]["admin"]
    login = LoginPage(page, ui_config["base_url"]).open()
    login.login_expect_success(acc["username"], acc["password"])
    ulp = UserListPage(page, ui_config["base_url"])
    ulp.wait_loaded()
    return ulp


@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    """用例失败时自动截图（挂在 Allure 报告里）"""
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        pass


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """把测试结果挂到 item 上，供 fixture 判断是否失败"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    if rep.when == "call" and rep.failed:
        # 找到该用例的 page 对象并截图
        page = item.funcargs.get("page")
        if page is not None:
            name = item.name.replace("/", "_").replace("\\", "_")
            browser_manager.screenshot_on_failure(page, name)
