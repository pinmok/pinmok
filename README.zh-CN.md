# Pinmok

**会 Django，就够了。**

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

[English](README.md) | 中文

---

## 简介

Pinmok 是一个基于 Django Admin 的模块化后台管理框架。

它的目标只有一个：让开发者把精力放在业务上，而不是框架本身。只要会写 Django app，就能接入后台逻辑；只要会用
Bootstrap，就能轻松构建后台界面。框架负责把菜单、权限、主题这些基础能力串联起来，而开发者只需遵循简单的规范，专注自己的业务，其余的交给 Pinmok。

因为基于 Django Admin 扩展，你已有的 Admin 使用习惯和知识可以直接沿用，没有额外的学习成本。

框架核心只包含站点设置和用户/组管理，其余功能以独立 app 的形式按需安装，像集装箱一样，按需安装，随时插拔。

## 核心特性

**模块化架构**
每个功能以独立 app 的形式存在，安装即可用，卸载不影响其他模块。开发自己的 app 与新建普通 Django app 没有本质区别，一切遵循Django习惯。

**菜单与权限**
每个 app 可以声明自己的菜单，框架统一管理、合并展示，支持最多三级层级。权限与菜单节点绑定，同时控制菜单的可见性与 URL 的访问控制，无需额外配置。

**主题系统**
支持独立主题包，每套主题可以自定义布局、样式变量和页面组件，多个主题共存，后台可切换。

**国际化支持**
遵循 Django 原生国际化机制，框架内所有用户可见文本均支持多语言，开发者的 app 同样可以无缝接入 Django 的 i18n 体系。

**后台界面基于 Tabler**
Tabler 是基于 Bootstrap 的现代后台 UI 框架。无论是使用框架内置组件，还是自己开发界面，Bootstrap 的知识都可以直接复用，不需要学习新的 UI 体系。

完整的配置说明和快速开始指南，请参阅 [文档（待补充）](#)。

## 目录结构

```
pinmok/
├── cmfadmin/       # 核心 app：菜单、权限、主题、站点配置
├── content/        # 内容管理 app（可选）
├── ...             # 其他可选 app
└── manage.py
```

## 参与贡献

欢迎提交 Issue 反馈问题，或通过 Pull Request 参与开发。

- Fork 仓库，基于 `main` 新建功能分支
- 代码注释使用英文
- 用户可见文本使用 `_()` 标记以支持国际化
- 提交 PR 时请简要描述改动内容

仓库地址：

- GitHub：[github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee：[gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)