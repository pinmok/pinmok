# Appendix

Some of Pinmok's built-in features are self-contained and not yet substantial enough to warrant their own chapters, yet they remain
essential in day-to-day development. This appendix collects them in one place. As the project evolves, some of these features will grow into
dedicated chapters, and the appendix will be updated accordingly.

## Admin Context Extension

Admin pages often need to share global context data such as the current user's menu, site configuration, or application state. If each view
handles this separately, the same logic becomes scattered across the project and is difficult to maintain. To address this, Pinmok overrides
Django Admin’s `each_context()` method and introduces a dedicated signal mechanism.

### The `extend_admin_context` Signal

This signal is sent by `PinmokAdminSite` each time `each_context()` is called. The `sender` is the `PinmokAdminSite` class itself. Receivers
inject data by modifying the `context` dictionary directly — no return value is needed.

**Signal parameters:**

| Parameter | Type          | Description                                                         |
|-----------|---------------|---------------------------------------------------------------------|
| `sender`  | `type`        | The signal sender, i.e. the `PinmokAdminSite` class                 |
| `request` | `HttpRequest` | The current request object                                          |
| `context` | `dict`        | The shared admin context dictionary; call `update()` to inject data |

**Example:**

```python
from django.dispatch import receiver
from pinmok.core.signals import extend_admin_context


@receiver(extend_admin_context)
def inject_my_context(sender, request, context, **kwargs):
    context.update({
        'my_key': 'my_value',
    })
```

The receiver signature must include `**kwargs`. This is a Django signal requirement that ensures compatibility if additional parameters are
introduced in the future.

---

## Email Service

Pinmok provides a built-in `EmailService` class that wraps Django's email sending logic. Its primary purpose is to move SMTP configuration
out of `settings.py` and into the admin site settings, so that end users can manage mail configuration through the backend without touching
the codebase. Developers call `EmailService` directly; the actual connection parameters are configured by the user in the admin.

Import path:

```python
from pinmok.padmin.service.email import EmailService
```

The current version of `EmailService` covers the core sending interface, supporting both plain email delivery and template variable
substitution, which is sufficient for most common use cases.

### Configuration Priority

`EmailService` automatically selects which SMTP configuration to use during initialization:

| Database config | settings config | In effect                          |
|-----------------|-----------------|------------------------------------|
| Present         | Present         | Database config takes priority     |
| Present         | Absent          | Database config                    |
| Absent          | Present         | settings config                    |
| Absent          | Absent          | Django defaults (sending may fail) |

### Sending a Plain Email

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

Sends an HTML email to one or more recipients. The sender address is read from the admin site configuration and does not need to be passed
in. The email body supports HTML; Django sets `content_subtype` to `html` so the recipient's mail client renders it accordingly.

**Parameters:**

| Parameter | Type               | Description                                                        |
|-----------|--------------------|--------------------------------------------------------------------|
| `to`      | `str \| list[str]` | Recipient address or list of addresses                             |
| `subject` | `str`              | Email subject line; required — pass `''` to send without a subject |
| `content` | `str`              | Email body; HTML is supported                                      |

**Return value:** `int` — the number of messages successfully sent.

---

### Sending a Template Email

#### `send_with_template(to, subject, content, template_params=None)`

```python
service.send_with_template(
    to='user@example.com',
    subject='Hello ${username}, you have a new message',
    content='<p>Your verification code is <strong>${verify_code}</strong>. It expires in 10 minutes.</p>',
    template_params={
        'username': 'Tomas',
        'verify_code': '123456',
    }
)
```

Extends plain email sending with variable substitution. Before sending, all `${var_name}` placeholders in `subject` and `content` are
replaced with the corresponding values from `template_params`. Placeholders with no matching key are left as-is. The template content is
supplied by the caller — `EmailService` only handles substitution and delivery.

If `template_params` is omitted or empty, `subject` and `content` are sent as-is, making the behavior identical to `send()`.

**Parameters:**

| Parameter         | Type                     | Description                                                                                             |
|-------------------|--------------------------|---------------------------------------------------------------------------------------------------------|
| `to`              | `str \| list[str]`       | Recipient address or list of addresses                                                                  |
| `subject`         | `str`                    | Email subject line; supports placeholders; required                                                     |
| `content`         | `str`                    | Email body; supports HTML and placeholders                                                              |
| `template_params` | `dict[str, str] \| None` | Variable substitution map; keys are variable names, values are substitution strings; defaults to `None` |

**Return value:** `int` — the number of messages successfully sent.

**Exceptions:** Sending errors propagate as standard exceptions. It is good practice to wrap calls in a try/except block:

```python
from pinmok.padmin.service.email import EmailService, EmailValueError

service = EmailService()
try:
    service.send_with_template(
        to='user@example.com',
        subject='Hello ${username}',
        content='<p>Code: ${verify_code}</p>',
        template_params={'username': 'Tomas', 'verify_code': '123456'},
    )
except EmailValueError as e:
    # Handle validation errors
    print(e)
except Exception as e:
    # Handle other sending errors
    print(e)
```

---

## Admin URL Registration

Django admin views are not ordinary views — every admin URL must pass through login verification, permission checks, and CSRF protection,
all of which are handled by `AdminSite.admin_view()`. Registering an admin view directly in the project's URL configuration, bypassing this
wrapper, can cause functional errors at best and security vulnerabilities at worst.

Pinmok overrides `AdminSite.get_urls()` and establishes a convention: declare an `admin_urlpatterns` variable in your app's `urls.py`, and
Pinmok will scan it at startup, wrap each URL with `admin_view()`, and register it into the admin URL configuration. Developers focus on the
view logic itself; the framework handles the rest.

You do not need `admin_urlpatterns` in these cases:

- The URL belongs to the frontend and has nothing to do with the admin — register it in the project's URL configuration as usual.
- You have your own admin permission handling and do not need Pinmok to manage it.

### Declaring Admin URLs

Declare a module-level variable named `admin_urlpatterns` in your app's `urls.py`, with a standard list of URL patterns as its value:

```python
# myapp/urls.py
from django.urls import path
from . import views

admin_urlpatterns = [
    path('dashboard/', views.dashboard, name='myapp-dashboard'),
    path('export/', views.export, name='myapp-export'),
]
```

Pinmok scans all installed apps for this variable at startup and registers the patterns into the admin URL configuration. The URLs are
mounted under the app's namespace:

```
/admin/myapp/dashboard/
/admin/myapp/export/
```

### Automatic Permission Wrapping

For every `URLPattern` entry in the list, Pinmok automatically wraps the view function with `admin_view()`, enforcing login verification and
permission checks on every request. No manual handling is required.

### Using `include()`

If an entry is a `URLResolver` — that is, a URL group introduced via `include()` — Pinmok registers it as-is without applying
`admin_view()`. This is an intentional escape hatch: when you have custom permission handling, use `include()` to bring in your own URL
group and manage permissions yourself.

```python
# myapp/urls.py
from django.urls import path, include
from . import views, api_urls

admin_urlpatterns = [
    # Plain view: Pinmok wraps this with admin_view() automatically
    path('dashboard/', views.dashboard, name='myapp-dashboard'),

    # Custom permission handling: Pinmok does not intervene
    path('api/', include(api_urls)),
]
```

!!! warning "Warning"

    When using `include()`, make sure the included URL group contains proper permission checks. Without them, the views will be accessible to
    all users.

---

## PinmokPermissionMixin

`PinmokPermissionMixin` is a class-based view mixin for enforcing permission checks on views that cannot be covered by `admin_view()`. The
most common use case is AJAX endpoints.

### Usage

Inherit from `PinmokPermissionMixin` and declare a `permission` attribute on the class:

```python
from pinmok.core.mixins import PinmokPermissionMixin
from django.views import View


class MyAjaxView(PinmokPermissionMixin, View):
    permission = 'myapp.can_do_something'
```

`permission` is optional. Setting it to `None` performs a login check only, without checking any specific permission.

### Behavior

Permission checks run at the `dispatch` stage. If the check fails:

- AJAX requests (identified by the `X-Requested-With: XMLHttpRequest` header) receive a JSON 401 response.
- Regular requests are redirected to the login page.

### Note

`PinmokPermissionMixin` uses Pinmok's own `permission_checker`, which is independent of Django's `admin_view()` mechanism. Do not mix the
two. `permission_checker` supports custom replacement; see the Permissions chapter for details.