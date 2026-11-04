# -*- coding: utf-8 -*-
"""日志工具：控制台 + 文件双输出，按天切分"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")

_initialized = False


def get_logger(name="api_test"):
    """获取全局唯一的 logger，避免重复添加 handler"""
    global _initialized
    logger = logging.getLogger(name)
    if _initialized:
        return logger

    os.makedirs(LOG_DIR, exist_ok=True)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 文件（按天切分，保留 7 天）
    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "run.log"), when="midnight",
        backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    _initialized = True
    return logger


log = get_logger()
