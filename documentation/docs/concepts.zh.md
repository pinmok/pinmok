# 核心概念

## 架构概览

Pinmok 构建在 Django Admin 之上，并非替换，而是对其进行扩展和封装。开发者如果完全按照 Django Admin 去开发，则等同于后台更换了皮肤，因此你完全不必担心兼容性问题。

Pinmok 提供了自己的 AdminSite，为了让开发者更容易上手，仍然沿用 Django 的命名习惯。 Pinmok 与原生的 admin.site 互不干扰，甚至可以并存，它只是提供了一个新的站点。

你只需要按照 Pinmok 的约定开发自己的应用，框架会自动接管菜单、权限等通用能力， 让你专注于业务逻辑本身。

## 命名空间包

Pinmok 的各功能模块以命名空间包的方式组织，顶层目录 `pinmok/` 下没有 `__init__.py`，这是有意为之。

```text
pinmok/          ← 命名空间目录，不含 __init__.py
├── core/        ← 核心模块
├── padmin/      ← 后台管理模块
└── content/     ← 内容管理模块（独立安装）
```

这样设计的好处是：每个子模块（`pinmok.padmin`、`pinmok.content` 等）可以作为独立的 Python 包单独发布和安装，而它们在导入时共享同一个 `pinmok`
命名空间，彼此不干扰。Pinmok 官方后续发布的模块也遵循这一规则。第三方开发者发布的应用无需放在此命名空间下，同样可以正常接入 Pinmok。

```bash
# 只安装核心后台
pip install pinmok

# 按需安装其他模块
pip install pinmok-content
```

> **注意**：如果你将 Pinmok 源码直接复制到项目目录中，请确保 `pinmok/` 目录下没有 `__init__.py`，否则命名空间机制将失效。

## 应用约定

Pinmok 采用约定优于配置的设计思路。框架提供了一系列可选的约定，用户按自己的实际需求，选择使用相应的约定。

### 模型管理

提供了 `PinmokModelAdmin`、`PinmokStackedInline` 和 `PinmokTabularInline`，分别对应 Django 原生的 `ModelAdmin`、`StackedInline` 和
`TabularInline`。对于已有的 `ModelAdmin`，框架会自动兼容，无需任何改动。

### 后台菜单

提供了后台菜单注册能力，开发者只需调用内置的注册函数，即可自动在后台生成并展示对应的菜单项。

### 后台路由

提供了后台路由注册机制，允许开发者在应用中定义自己的后台路由，框架会统一将其纳入后台路由体系，自动处理权限验证与登录保护。

### 模板继承

对后台界面进行了统一扩展，包括 JS 交互、消息通知等。只需继承 `admin/base.html` 或 `admin/base_site.html`，即可自动获得这些能力。

### 全局上下文扩展

提供了 `extend_admin_context` 信号，用于扩展后台全局上下文，允许开发者向其中注入自定义数据。

### API 响应

约定了统一的 JSON 响应格式，提供了标准的成功与失败输出方法，便于开发者在自己的应用中保持一致的 API 风格。

### API 视图权限

提供了 `PinmokPermissionMixin`，用于后台 API 类视图的权限控制，适合开发者在自己的 API 视图中使用，自动处理无权限时的跳转与 AJAX 响应。框架默认要求
`is_staff`，开发者也可以通过 `permission_checker.register()` 注入自定义的权限检查逻辑。

### 模板管理

提供了一套扩展的模板管理，即主题管理，允许开发者为同一个前端提供多套模板，随时切换主题。

### 配置管理

提供了 `ConfigModelAdmin`，适用于键值对形式的数据结构，支持按类别分页管理，可以方便管理配置信息。

### 多语言模型

提供了透明的多语言翻译层，开发者只需让主表继承 `TranslatableModel`，翻译表继承 `TranslationModel`，并按约定定义外键与字段，即可自动获得多语言支持。