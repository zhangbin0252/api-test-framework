# -*- coding: utf-8 -*-
"""YAML 读取工具：统一处理路径与编码"""
import os
import yaml

# 项目根目录（utils 的上一级）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_yaml(relative_path):
    """读取相对项目根目录的 yaml 文件

    :param relative_path: 例如 "config/config.yaml" 或 "data/login.yaml"
    :return: 解析后的 Python 对象
    """
    path = os.path.join(ROOT, relative_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
