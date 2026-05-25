# Appendix

Pinmok provides a set of lightweight extensions and handy auxiliary features, all documented in this appendix.

## Admin Context Extension

Pinmok extends Django Admin's built-in management site by overriding the `each_context` method and introducing a dedicated signal mechanism.
Developers can inject custom data into the admin context simply by listening to the corresponding signal — no framework code needs to be
modified. Injected data will be available across all admin pages.

### extend_admin_context

This signal fires on every request that calls `each_context`. Signal receivers modify the context dictionary directly to append custom data,
with no return value required.

#### Example

```python
from django.dispatch import receiver
from pinmok.core.signals import extend_admin_context


@receiver(extend_admin_context)
def inject_my_context(sender, request, context, **kwargs):
    context.update({
        'my_key': 'my_value',
    })
```

#### Signal Parameters

- `sender` — The sending class
- `request` — The current `HttpRequest` object
- `context` — The shared admin context dict; call `update()` on it to inject data

## Email Service

Pinmok includes a built-in email service that wraps Django's native mail-sending logic. SMTP parameters are configured via the admin panel,
eliminating manual configuration in `settings.py`.

### Configuration Priority

`EmailService` automatically determines which configuration to use at initialisation time, according to the following rules:

| Database config | settings config | Effective config                    |
|-----------------|-----------------|-------------------------------------|
| Present         | Present         | Database config takes priority      |
| Present         | Absent          | Database config                     |
| Absent          | Present         | settings config                     |
| Absent          | Absent          | Django defaults (delivery may fail) |

### Sending Emails

Pinmok provides an email service class that supports both plain and template-based emails. Import path: `pinmok.padmin.service.email`.

#### Plain Email

For straightforward email delivery, pass the standard parameters. Example:

```python
from pinmok.padmin.service.email import EmailService

service = EmailService()

# Minimal — subject is optional
service.send(to='user@example.com', content='<p>Hello</p>')

# Standard
service.send(
    to='user@example.com',
    subject='Hello',
    content='<p>This is a test email.</p>',
)
```

> The `to` parameter accepts either a single address string or a list of strings. The sender address is always read from the admin site
> configuration and does not need to be passed manually.

#### Template Email

Template emails allow you to pre-configure a fixed email body in the admin interface, with dynamic content represented by placeholder
variables. At send time, you supply the variable values and they are substituted automatically. This is well-suited to fixed-format emails
such as verification codes and notifications.

##### 1. Configure the Template in the Admin

In the admin interface, go to **Email Settings**. On the settings page on the right, expand the **Email Templates** section at the bottom —
it is collapsed by default.

- **Sender Name** — Optional. When provided, the sender will appear as `Name <address>`, e.g. `Pinmok<noreply@example.com>`.
- **Subject** — The email subject. Supports variable placeholders, e.g. `Hello ${username}, you have a new message`.
- **Content** — The email body. Supports HTML and variable placeholders, e.g.
  `<p>Your verification code is <strong>${verify_code}</strong>. It expires in 10 minutes.</p>`.
- **Available Variables** — Declares the variable names used in the template, separated by commas, e.g. `username, verify_code`. The names
  declared here must exactly match the keys in `template_params` at call time, otherwise an `EmailValueError` will be raised.

> The placeholder format is `${var_name}`. Unresolved placeholders will be preserved in the final email content. If no template variables
> are configured in the admin, `template_params` may be omitted and the template content will be sent as-is.

##### 2. Usage Example

```python
service.send_with_template(
    to='user@example.com',
    template_params={
        'username': 'Crazy',
        'verify_code': '123456',
    }
)
```

If the template defines variables that are not supplied at call time, an `EmailValueError` is raised. It is recommended to catch it in your
business logic:

```python
from pinmok.padmin.service.email import EmailService, EmailValueError

try:
    service.send_with_template(to='user@example.com', template_params={'username': 'Crazy'})
except EmailValueError as e:
    # Handle missing variable error
    print(e)
except Exception as e:
    # Handle other send errors
    print(e)
```

## Admin URL Registration

Django admin views are not ordinary views — All admin routes require login authentication, permission validation and CSRF protection,
all of which are handled by `AdminSite.admin_view()`. Registering admin views directly in the project's URL configuration and bypassing this
wrapper can cause unexpected behavior at best and introduce security vulnerabilities at worst.

To address this, Pinmok overrides `AdminSite.get_urls()` and establishes a convention: declare an `admin_urlpatterns` variable in your app's
`urls.py`, and Pinmok will automatically scan for it at startup, wrap each URL with `admin_view()`, and register everything into the admin
URL configuration. Developers can focus purely on view logic; the framework takes care of permission handling.

You do not need to use `admin_urlpatterns` if:

- The URL belongs to the frontend and has nothing to do with the admin — register it in the project's URL configuration as usual.
- You have a thorough understanding of Django's admin permission mechanism and have your own implementation — no need for Pinmok to
  intervene.

### Defining URLs

In your app's `urls.py`, declare a module-level variable named `admin_urlpatterns` containing a standard list of URL patterns:

```python
# myapp/urls.py
from django.urls import path
from . import views

admin_urlpatterns = [
    path("dashboard/", views.dashboard, name="myapp-dashboard"),
    path("export/", views.export, name="myapp-export"),
]
```

Pinmok scans all installed apps' `urls.py` files at startup, reads `admin_urlpatterns`, and registers the patterns into the admin URL
configuration.

### Automatic Permission Wrapping

For every `URLPattern` in the list, Pinmok automatically wraps the view callback with `admin_view()`, enforcing login verification and
permission checks on every request. No manual handling is required.

The URLs are registered under the app's namespace:

```
/admin/myapp/dashboard/
/admin/myapp/export/
```

### Using `include()`

If an entry is a `URLResolver` (i.e. a URL group introduced via `include()`), Pinmok registers it directly **without** wrapping it with
`admin_view()`.

This design serves as a reserved flexible entry: when a developer has custom permission-handling logic, they can introduce their own URL
group via `include()` and manage permissions themselves.

```python
# myapp/urls.py
from django.urls import path, include
from . import api_urls

admin_urlpatterns = [
    # Plain view — Pinmok wraps it with admin_view() automatically
    path("dashboard/", views.dashboard, name="myapp-dashboard"),

    # Custom permission handling — Pinmok does not intervene
    path("api/", include(api_urls)),
]
```

> When using `include()`, ensure that the included URL group contains its own permission checks. Without them, the views will be accessible
> to all users.

## PinmokPermissionMixin

`PinmokPermissionMixin` is a class-based view mixin that provides permission control for views that cannot be managed by the built-in
`admin_view` mechanism. The typical use case is AJAX endpoints.

### Usage

Inherit from `PinmokPermissionMixin` and declare a `permission` attribute on the class:

```python
from pinmok.core.mixins import PinmokPermissionMixin
from django.views import View


class MyAjaxView(PinmokPermissionMixin, View):
    permission = 'myapp.can_do_something'
```

`permission` is optional. When set to `None`, only login verification is performed — no specific permission is checked.

### Behaviour

The permission check runs at the `dispatch` stage. If the check fails:

- AJAX requests (`X-Requested-With: XMLHttpRequest`) receive a JSON 401 response.
- Regular requests are redirected to the login page.

### Note

`PinmokPermissionMixin` uses Pinmok's own `permission_checker`, which is entirely separate from Django's `admin_view()` mechanism. The two
should not be mixed.