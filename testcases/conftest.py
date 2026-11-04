# -*- coding: utf-8 -*-
"""pytest 全局 fixture

关键设计：
1. 会话级自动启动本地 Mock 服务——用例不依赖任何外部站点，结果 100% 可复现
2. 会话级登录一次，token 写入 Session，全模块复用（避免重复登录）
3. 每个用例前重置会话头，防止用例之间互相污染
"""
import os
import sys
import socket
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.user_api import UserApi
from business.user_business import UserBusiness
from utils.yaml_util import read_yaml
from utils.logger_util import log


def _port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def cfg():
    """全局配置，整个会话只读一次"""
    return read_yaml("config/config.yaml")


@pytest.fixture(scope="session", autouse=True)
def mock_server(cfg):
    """会话级启动本地 Mock 服务

    端口已被占用时直接复用（方便你手动开着服务调试）。
    """
    from urllib.parse import urlparse
    parsed = urlparse(cfg["mock"]["base_url"])
    host, port = parsed.hostname, parsed.port

    if _port_open(host, port):
        log.info(f"Mock 服务已在运行：{host}:{port}，直接复用")
        yield cfg["mock"]["base_url"]
        return

    from mock_server.mock_server import start_server
    server = start_server(host, port)
    log.info(f"Mock 服务已启动：http://{host}:{port}")
    yield cfg["mock"]["base_url"]
    server.shutdown()
    log.info("Mock 服务已停止")


@pytest.fixture(scope="session")
def user_api(mock_server):
    """用户接口实例，整个会话复用同一个 Session"""
    return UserApi()


@pytest.fixture(scope="session")
def user_business(user_api):
    """业务层实例"""
    biz = UserBusiness()
    biz.api = user_api
    return biz


@pytest.fixture(scope="session")
def admin_token(user_business):
    """管理员登录一次，token 全模块复用"""
    log.info("=" * 60)
    log.info("会话级 fixture：管理员登录，token 将被全模块复用")
    token = user_business.login_success("admin")
    log.info(f"登录成功，token 前 12 位：{token[:12]}...")
    return token


@pytest.fixture(scope="session")
def reset_mock_state(mock_server):
    """会话级：在测试开始前把 Mock 数据恢复到初始状态

    接口自动化最常见的坑就是「用例之间互相污染」：
    上一个用例删掉了用户，下一个用例查列表就少一条，结果时好时坏。
    真实项目里的解法是每个用例前重置数据（或每次用新造的数据），
    这里用快照回滚的方式实现。
    """
    import copy
    from mock_server import mock_server as ms

    snapshot = {
        "USERS": copy.deepcopy(ms.USERS),
        "TOKENS": dict(ms.TOKENS),
        "NEXT_ID": list(ms.NEXT_ID),
    }
    yield snapshot

    # 会话结束不做恢复，避免影响你手动调试


@pytest.fixture()
def mock_state(reset_mock_state):
    """每个用例开始前，把 Mock 的内存数据恢复到快照

    这样用例的执行顺序、是否被其它用例删过数据，都不影响结果。
    """
    import copy
    from mock_server import mock_server as ms

    snap = reset_mock_state
    ms.USERS.clear()
    ms.USERS.update(copy.deepcopy(snap["USERS"]))
    ms.TOKENS.clear()
    ms.TOKENS.update(snap["TOKENS"])
    ms.NEXT_ID[:] = snap["NEXT_ID"]
    yield


@pytest.fixture()
def admin_api(user_api, admin_token, mock_state):
    """每个用例拿到一个已登录的会话（用例之间互不污染）

    为什么是 function 级而不是 session 级？
    会话头是共享的，如果某个用例故意清掉 token 或切成普通用户，
    后面的用例就会受影响。这里每个用例开始前：
      1. 重置 Mock 数据到快照（避免删除/创建操作影响后续用例）
      2. 重新写入管理员 token
    这是接口自动化稳定性的关键。
    """
    user_api.set_token(admin_token)
    yield user_api
    user_api.set_token(admin_token)


@pytest.fixture()
def clean_api(user_api, mock_state):
    """未登录的干净会话，用于测试鉴权类用例"""
    user_api.clear_token()
    yield user_api
    user_api.clear_token()

