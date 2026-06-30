# 入门

如果你熟悉 Django，可以展开下方的**快速开始**，无需阅读正文。

??? abstract "快速开始"

    **1. 安装**

    ```bash
    pip install pinmok
    ```

    **2. `settings.py` —— `INSTALLED_APPS` 顶部添加**
    
    ```python
    INSTALLED_APPS = [
        'pinmok.padmin',  # 放在 django.contrib.admin 之前
        'django.contrib.admin',
        # ...
    ]
    ```
    
    **3. `urls.py` —— 替换 admin 引入**
    
    - 用 pinmok 的 `admin` 替换原有的 `from django.contrib import admin`
    - 最底部添加别名解析，不需要路由别名功能可以忽略，不添加
    
    ```python
    from django.urls import path
    from pinmok.core import admin  # 替换为 pinmok 的 admin
    from pinmok.padmin.views import alias_resolver
    
    urlpatterns = [
        path('admin/', admin.site.urls),
        # 其它路由定义
    ]
    
    # 该功能用于路由别名，不需要该功能可以忽略
    urlpatterns += [
        path('<path:alias>', alias_resolver, name='alias_resolver'),
    ]
    ```
    
    **4. 迁移、建账号、启动**
    
    ```bash
    python manage.py migrate # 迁移
    python manage.py createsuperuser # 创建管理员账号
    python manage.py runserver # 启动服务
    ```
    
    访问 `http://127.0.0.1:8000/admin/` ，用刚才创建的账号登录，即可看到 Pinmok 后台。

---

## 环境要求

在开始之前，确认你的环境满足以下要求：

- Python >= 3.12
- Django >= 5.2

Pinmok 的核心依赖会随 pip 自动安装，无需手动处理：

- pillow >= 10.0
- filetype >= 1.0.10

> Pinmok提供了一个多语言翻译文件去重工具，该工具会去除`po`文件中，与系统相同的 msgid 翻译，以减小翻译文件的体积。
> 如果你的项目涉及多语言，并且有去除重复翻译的需求，那么还需要安装 `polib` 依赖：
> ```bash
> pip install polib
> ```

## 安装

### 通过 pip 安装（推荐）

进入 Django 项目虚拟环境，执行：

```bash
pip install pinmok
```

### 通过源码安装

如果你想查看源码，或者参与 Pinmok 本身的开发，可以从代码仓库克隆：

```bash
# GitHub
git clone https://github.com/pinmok/pinmok.git

# Gitee
git clone https://gitee.com/pinmok/pinmok.git
```

克隆完成后进入目录，安装到当前环境：

```bash
cd pinmok
pip install .
```

如果你需要修改 Pinmok 的代码并让改动立即生效，用可编辑模式安装：

```bash
pip install -e .
```

### 将源码直接集成到项目

有时候你需要对 Pinmok 做深度定制，或者不方便通过 pip 管理依赖，可以把源码直接放进项目目录。

这里有一点需要注意：`pinmok` 是一个**命名空间包**，它的目录下没有 `__init__.py`，这不是遗漏，是有意为之。Pinmok 的各个功能模块（`padmin`、`content`
等）都挂在这个命名空间下，靠这个机制才能做到独立安装、按需组合。如果你在 `pinmok/` 目录下添加了 `__init__.py`，命名空间包机制会被破坏，导致各模块无法正常加载。

目录结构应当是这样的：

```text
myproject/
├── manage.py
├── myproject/          ← 你的配置文件目录
├── your_app/           ← 你的应用目录
└── pinmok/             ← 命名空间目录，不含 __init__.py
    ├── core/
    ├── padmin/
    └── content/        ← 其他 Pinmok 模块同样放在这里
```

## 配置

### settings.py

#### 注册应用

将 `pinmok.padmin` 加入 `INSTALLED_APPS`，位置必须在 `django.contrib.admin` 之前：

```python title="settings.py"
INSTALLED_APPS = [
    'pinmok.padmin',  # 必须在 django.contrib.admin 之前
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

顺序很重要。Pinmok 需要在 Django Admin 初始化之前完成自身的注册，放在列表顶部是最稳妥的做法。

#### 国际化（可选）

如果你的项目需要多语言支持，Pinmok 的配置方式与 Django 原生完全一致，正确设置 `LANGUAGE_CODE`、`LANGUAGES`，并在 `MIDDLEWARE` 中加入
`LocaleMiddleware` 即可。Pinmok 不引入任何额外的国际化配置项，具体设置方法请参阅 Django 相关资料。

### urls.py

打开项目的 `urls.py`，做如下改动：

**替换 admin 的引入方式。**

```python
# 将原来的
from django.contrib import admin

# 改为
from pinmok.core import admin
```

Pinmok 在 `pinmok/core/admin.py` 里提供了一个同名模块，模拟了 Django 原生的引入方式，所以这一行改掉之后，其余代码不需要任何调整。

这里的 `admin.site` 是 Pinmok 扩展过的站点实例，它继承并替换了 Django 原生的 `AdminSite`，Pinmok 的菜单、权限和页面注册机制都依赖它——如果仍然使用原生的
`from django.contrib import admin`，这些功能不会生效。

**追加别名路由**

如果需要路由别名功能，则需要最文件底部添加如下代码：

```python
from pinmok.padmin.views import alias_resolver

# 放在 urlpatterns 最后
urlpatterns += [
    path('<path:alias>', alias_resolver, name='alias_resolver'),
]
```

`alias_resolver` 用于处理 URL 别名——你可以给后台页面配置一个更友好的路径，访问时由它负责转发。它使用了 `<path:alias>`
这个通配模式，会拦截所有前面未匹配的请求，因此必须放在最后。如果放在前面，它会把其他路由的请求全部截走。

如果你的项目确认不使用 URL 别名，这一条可以省略。

完整的 `urls.py` 看起来像这样：

```python title="urls.py"
from django.urls import path
from pinmok.core import admin
from pinmok.padmin.views import alias_resolver

urlpatterns = [
    path('admin/', admin.site.urls),
    # 其它路由定义
]

urlpatterns += [
    path('<path:alias>', alias_resolver, name='alias_resolver'),
]
```

## 迁移与初始化

配置完成后，执行数据库迁移：

```bash
python manage.py migrate
```

Pinmok 会在迁移时创建所需的数据表，包括菜单、权限和站点配置相关的表。

然后创建超级管理员账号：

```bash
python manage.py createsuperuser
```

根据提示，输入超级管理员用户名和密码，该账号用于登录后台使用。

## 启动

```bash
python manage.py runserver
```

浏览器访问 `http://127.0.0.1:8000/admin/` ，用刚才创建的超级管理员账号登录。

## 同步菜单

如果一切正常，你会看到 Pinmok 的后台界面——左侧是导航菜单区域，右侧为内容区。此时菜单条目可能不完整，需要执行一次同步。

点击位于左侧菜单栏顶部的同步菜单按钮（☰），Pinmok 会自动扫描所有已安装应用的 menus.py，将菜单项写入数据库并刷新缓存。同步完成后，完整的菜单结构将立即显示。

![Pinmok后台界面](/assets/images/admin.zh.png)

---
安装完成，你可以开始使用 Pinmok 了。