# Getting Started

This section will guide you through installing and configuring Pinmok in a Django project, and get a working admin interface up and running.

## Requirements

The following are the recommended runtime environments. Versions below these have not been tested and are not guaranteed to work.

- Python >= 3.12
- Django >= 5.2 (compatible with the latest version; older versions are untested and not recommended)

### Dependencies

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0 (for multilingual msgid deduplication, install as needed)

## Installation

### Via pip (Recommended)

Make sure your Django environment is activated, then run:

```bash
pip install pinmok
```

### From Source

If you want to browse the source code or contribute to Pinmok itself, clone the repository from GitHub or Gitee:

```bash
# GitHub
git clone https://github.com/pinmok/pinmok.git

# Gitee
git clone https://gitee.com/pinmok/pinmok.git
```

Once cloned, navigate to the repository root and install into your current environment:

```bash
cd pinmok
pip install .
```

If you need to modify the Pinmok source code and have changes take effect immediately, use editable mode:

```bash
pip install -e .
```

### Integrating Source Code Directly into Your Project

If you want to embed Pinmok's source code directly into your project (for example, for deep customization), you can skip pip and copy the
source manually.

Note that `pinmok` is a **namespace package** — it intentionally has no `__init__.py`. All Pinmok applications (such as `padmin` and
`content`) live under this namespace, relying on the namespace package mechanism to be installed independently and composed freely.

The correct directory structure is as follows:

```text
myproject/
├── manage.py
├── myproject/
├── your_app/
└── pinmok/             ← namespace directory, no __init__.py
    ├── core/           ← core module, included in the repository
    ├── padmin/         ← admin module, main Pinmok functionality
    └── content/        ← other Pinmok applications go here
```

## Configuration

### settings.py

#### Registering Applications

In `INSTALLED_APPS`, place `pinmok.padmin` before `django.contrib.admin`. It is recommended to put it at the very top of the list. Make sure
the following apps are all registered:

```python
INSTALLED_APPS = [
    'pinmok.padmin',  # ← must come before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

#### Internationalization

Pinmok supports internationalization using the same configuration as Django. If your project requires multiple languages, make sure
`LANGUAGE_CODE` and `LANGUAGES` are properly configured, and that `LocaleMiddleware` is added.

### urls.py

Update your project's `urls.py` to look like the following:

```python
from django.urls import path, include

from pinmok.core import admin
from pinmok.padmin.views import alias_resolver

urlpatterns = [
    path('admin/', admin.site.urls),
    # other url definitions
]

# Note: alias_resolver must always be the last definition.
# <path:alias> matches everything — any route registered after it will be unreachable.
urlpatterns += [
    path('<path:alias>', alias_resolver, name='alias_resolver'),
]
```

**Notes**

- Replace `from django.contrib import admin` with `from pinmok.core import admin`. Pinmok provides an `admin.py` that mirrors the original
  import, so the rest of your code can stay exactly the same.
- Add the `<path:alias>` route at the very end of your URL definitions. This is used for URL aliasing — it intercepts any unmatched
  requests, checks whether an alias is defined, and raises a 404 if none is found. **If you do not use URL aliasing or have your own
  handling, this definition can be omitted entirely.**

### Run Migrations

```bash
python manage.py migrate
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

## Start the Server

```bash
python manage.py runserver
```

- Visit `http://127.0.0.1:8000` to access the site homepage.
- Visit `http://127.0.0.1:8000/admin/` and log in with the superuser account to see the Pinmok admin interface.

## Your First App

The following example uses a simple `blog` app to demonstrate how to get up and running with Pinmok.

### Create the App

```bash
python manage.py startapp blog
```

Register it in `settings.py`:

```python
INSTALLED_APPS = [
    # other apps
    'blog',
]
```

### Register Models

In `blog/admin.py`, register your models:

```python
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin
from .models import Post, Category


@padmin.register(Post)
class PostAdmin(PinmokModelAdmin):
    pass


@padmin.register(Category)
class CategoryAdmin(PinmokModelAdmin):
    pass
```

While models can be registered using Django's built-in admin, it is strongly recommended to use Pinmok's `padmin` instead.

### Sync the Menu

Even if the app does not define a `menus.py`, Pinmok will automatically use the app's `verbose_name` as the root menu entry after syncing,
consistent with Django Admin's default behavior. Log in as a superuser and click the **☰** sync menu button in the top navigation bar — the
registered models will appear in the left sidebar.

> Whenever you add or modify a `menus.py`, you need to manually sync the menu once.