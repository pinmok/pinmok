# Core Concepts

## Architecture Overview

Pinmok is built on top of Django Admin — not as a replacement, but as its extension and enhancement. If you fully follow Django Admin
development conventions, the result is essentially a reskinned admin interface, so there is no need to worry about compatibility.

Pinmok provides its own AdminSite while adhering to Django's native naming conventions to lower the learning curve. It coexists with the
native `admin.site` without interference — it simply provides a new site instance.

You only need to follow Pinmok's conventions when developing your own apps. The framework will automatically take over common
responsibilities such as menus and permissions, letting you focus on business logic.

## Namespace Package

Pinmok's modules are organized as a namespace package. The top-level `pinmok/` directory intentionally contains no `__init__.py`.

```text
pinmok/          ← namespace directory, no __init__.py
├── core/        ← core module
├── padmin/      ← admin module
└── content/     ← content module (installed separately)
```

This design allows each sub-module (`pinmok.padmin`, `pinmok.content`, etc.) to be published and installed as an independent Python package,
while sharing the same `pinmok` namespace at import time without conflict. Official Pinmok modules follow this convention. Third-party apps
do not need to reside within this namespace to integrate with Pinmok.

```bash
# Install the core admin module
pip install pinmok

# Install additional modules as needed
pip install pinmok-content
```

> **Note**: If you copy the Pinmok source directly into your project, make sure there is no `__init__.py` inside the `pinmok/` directory, or
> the namespace mechanism will stop working.

## App Conventions

Pinmok follows a convention-over-configuration approach. All conventions are optional — use only what your app needs.

### Model Admin

Provides `PinmokModelAdmin`, `PinmokStackedInline`, and `PinmokTabularInline`, corresponding to Django's native `ModelAdmin`,
`StackedInline`, and `TabularInline`. Existing `ModelAdmin` classes are automatically compatible — no changes required.

### Admin Menu

Provides a menu registration mechanism. Developers simply call the built-in registration function, and the corresponding menu items will be
automatically generated and displayed in the admin interface.

### Admin URLs

Provides an admin URL registration mechanism. Developers can define their own admin routes within an app, and the framework will
automatically include them in the admin URL structure with built-in permission verification and login protection.

### Template Inheritance

Pinmok extends the admin interface with unified JS interactions, toast notifications, and more. Simply inherit from `admin/base.html` or
`admin/base_site.html` to gain these capabilities automatically.

### Global Context Extension

Provides the `extend_admin_context` signal for extending the global admin context, allowing developers to inject custom data into every
admin page.

### API Response

Defines a unified JSON response format with standard success and error response utilities, helping developers maintain a consistent API
style across their apps.

### API View Permission

Provides `PinmokPermissionMixin` for permission control in class-based API views. It automatically handles redirects for unauthorized
regular requests and returns JSON-formatted 401 responses for AJAX requests. The default checker requires `is_staff`; a custom checker can
be registered via `permission_checker.register()`.

### Theme Management

Provides an extended template management system — also referred to as theme management — allowing developers to offer multiple template sets
for the same frontend and switch between them at any time.

### Config Admin

Provides `ConfigModelAdmin` for key-value data structures, with support for category-based pagination, making it convenient for managing
configuration data.

### Translatable Models

Provides a seamless translation layer. Developers inherit `TranslatableModel` for the main table and `TranslationModel` for the translation
table, then follow the field conventions — and multi-language support is handled automatically.