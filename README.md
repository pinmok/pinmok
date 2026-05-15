# Pinmok

Feels like Django. Barely any learning.

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

English | [中文](README.zh-CN.md)

---

## Introduction

Pinmok is a modular admin framework built on top of Django Admin. It extends Admin with a modular design philosophy, while fully preserving
the Django development experience you already know.

Pinmok provides a standardized menu system that goes beyond model-bound navigation, extending into complex business workflows. It also
covers common site configuration, frontend theme management, and a complete chain from menu visibility to URL access control. Each feature
lives in its own independent app — plug in what you need, remove what you don't, keeping backend infrastructure and business logic cleanly
separated. Whether it's content management, user operations, or data dashboards, any module can be wired into Pinmok and combined freely.

## Features

**Minimal learning curve**
Takes over Django Admin while remaining fully compatible with existing usage — no changes to your current logic required. Django knowledge
covers the backend; Bootstrap knowledge covers the interface.

**Flexible menu system**
A simple configuration is all it takes to plug in a custom menu structure and extend your admin with new business sections.

**Modular by design**
Each module is independent. Install it and it works; remove it and nothing else breaks. Start lightweight and add only what you need.

**No separate permission logic**
Configure your menus and access control is handled automatically. Menu visibility and URL-level access are the same thing — defined once,
enforced everywhere.

**Themeable interface**
The admin supports self-contained theme packages with customizable layouts, color schemes, and components. Multiple themes can coexist and
be switched at any time.

**Internationalization out of the box**
Built on Django's native i18n system. All user-facing text in the framework is translatable, and your own apps plug into the same pipeline
with no extra setup.

## Requirements

- Python >= 3.12
- Django >= 5.2 (compatible with the latest release; older versions are untested and not recommended)

### Dependencies

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0 (msgid deduplication for i18n, install only if needed)

> Other dependency conventions follow Django's standards.

## Contributing

Pinmok is still in its early stages, and there's plenty to build together. If you find this project worthwhile, contributions are welcome —
and so is a Star on the repository. For an independently developed open source project, that kind of support genuinely matters.

- GitHub: [github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee: [gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)