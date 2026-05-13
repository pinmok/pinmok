# Pinmok

**If you know Django, you're ready.**

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

English | [中文](README.zh-CN.md)

---

## Introduction

Pinmok is a modular admin framework built on top of Django Admin.

Its goal is simple: let developers focus on their business logic, not the framework itself. If you can write a Django app, you can plug in
backend logic. If you know Bootstrap, you can build the interface. Pinmok takes care of the rest — wiring together menus, permissions, and
themes — so you only need to follow a few conventions and focus on what matters.

Because Pinmok extends Django Admin, your existing Admin knowledge transfers directly. No new mental model to learn, no extra overhead.

The core ships with only site settings and user/group management. Everything else is an independent app — install what you need, remove what
you don't.

## Features

**Modular Architecture**
Each feature lives in its own app. Install it and it works; remove it and nothing else breaks. Building your own app is no different from
building a regular Django app — just follow the conventions, and Pinmok handles the integration.

**Menus & Permissions**
Each app declares its own menus. Pinmok merges and manages them centrally, with up to three levels of hierarchy. Permissions are bound to
menu nodes, controlling both visibility and URL access in one place — no extra configuration needed.

**Theme System**
Themes are self-contained packages. Each theme can define its own layout, style variables, and page components. Multiple themes can coexist
and be switched from the admin.

**Internationalization**
Pinmok follows Django's native i18n system. All user-facing text in the framework supports multiple languages. Your own apps can plug into
the same Django i18n pipeline without any extra setup.

**UI Based on Tabler**
Tabler is a modern admin UI framework built on Bootstrap. Whether you use built-in components or build your own interface, your Bootstrap
knowledge applies directly — no new UI system to learn.

For full setup and documentation, see [Docs (coming soon)](#).

## Project Structure

```
pinmok/
├── cmfadmin/       # Core app: menus, permissions, themes, site config
├── content/        # Content management app (optional)
├── ...             # Other optional apps
└── manage.py
```

## Contributing

Issues and pull requests are welcome.

Repositories:

- GitHub: [github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee: [gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)