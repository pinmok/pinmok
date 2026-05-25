# 快速开始

本节将引导你在一个全新的 Django 项目中完成 Pinmok 的安装与基础配置，最终跑起一个带有菜单的后台管理界面。

## 环境要求

以下为推荐运行环境，低于此版本未经测试，不保证正常运行。

- Python >=3.12
- Django >= 5.2 （已兼容最新版本，低版本未测试，暂不推荐）

### 依赖

- pillow >= 10.0
- filetype >= 1.0.10
- polib >= 1.1.0 （多语言 msgid 去重，按需安装）

## 安装

### 通过 pip 安装（推荐）

确保你的 Django 环境已激活，然后执行：

```bash
pip install pinmok
```

### 通过源码安装

如果你希望查看源码，或参与 Pinmok 本身的开发，可以从 GitHub 或 码云 克隆仓库：

```bash
# GitHub
git clone https://github.com/pinmok/pinmok.git

# Gitee
git clone https://gitee.com/pinmok/pinmok.git
```

克隆完成后，进入仓库根目录，安装到当前环境：

```bash
cd pinmok
pip install .
```

如果你需要修改 Pinmok 源码并希望改动立即生效，使用可编辑模式安装：

```bash
pip install -e .
```

### 将源码直接集成到项目中

如果你希望将 Pinmok 源码直接放入自己的项目（例如需要深度定制），可以不通过 pip，手动将源码复制到项目目录中。

需要注意的是，pinmok 是一个 命名空间包，目录下没有 __init__.py，这是有意为之。Pinmok 的各个应用（如
padmin、content）都位于这个命名空间下，依赖命名空间包机制才能独立安装、自由组合。

正确的目录结构如下：

```text
myproject/
├── manage.py
├── myproject/
├── your_app/
└── pinmok/             ← 命名空间目录，不含 __init__.py
    ├── core/           ← 核心模块，随 Pinmok 一同包含在仓库中
    ├── padmin/         ← 后台管理模块，Pinmok 功能代码
    └── content/        ← 其他 Pinmok 应用同样放在此处
```

## 配置

### settings.py 文件

#### 注册应用

在 `settings.py` 的 `INSTALLED_APPS` 中，将 `pinmok.padmin` 放在 `django.contrib.admin`之前，推荐放在应用列表的最顶部。另外，确保以下应用已注册：

```python
INSTALLED_APPS = [
    'pinmok.padmin',  # ← 添加在 django.contrib.admin 之前 
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

#### 国际化

Pinmok 支持国际化，配置方式与 Django 原生一致。如需多语言，请确保正确配置 LANGUAGE_CODE、LANGUAGES，并添加 LocaleMiddleware。

### urls.py 文件

在项目的 `urls.py` 中注册 Pinmok 的路由，将内容改为以下的样子：

```python
from django.urls import path, include

from pinmok.core import admin
from pinmok.padmin.views import alias_resolver

urlpatterns = [
    path('admin/', admin.site.urls),
    # 其它路由定义
]

# 注意：alias_resolver 必须始终是最后一个定义。
# <path:alias> 匹配所有内容 — 在它之后注册的任何路由都将永远无法访问。
urlpatterns += [
    path('<path:alias>', alias_resolver, name='alias_resolver'),
]
```

**说明**

- 将 `admin` 的引入由 `from django.contrib import admin` 改为 `from pinmok.core import admin`。Pinmok 特意创建了一个 admin.py
  文件，用来模拟引入，因此你可以保留以前的习惯。
- 在所有路由的最后，添加 `<path:alias>` 路由的定义。这是为路由别名而使用的，它会拦截所有在前方未命中的路由定义，鉴别是否定义了别名，如果仍未命中则抛出404错误。
  **如果你明确不使用 URL 别名，或者有自己的处理方式，那么这条定义可以完全忽略。**

### 执行迁移

```bash
python manage.py migrate
```

### 创建超级用户

```bash
python manage.py createsuperuser
```

## 启动

```bash
python manage.py runserver
```

- 访问 `http://127.0.0.1:8000` ，即可以访问站点首页。
- 访问 `http://127.0.0.1:8000/admin/` ，使用刚才创建的账号登录，即可看到 Pinmok 后台界面。

## 第一个应用

下面以一个简单的 `blog` 应用为例，演示如何在 Pinmok 中快速建立应用。

### 创建应用

```bash
python manage.py startapp blog
```

在 `settings.py` 中注册：

```python
INSTALLED_APPS = [
    # 其它APP
    'blog',
]
```

### 注册模型

在 `blog/admin.py` 中注册模型：

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

虽然模型可以使用 Django 的 admin注册，但强烈建议使用 Pinmok 的 padmin 注册。

### 同步菜单

即使应用未定义 menus.py，同步后 Pinmok 也会自动以应用的 verbose_name 作为根菜单，与 Django Admin 的默认行为保持一致。
以超级管理员身份登录后台，点击顶部导航栏的 `☰` **同步菜单** 按钮，即可在左侧导航中看到刚才定义的博客管理菜单。

> 每次新增或修改 `menus.py` 后，都需要手动同步一次菜单。