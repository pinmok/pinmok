# Pinmok

完整承袭 Django 原生开发习惯，上手即可快速开发

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

[English](README.md) | 中文

---

## 简介

Pinmok 是一个基于 Django Admin 的模块化后台管理框架，它在完全保留 Django 原有开发习惯的基础上，以模块化的设计理念对 Admin 进行扩展。

Pinmok 提供了标准化的菜单，不再拘泥于模型，将菜单功能延伸至复杂业务。同时还提供了常见的基础配置信息，前端主题管理等功能，打通了从界面可见性到 URL
访问控制的完整链路。每个业务功能以独立 app 的形式存在，按需接入，互不干扰，让后台开发和业务开发真正解耦。无论是内容管理、用户运营，还是数据看板，都可以作为独立模块接入
Pinmok，自由组合，灵活扩展。

## 核心功能

**极低的学习成本**
接管 Django admin 原生后台，完全兼容原有用法，无需修改已有逻辑。会 Django 就能写后台逻辑，会 Bootstrap 就能写后台界面。

**灵活菜单系统**
通过简单配置，即可接入自定义菜单系统，轻松拓展后台业务。

**按需组装，互不干扰**
每个功能模块独立存在，装上就能用，拿掉不影响其他部分。项目从轻量起步，需要什么加什么。

**权限不需要单独维护**
菜单配好了，访问控制就配好了。不需要额外写权限逻辑，菜单的可见性和 URL 的访问控制是同一件事。

**主题可以整套替换**
后台界面支持独立主题包，布局、配色、组件都可以定制，支持多套主题共存，随时切换。

**多语言开箱即用**
框架完整支持 Django 原生国际化体系，所有用户可见文本均可翻译。你的 app 接入同一套机制，无需额外配置。

## 环境要求

- Python >=3.12
- Django >= 5.2 （已兼容最新版本，低版本未测试，暂不推荐）

### 依赖

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0 （多语言 msgid 去重，按需安装）

> 其它依赖规范与 Django 相同

## 参与贡献

Pinmok 目前还在早期阶段，有很多可以一起做的事。如果你觉得这个方向有价值，欢迎参与进来，也欢迎去仓库点个 Star——对一个独立开发的开源项目来说，这是很实在的支持。

- GitHub：[github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee：[gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)