# Pinmok

**Feels like Django. Barely any learning.**

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

English | [中文](README.zh-CN.md)

---

## What is Pinmok

Django Admin has a fundamental constraint: the admin interface is built around your models. Navigation derives from your data structure, and
the moment your business logic outgrows basic CRUD, you end up spending more time fighting the framework than building your product.

Pinmok removes that constraint. The admin is no longer a reflection of your database schema — it's organized around your business. Menu
structure, page entries, and navigation hierarchy are all yours to define. A single business section can span multiple models, or none at
all. If a feature has no model behind it, it can still have its own place in the admin. The way your backend is organized follows how your
product works, not how your tables are laid out. Add a new business module and the admin grows with it — the same way adding a Django app
adds a new set of routes, at no extra cost.

None of this replaces what Django Admin already does. Registration, permissions, URL structure — all untouched. Pinmok works from the
inside, not on top.

If you know Django, you already know Pinmok.

---

## What it does

- **Admin organized around your business, not your models**

  Menu structure, page entries, and navigation depth are all defined by you. A business section can span multiple models or share one across
  sections. Features with no model at all can still have a dedicated admin page. Your backend is shaped by what your product does, not by
  what your database looks like.

- **Internationalization built in**

  The admin interface ships with full i18n support. No extra configuration needed to serve users in different languages.

- **Menus and access control in one place**

  Each app defines its own menu items, which merge automatically with Django Admin's native navigation. You control the order. Defining a
  menu entry also defines the access rule — menu visibility and URL-level permissions share the same definition, set once and enforced
  everywhere.

- **Site configuration that lives in the admin**

  Site name, logo, feature flags, and similar settings can be changed directly in the admin interface. Save and it takes effect
  immediately — no code changes, no redeployment.

- **A modern interface built on tools you already know**

  The UI is rebuilt on Bootstrap 5 / Tabler. Business pages use standard HTML and CSS components. No new frontend framework to learn.

- **Modular by design**

  The core and admin modules are independent. Install what you need, combine as you like. Each piece works on its own, and removing one
  doesn't break the others.

- **Extension points for developers**

  Common customization hooks and utilities are built in, covering most admin extension scenarios without requiring you to reimplement the
  same patterns from scratch.

---

## Requirements

- Python >= 3.12
- Django >= 5.2

**Dependencies**

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0 (msgid deduplication for i18n — install only if needed)

---

## Installation

### pip

```bash
pip install pinmok
```

### Source integration

If you need to modify the framework itself, you can bring the source directly into your project:

```bash
git clone https://github.com/pinmok/pinmok.git
```

Copy the `pinmok/` directory into your project. **Do not** add an `__init__.py` under `pinmok/` — this is intentional and required for the
namespace package mechanism to work correctly.

For full setup instructions, see the documentation.

---

## Documentation & Resources

- Docs: [docs.pinmok.com](https://docs.pinmok.com)
- Website: [www.pinmok.com](https://www.pinmok.com)

---

## Contributing

Pinmok is still early. A lot will become clearer as it gets used in the real world. If you find it useful, PRs and issues are welcome. If
you don't have anything specific to contribute right now, a Star goes a long way — it helps other people find the project.

- GitHub: [github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee: [gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)

---

## License

[MIT License](LICENSE)