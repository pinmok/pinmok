# 附录

Pinmok 的部分内置功能相对独立，尚不足以单独成章，但在实际开发中同样不可或缺。随着项目持续演进，其中某些功能会逐步扩展为独立章节，附录的内容也会随之更新。

## 后台上下文扩展

后台页面往往需要共享一些全局数据，例如当前用户的菜单、站点配置或业务状态。如果由各个视图自行处理，同样的逻辑就会分散在项目各处，难以维护。为此，Pinmok
重写了 Django Admin 的 `each_context()` 方法，并在其中引入了一个专属信号机制。

### `extend_admin_context` 信号

该信号由 `PinmokAdminSite` 在每次调用 `each_context()` 时发出，`sender` 为 `PinmokAdminSite` 类本身。接收方通过直接修改 `context`
字典注入数据，无需返回值。

**信号参数：**

| 参数        | 类型            | 说明                               |
|-----------|---------------|----------------------------------|
| `sender`  | `type`        | 信号发送方，即 `PinmokAdminSite` 类      |
| `request` | `HttpRequest` | 当前请求对象                           |
| `context` | `dict`        | 后台共享上下文字典，直接调用 `update()` 注入数据即可 |

**监听示例：**

```python
from django.dispatch import receiver
from pinmok.core.signals import extend_admin_context


@receiver(extend_admin_context)
def inject_my_context(sender, request, context, **kwargs):
    context.update({
        'my_key': 'my_value',
    })
```

接收函数签名中必须包含 `**kwargs`，这是 Django 信号机制的要求，用于兼容未来可能新增的信号参数。

---

## 邮件服务

Pinmok 内置了一个邮件服务类 `EmailService`，封装了邮件发送逻辑。它的核心作用是将 SMTP 配置的读取方式从 `settings.py`
改为从后台站点配置中读取，让终端用户可以在管理后台直接维护邮件配置，而无需修改代码。开发者只需调用 `EmailService`，实际的发送参数由用户在后台设置。

引入路径：

```python
from pinmok.padmin.service.email import EmailService
```

当前版本的 EmailService 封装了基本的发送接口，支持普通邮件发送和模板变量替换，满足常见的业务邮件需求。

### 配置优先级

`EmailService` 初始化时会自动判断使用哪套 SMTP 配置，规则如下：

| 数据库配置 | settings 配置 | 实际使用               |
|-------|-------------|--------------------|
| 有     | 有           | 数据库配置优先            |
| 有     | 无           | 数据库配置              |
| 无     | 有           | settings 配置        |
| 无     | 无           | Django 默认值（发送可能失败） |

### 发送普通邮件

#### `send(to, subject, content)`

```python
from pinmok.padmin.service.email import EmailService

service = EmailService()
service.send(
    to='user@example.com',
    subject='Hello',
    content='<p>This is a test email.</p>',
)
```

发送一封 HTML 邮件。发件人地址从后台站点配置中读取，无需手动传入。邮件内容支持 HTML，Django 会将 `content_subtype` 设置为 `html`，收件方邮件客户端将以
HTML 格式渲染正文。

**参数：**

| 参数        | 类型    | 说明                       |
|-----------|-------|--------------------------|
| `to`      | `str  | list[str]`               | 收件人地址，支持单个地址或地址列表        |
| `subject` | `str` | 邮件主题，必填，不发送主题时传空字符串 `''` |
| `content` | `str` | 邮件正文，支持 HTML             |

**返回值：** `int`，成功发送的邮件数量。

---

### 发送模板邮件

#### `send_with_template(to, subject, content, template_params=None)`

```python
service.send_with_template(
    to='user@example.com',
    subject='您好 ${username}，您有一条新消息',
    content='<p>您的验证码为：<strong>${verify_code}</strong>，请在 10 分钟内使用。</p>',
    template_params={
        'username': 'Tomas',
        'verify_code': '123456',
    }
)
```

在普通邮件发送的基础上，对 `subject` 和 `content` 中的占位变量进行替换后再发送。占位符格式为 `${var_name}`，未匹配到的占位符会原样保留在邮件中。模板内容由调用方传入，
`EmailService` 只负责变量替换和发送，不从后台读取模板。

若不传 `template_params`，或 `template_params` 为空，则 `subject` 和 `content` 原样发送，效果与 `send()` 相同。

**参数：**

| 参数                | 类型              | 说明                 |
|-------------------|-----------------|--------------------|
| `to`              | `str            | list[str]`         | 收件人地址，支持单个地址或地址列表                     |
| `subject`         | `str`           | 邮件主题，支持占位变量，必填     |
| `content`         | `str`           | 邮件正文，支持 HTML 和占位变量 |
| `template_params` | `dict[str, str] | None`              | 变量替换字典，key 为变量名，value 为替换值，默认为 `None` |

**返回值：** `int`，成功发送的邮件数量。

**异常：** 若后台模板变量声明与 `template_params` 不一致，抛出 `EmailValueError`。建议在业务代码中捕获处理：

```python
from pinmok.padmin.service.email import EmailService, EmailValueError

service = EmailService()
try:
    service.send_with_template(
        to='user@example.com',
        subject='您好 ${username}',
        content='<p>验证码：${verify_code}</p>',
        template_params={'username': 'Tomas', 'verify_code': '123456'},
    )
except EmailValueError as e:
    # 处理变量缺失错误
    print(e)
except Exception as e:
    # 处理其它发送错误
    print(e)
```

---

## 后台 URL 注册

Django 后台视图并非普通视图——每一个后台 URL 都需要经过登录校验、权限检查和 CSRF 保护等处理，这些逻辑由 `AdminSite.admin_view()`
统一负责。如果开发者直接在项目路由中注册后台视图而绕过这层包裹，轻则功能异常，重则产生安全漏洞。

Pinmok 重写了 `AdminSite.get_urls()`，提供了一套约定：在应用的 `urls.py` 中声明 `admin_urlpatterns` 变量，Pinmok 会在启动时自动扫描并读取，为每个
URL 包裹 `admin_view()`，最终注册到后台路由中。开发者只需专注于视图逻辑本身，权限处理由框架统一接管。

以下情况不需要使用 `admin_urlpatterns`：

- 普通的前台 URL，与后台无关，按正常方式在项目路由中注册即可。
- 你已有自己的后台权限处理实现，不需要 Pinmok 代劳。

### 定义方式

在应用的 `urls.py` 中声明模块级变量 `admin_urlpatterns`，值为标准的 URL 模式列表：

```python
# myapp/urls.py
from django.urls import path
from . import views

admin_urlpatterns = [
    path('dashboard/', views.dashboard, name='myapp-dashboard'),
    path('export/', views.export, name='myapp-export'),
]
```

Pinmok 启动时自动扫描所有已安装应用的 `urls.py`，读取 `admin_urlpatterns` 并注册到后台 URL 配置中。最终这些 URL 会注册在应用的命名空间下：

```
/admin/myapp/dashboard/
/admin/myapp/export/
```

### 自动权限包裹

列表中每一个 `URLPattern` 条目，Pinmok 会自动用 `admin_view()` 包裹其视图函数，确保访问时强制进行登录校验和权限检查，无需开发者手动处理。

### 使用 `include()` 的情况

如果某个条目是通过 `include()` 引入的 URL 组（即 `URLResolver`），Pinmok **不会**对其进行 `admin_view()`
包裹，而是直接注册。这是有意为之的灵活出口：当你有自定义的权限处理逻辑时，可以通过 `include()` 引入自己的 URL 组，并在其中自行管理权限。

```python
# myapp/urls.py
from django.urls import path, include
from . import views, api_urls

admin_urlpatterns = [
    # 普通视图：由 Pinmok 自动包裹 admin_view()
    path('dashboard/', views.dashboard, name='myapp-dashboard'),

    # 自定义权限处理：Pinmok 不干预，由开发者自己负责
    path('api/', include(api_urls)),
]
```

!!! warning "警告"

    使用 `include()` 时，请确保被引入的 URL 组中已包含完善的权限校验逻辑，否则相关视图将对所有用户开放访问。

---

## PinmokPermissionMixin

`PinmokPermissionMixin` 是一个类视图 Mixin，用于对无法通过 `admin_view()` 覆盖的视图进行权限控制，典型场景是 AJAX 接口。

### 使用方式

继承 `PinmokPermissionMixin` 并在类中声明 `permission` 属性：

```python
from pinmok.core.mixins import PinmokPermissionMixin
from django.views import View


class MyAjaxView(PinmokPermissionMixin, View):
    permission = 'myapp.can_do_something'
```

`permission` 为可选项，设为 `None` 时仅做登录校验，不检查具体权限。

### 行为说明

权限检查在 `dispatch` 阶段执行，校验不通过时：

- AJAX 请求（请求头包含 `X-Requested-With: XMLHttpRequest`）返回 JSON 格式的 401 响应。
- 普通请求重定向到登录页。

### 注意事项

`PinmokPermissionMixin` 使用的是 Pinmok 自己的 `permission_checker`，与 Django `admin_view()` 是两套独立的权限机制，请勿混用。
`permission_checker` 支持自定义替换，详见权限章节。