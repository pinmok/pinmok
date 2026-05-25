# 附录

Pinmok 还附带多项轻量化扩展工具与实用小功能，相关内容统一收录于附录部分。

## 后台上下文扩展

Pinmok 扩展了 Django Admin 原生管理站点，重写了 each_context 上下文方法，并在此基础上引入了专属信号机制。开发者只需监听对应信号，
即可向后台上下文注入自定义数据，无需改动框架任何代码，注入的数据将在所有后台页面中统一可用。

### extend_admin_context

该信号在每次请求调用 each_context 时触发，接收方通过直接修改 context 字典注入数据，无需返回值。

#### 监听示例

```python
from django.dispatch import receiver
from pinmok.core.signals import extend_admin_context


@receiver(extend_admin_context)
def inject_my_context(sender, request, context, **kwargs):
    context.update({
        'my_key': 'my_value',
    })
```

#### 信号参数：

- sender：发送方类
- request：当前 HttpRequest 对象
- context：后台共享上下文字典，直接调用 update() 注入数据即可

## 邮件服务

Pinmok 内置邮件服务，封装了 Django 原生邮件发送逻辑，SMTP 配置从后台站点配置中读取，无需在 `settings.py` 中单独配置。

### 配置优先级

EmailService 初始化时会自动判断使用哪套配置，规则如下：

| 数据库配置 | settings 配置 | 实际使用               |
|-------|-------------|--------------------|
| 有     | 有           | 数据库配置优先            |
| 有     | 无           | 数据库配置              |
| 无     | 有           | settings 配置        |
| 无     | 无           | Django 默认值（发送可能失败） |

### 发送邮件

Pinmok 提供了一个邮件服务类，支持发送普通邮件和模板邮件。引入路径为：`pinmok.padmin.service.email`。

#### 普通邮件

常用的邮件发送，提供正常参数即可。使用示例如下：

```python
from pinmok.padmin.service.email import EmailService

service = EmailService()

# 最小发送，subject 可省略
service.send(to='user@example.com', content='<p>Hello</p>')

# 标准发送
service.send(
    to='user@example.com',
    subject='Hello',
    content='<p>This is a test email.</p>',
)
```

> 参数 `to` 支持单个地址字符串或地址列表，即 str 或 list[str]。发件人地址始终从后台站点配置中读取，无需手动传入。

#### 模板邮件

模板邮件支持在管理后台预设邮件固定正文，动态内容以占位变量标识。发送邮件时填入对应变量值，即可自动替换内容并完成发送，适合验证码、通知类等格式固定的业务邮件。

##### 1. 在后台配置模板

在后台管理界面，找到 `邮件设置`，右侧设置页下方，展开 `邮件模板`，默认情况下，它是折叠的。

- **发件人名称**：可选，填写后发件人将显示为：`名称<邮件地址>` 的格式，例如：`Pinmok<noreply@example.com>`。
- **主题**：邮件主题，支持变量占位符，例如：`您好 ${username}，您有一条新消息`。
- **内容**：邮件正文，支持 HTML，支持变量占位符，例如：`<p>您的验证码为：<strong>${verify_code}</strong>，请在 10 分钟内使用。</p>`
- **可用变量**：声明模板中使用的变量名，多个变量以英文逗号分隔，例如：`username, verify_code`。此处声明的变量名必须与调用时 `template_params` 中的
  key 完全一致，否则会抛出 `EmailValueError`。

> 变量占位符格式为 `${var_name}`，未匹配到的占位符会原样保留在邮件中。若后台未配置模板变量，`template_params` 可不传，模板内容将原样发送。

##### 2. 调用示例

```python
service.send_with_template(
    to='user@example.com',
    template_params={
        'username': 'Crazy',
        'verify_code': '123456',
    }
)
```

若后台模板中定义了变量但调用时未提供，会抛出 EmailValueError，建议在业务代码中捕获处理：

```python
from pinmok.padmin.service.email import EmailService, EmailValueError

try:
    service.send_with_template(to='user@example.com', template_params={'username': 'Crazy'})
except EmailValueError as e:
    # 处理变量缺失错误
    print(e)
except Exception as e:
    # 处理其它发送错误
    print(e)
```

## 后台 URL 定义

Django 的后台视图并非普通视图——每一个后台 URL 都需要经过登录校验、权限检查，以及 CSRF 保护等一系列处理，这些逻辑由 `AdminSite.admin_view()`
统一负责。如果开发者直接在项目路由中注册后台视图，绕过这层包裹，轻则功能异常，重则产生安全漏洞。

为此，Pinmok 重写了 `AdminSite.get_urls()`，提供了一套约定：在应用的 `urls.py` 中声明 `admin_urlpatterns` 变量，Pinmok 会在启动时自动扫描、读取，并为每个
URL 包裹 `admin_view()`，最终注册到后台路由中。这样开发者只需专注于视图逻辑本身，权限处理由框架统一接管。

如果你的 URL 属于以下情况，则不需要使用 `admin_urlpatterns`：

- 普通的前台 URL，与后台无关，按正常方式在项目路由中注册即可
- 你完全清楚后台权限的处理机制，并有自己的实现方式，不需要 Pinmok 代劳

### 定义方式

在应用的 `urls.py` 中，声明一个名为 `admin_urlpatterns` 的模块级变量，值为标准的 URL 模式列表：

```python
# myapp/urls.py
from django.urls import path
from . import views

admin_urlpatterns = [
    path("dashboard/", views.dashboard, name="myapp-dashboard"),
    path("export/", views.export, name="myapp-export"),
]
```

Pinmok 在启动时会自动扫描所有已安装应用的 `urls.py`，读取 `admin_urlpatterns` 并将其注册到后台 URL 配置中。

### 自动权限包裹

对于列表中的每一个 `URLPattern`，Pinmok 会自动用 `admin_view()` 包裹其视图函数，确保访问该 URL 时强制进行登录校验和权限检查，无需开发者手动处理。

最终这些 URL 会注册在应用的命名空间下：

```
/admin/myapp/dashboard/
/admin/myapp/export/
```

### 使用 `include()` 的情况

如果某个条目是 `URLResolver`（即通过 `include()` 引入的 URL 组），Pinmok **不会**对其进行 `admin_view()` 包裹，而是直接注册。

这是有意为之的灵活出口：当开发者有自定义的权限处理逻辑时，可以通过 `include()` 引入自己的 URL 组，并在其中自行管理权限。

```python
# myapp/urls.py
from django.urls import path, include
from . import api_urls

admin_urlpatterns = [
    # 普通视图：由 Pinmok 自动包裹 admin_view()
    path("dashboard/", views.dashboard, name="myapp-dashboard"),

    # 自定义权限处理：Pinmok 不干预，由开发者自己负责
    path("api/", include(api_urls)),
]
```

> 使用 `include()` 时，请确保被引入的 URL 组中已包含完善的权限校验逻辑，否则相关视图将对所有用户开放访问。

## PinmokPermissionMixin

`PinmokPermissionMixin` 是一个类视图 mixin，用于对无法通过 `admin_view()` 覆盖的视图进行权限控制，典型场景是 AJAX 接口。

### 使用方式

继承 `PinmokPermissionMixin`，并在类中声明 `permission` 属性：

```python
from pinmok.core.mixins import PinmokPermissionMixin
from django.views import View


class MyAjaxView(PinmokPermissionMixin, View):
    permission = 'myapp.can_do_something'
```

`permission` 为可选项，设为 `None` 时仅做登录校验，不检查具体权限。

### 行为说明

权限检查在 `dispatch` 阶段执行，校验不通过时：

- AJAX 请求（`X-Requested-With: XMLHttpRequest`）返回 JSON 格式的 401 响应
- 普通请求重定向到登录页

### 注意事项

`PinmokPermissionMixin` 使用的是 Pinmok 自己的 `permission_checker`，与 Django `admin_view()` 是两套独立的权限机制，请勿混用。