# DjangoCMF

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](#)
[![License](https://img.shields.io/badge/license-MIT-blue)](#)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](#)

## 简介

这里放项目的简单描述，例如：

> 一个基于 Django 的 CMS 系统，核心模块开源，支持插件化扩展。

## 安装

```bash
# 安装核心模块
pip install djangocmf-core

# 安装可选插件（示例）
pip install djangocmf-portal
````

## 使用

1. 在 `INSTALLED_APPS` 添加核心模块和插件：

```python
INSTALLED_APPS = [
    "djangocmf.cmfadmin",
]
```

1. 运行数据库迁移：

```bash
python manage.py migrate
```

1. 启动开发服务器：

```bash
python manage.py runserver
```

## 贡献

欢迎提交 issue 或 PR。

## 许可证

本项目遵循 [MIT License](LICENSE)。
