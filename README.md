# <img src="https://www.pinmok.com/assets/img/pinmok.bg.svg" height="60" alt="Pinmok"> Pinmok

[English](#English) | [简体中文](#简体中文)

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)


---

## English

**Feels like Django. Barely any learning.**

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

---

## 简体中文

**像Django一样，一学就会。**

## Pinmok 是什么

Django Admin 有一个根本性的约束：后台界面围绕 Model 定义生成，菜单结构与数据模型绑定，导航逻辑自动派生。业务复杂度一旦超出 CRUD
范畴，开发者便需要投入大量精力与框架的默认实现进行博弈。

Pinmok 改变了这一局面，解开了这一耦合。后台不再作为 Model 层的映射存在，而是回归业务本身，由业务逻辑主导。菜单结构可以按业务需求自由编排——既可以沿用
ModelAdmin，也可以完全自定义，甚至某个功能没有对应的 Model，同样可以在 Admin 中占据独立入口。后台的组织方式由业务需求驱动，而非由数据表结构决定。每新增一个业务模块，
Admin 即自动扩展对应的功能区域，如同 Django 中添加一个 app 即新增一条路由，机制一致且无额外成本。

同时，原有的 Admin 注册方式、权限体系、URL 结构完全保留。Pinmok 做的是内部赋能，而非上层替换。

因此，Django 的使用者，即 Pinmok 的使用者。

---

## 它能做什么

- **后台由业务定义，而非由 Model 定义**

  菜单结构、页面入口、导航层级，全部按业务逻辑自由编排。一个业务模块可以跨多个 Model，多个业务模块也可以共享同一个 Model；即便某个功能完全没有对应的
  Model，同样可以在 Admin 中拥有独立页面。后台的组织方式由业务需求驱动，而非由数据表结构决定。

- **原生多语言支持**

  后台界面内置多语言机制，无需额外配置即可适配不同语言环境。

- **菜单与权限统一配置**

  每个应用独立定义自己的菜单项，与 Django Admin 原生菜单自动融合，顺序由你控制。菜单定义的同时即完成访问控制配置——菜单可见性与 URL
  权限基于同一份定义，一处设定，全局生效。

- **站点配置在后台实时修改**

  站点名称、Logo、功能开关等配置项，直接在后台界面修改，保存即生效，无需改动代码，无需重新部署。

- **现代化界面，复用前端知识**

  UI 基于 Bootstrap 5 / Tabler 重写，编写业务页面时使用标准 HTML 与 CSS 组件，无新增前端框架学习成本。

- **模块化设计，按需组合**

  核心模块与后台功能模块相互独立，可单独安装，按需组合。装上即用，移除不影响其他模块运行。

- **面向开发者提供标准扩展接口**

  预留常用扩展点与实用接口，覆盖多数后台定制场景，减少重复实现，保持代码整洁。

---

## 环境要求

- Python >= 3.12
- Django >= 5.2

**依赖**

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0（i18n msgid 去重，按需安装）

---

## 安装

### pip 安装

```bash
pip install pinmok
```

### 源码集成

如果需要修改框架本身，可以将源码直接集成进项目：

```bash
git clone https://github.com/pinmok/pinmok.git
```

将 `pinmok/` 目录复制到项目中，**不要**在 `pinmok/` 下添加 `__init__.py`，这是命名空间包的标准用法。

完整配置说明请参阅文档。

---

## 文档与资源

- 文档：[docs.pinmok.com](https://docs.pinmok.com)
- 官网：[www.pinmok.com](https://www.pinmok.com)

---

## 参与贡献

Pinmok 还处于早期阶段，很多事情会在实际使用中逐渐明朗。如果你觉得这个项目有价值，欢迎提交 PR 或 Issue，
如果暂时没什么好说的，点个 Star 也不错——至少能让这个项目更容易被其他人找到。

- GitHub：[github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee：[gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)

---

## 许可证

[MIT License](LICENSE)