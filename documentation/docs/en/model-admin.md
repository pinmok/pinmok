# Model Administration

If you are already familiar with Django Admin model registration, or just need a quick reference, expand **Quick Start** below — no need to
read the full page.

??? abstract "Quick Start"

    Pinmok replaces Django Admin's model registration. Replace `admin.register` with `padmin.register` and `ModelAdmin` with `PinmokModelAdmin`. Everything else stays the same.

    **Replace imports**

    ```python
    # Before
    from django.contrib import admin
    from django.contrib.admin import ModelAdmin

    # After
    from pinmok import padmin
    from pinmok.padmin import PinmokModelAdmin
    ```

    > If you need to build your own `ModelAdmin` without using `PinmokModelAdmin`, you can mix in `PinmokModelAdminMixin` instead.
    > It handles UI theming and widget replacement only, and adds no extra custom logic.

    **Register a model**

    ```python
    @padmin.register(Article)  # use padmin.register
    class ArticleAdmin(PinmokModelAdmin):
        # All standard ModelAdmin attributes work as usual
        list_display = ('title', 'author', 'created_at')
        search_fields = ('title',)

        # Pinmok extension: menu sort order, lower values appear first
        menu_sort_order = 100

        # Pinmok extension: back button on the edit page
        back_url = reverse_lazy('admin:blog_article_changelist')

        # Pinmok extension: rich-text editor, list the field names to enable
        rich_text_fields = ['content']

        # Pinmok extension: image upload with optional cropping
        # Cropping is enabled by default; path mode writes the file path to the field
        image_crop_fields = [
            'thumbnail',
            {'cover': {
                'mode': 'resource',   # resource mode writes a Resource PK; deduplication included
                'aspectRatio': '16:9',
                'lockRatio': 'true',
            }}
        ]
    ```

    **Inline**

    ```python
    from pinmok.padmin import PinmokStackedInline, PinmokTabularInline

    class ArticleImageInline(PinmokStackedInline):
        model = ArticleImage
        extra = 0
        # image_crop_fields and rich_text_fields work inside Inline as well
        image_crop_fields = [{'image': {'aspectRatio': '4:3'}}]
    ```

    **Custom widgets**

    ```python
    from pinmok.padmin.widgets import PinmokSwitch

    class ArticleAdmin(PinmokModelAdmin):
        # Only specify the field types you want to override;
        # all others keep their Pinmok defaults
        formfield_overrides = {
            models.BooleanField: {'widget': PinmokSwitch},
        }
    ```

## Overview

### padmin and admin

At the heart of Django Admin is `admin.site` — a global `AdminSite` instance that handles model registration, URL routing, and permission
checks. Pinmok follows the same design, providing its own `AdminSite` instance and exposing a registration entry point through
`padmin.register`.

The goal of `padmin` is to keep the developer experience unchanged. Replace admin.register with padmin.register, and ModelAdmin
with PinmokModelAdmin. The API stays consistent while Pinmok handles theme replacement, widget injection, and menu integration in
the background.

**Legacy registration compatibility**

On startup, Pinmok scans `admin.site` for all registered models and migrates them to `padmin` automatically. For each model, a new admin
class is generated with `PinmokModelAdminMixin` mixed in, and the original registration is removed from `admin.site`.

This means models registered with the native `admin.register` still appear in the Pinmok admin and automatically receive Tabler styling and
Pinmok widgets. However, there is a clear limitation: the dynamically generated class only has `PinmokModelAdminMixin` — it cannot access
capabilities exclusive to `PinmokModelAdmin`, such as `back_url`. All future feature additions will also target `PinmokModelAdmin` directly.

For new projects, use `padmin.register` with `PinmokModelAdmin` to get the full feature set.

### The role of PinmokModelAdmin

`PinmokModelAdmin` is not a patch on top of `ModelAdmin` — it is a complete replacement. It takes over form rendering, widget injection, and
the template layer, unifying the entire admin UI under the Tabler theme (fully compatible with Bootstrap 5).

This drop-in replacement requires almost no changes to existing code — all standard ModelAdmin attributes including list_display,
search_fields, fieldsets, and inlines work exactly as before. Pinmok operates at the rendering layer and does not interfere with business
logic.

#### Template layer

Pinmok overrides a large number of Django Admin's built-in templates — including list pages, edit pages, the login page, and popups —
replacing them with the Tabler theme. This happens automatically with no configuration required.

Pinmok also provides two base templates that mirror the role of their Django Admin counterparts:

- `base.html` — a minimal skeleton that loads the required static assets (CSS and JS)
- `base_site.html` — extends `base.html` and provides a full admin layout including the menu, breadcrumbs, and page header

When building custom admin pages, inherit from `base_site.html` to get the complete admin shell. Use `base.html` if you need a blank canvas
or a completely different layout.

#### Overriding templates

To replace a Pinmok template, place a file with the same name under `templates/admin/` in any installed app. Django's template loader
searches apps in `INSTALLED_APPS` order and stops at the first match, so the app containing your template must appear before `pinmok.padmin`
in the list.

```python
INSTALLED_APPS = [
    'your_app',  # must come before pinmok.padmin for templates to take effect
    'pinmok.padmin',
    'django.contrib.admin',
    ...
]
```

The same rule applies when overriding Django's own built-in templates: your app must appear before `django.contrib.admin`.

#### Class hierarchy

All model administration classes in Pinmok are built on `PinmokModelAdminMixin`:

```
PinmokModelAdminMixin (extends BaseModelAdmin)
    ├── PinmokModelAdmin (combines ModelAdmin)      ← main subject of this chapter
    └── PinmokInlineMixin
            ├── PinmokStackedInline (combines StackedInline)
            └── PinmokTabularInline (combines TabularInline)
```

`PinmokModelAdminMixin` carries the shared capabilities: unified widget theming, `image_crop_fields`, `rich_text_fields`, and
`menu_sort_order`. `PinmokModelAdmin` adds edit-page features on top, such as `back_url`. Inline base classes share the same capabilities
through `PinmokInlineMixin`, which does not go through `ModelAdmin` — consistent with how Django's own `InlineModelAdmin` inherits directly
from `BaseModelAdmin`.

## Registering Models

### Replace imports

In your app's `admin.py`, replace the Django Admin imports with their Pinmok equivalents:

```python
# Django Admin
from django.contrib import admin
from django.contrib.admin import ModelAdmin

# Pinmok
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin
```

`padmin` is Pinmok's admin site namespace. Its `register` function is a drop-in replacement for `admin.register` — the usage is identical.

### Registration methods

Both the decorator and the `register()` call are supported, matching Django's own conventions:

```python
# Decorator (recommended)
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)


# register() call
padmin.register(Article, ArticleAdmin)
```

### Legacy registration compatibility

During `AppConfig.ready()`, Pinmok scans `admin.site` and migrates all registered models to `padmin`. Each model gets a freshly generated
admin class with `PinmokModelAdminMixin` mixed in, and its original `admin.site` entry is removed.

!!! warning "Compatibility scope"

    The compatibility mechanism works reliably for standard model registration covering list configuration, search fields, ordering,
    and similar display-only logic. It assumes formfield_for_foreignkey, formfield_for_manytomany, and other field rendering methods
    have not been overridden, and no custom widgets have been defined. In these cases, theming applies cleanly and business logic
    is unaffected.

    If the existing code includes UI customisation, the mixin injection may conflict with Pinmok's widget logic, silently overriding
    custom widgets or causing partial style breakage. In such cases, migrate explicitly by switching to `padmin.register` and
    `PinmokModelAdmin`.

Models registered the native way still load in the Pinmok admin and automatically receive Tabler styling. However, the dynamically generated
class cannot access the full `PinmokModelAdmin` feature set — attributes like `back_url` are unavailable, and all future Pinmok extensions
will target `PinmokModelAdmin` directly.

Unless you have a specific reason to keep the native syntax, replace `admin.register` with `padmin.register` and switch the base class to
`PinmokModelAdmin` to unlock the complete feature set.

## PinmokModelAdmin

`PinmokModelAdmin` inherits from both `PinmokModelAdminMixin` and Django's `ModelAdmin`. It is fully compatible with all standard
`ModelAdmin` usage and adds the following extensions.

### menu_sort_order

`menu_sort_order` controls the position of this model in the admin menu. It accepts an `int` and defaults to `10000`. Lower values appear
higher in the menu.

Django Admin does not provide fine-grained menu ordering — the display order is determined by app order and registration order, which is
difficult to control. `menu_sort_order` solves this by letting you assign an explicit weight to each model.

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
```

Custom menu items defined in `menus.py` and model menu items share the same ordering pool. If your admin mixes both, plan the sort values
together to ensure the menu appears in the intended order. See the [Menu System](menus.md) chapter for details.

### back_url

`back_url` adds a back button to the edit page (change form). Clicking it navigates to the specified URL.

Django Admin's edit page has no back button by default — users must rely on the browser's back action or navigate manually. `back_url`
provides a clear return path for edit flows with an obvious context: for example, returning to a filtered list after editing a record,
rather than the default changelist root.

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    back_url = reverse_lazy('admin:blog_article_changelist')
```

`reverse_lazy` is used instead of `reverse` because class attributes are evaluated at module load time, before URL configuration is fully
initialised.

### image_crop_fields

Django Admin renders `ImageField` as a plain file input with no preview, no cropping, and no deduplication. `image_crop_fields` replaces
this behavior via `PinmokImageFileInput` on the specified fields, providing an image upload interface with live preview. Upload
mode and cropping behaviour are controlled through per-field configuration.

Beyond cropping, `image_crop_fields` is the entry point to Pinmok's upload pipeline, which includes deduplication, compression, and resource
management.

#### Two upload modes

Pinmok provides two upload modes through the `mode` parameter, each targeting a different field type and use case.

- **path mode**

`path` mode (default) writes the uploaded file's path string directly to the field. It works with `ImageField` or `CharField` and does not
interact with the resource table — no deduplication is performed. The returned value is a relative path; use the field's `.url` attribute or
a `{% get_media_prefix %}` tag when rendering. This mode suits simple scenarios where image reuse is not a concern.

```python
# Model fields for path mode
class Article(models.Model):
    cover = models.ImageField(upload_to='covers/')
    # or
    thumbnail = models.CharField(max_length=255)
```

!!! tip "path mode and ImageField"

    In path mode, if the form field is an `ImageField`, Pinmok automatically replaces it with `PinmokImagePathField`
    so that a plain string path passes Django's form validation. This is transparent — no configuration is needed.

- **resource mode**

Pinmok includes a built-in `Resource` table for centralised file management. When images need to be reused across multiple records, model a
`ForeignKey` to `Resource` and use `resource` mode.

In resource mode, the uploaded file is processed by `UploadService`: it is validated, compressed, and deduplicated by SHA-256 hash. If the
same file has been uploaded before, the existing `Resource` record is returned without storing a duplicate. The primary key of the
`Resource` record is written to the field.

Compression is applied automatically: PNG files with transparency are optimised in place; all other formats are converted to JPEG at quality

85.

```python
# Model field for resource mode
from pinmok.padmin.models import Resource


class Article(models.Model):
    cover = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True, blank=True)
```

!!! note

    To avoid magic strings, use the built-in `ImageWidgetMode` enum. It provides `PATH` and `RESOURCE` constants corresponding
    to the two modes:

    ```python
    from pinmok.padmin.enums import ImageWidgetMode
    ```

    Use as `ImageWidgetMode.PATH` and `ImageWidgetMode.RESOURCE`.

#### Cropping behaviour

By default, `image_crop_fields` opens a crop dialog when the user selects an image. The dialog supports free-form cropping, fixed-ratio
cropping, rotation, and flipping. The cropped result is held in memory and uploaded when the form is submitted.

To skip cropping and upload directly, set `crop` to `'false'`. The deduplication and compression logic of `resource` mode is unaffected by
this setting.

SVG files always bypass cropping regardless of the `crop` setting. SVG is a vector format — pixel-based cropping does not apply.

#### Usage

`image_crop_fields` accepts a list. A plain string enables the field with default settings (cropping on, path mode):

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    image_crop_fields = ['cover']
```

To customise a field, pass a single-key dict. Strings and dicts can be mixed in the same list:

```python
image_crop_fields = [
    'thumbnail',  # default settings
    {'cover': {  # custom settings
        'mode': 'resource',
        'aspectRatio': '16:9',
        'lockRatio': 'true',
        'targetWidth': 1200,
    }}
]
```

Using the enum constant:

```python
from pinmok.padmin.enums import ImageWidgetMode

image_crop_fields = [
    {'cover': {'mode': ImageWidgetMode.RESOURCE}}
]
```

#### Parameters

| Parameter      | Default   | Description                                                                                                                                                                |
|----------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `mode`         | `'path'`  | Upload mode. `'path'` writes a path string to `ImageField` or `CharField`; `'resource'` writes a Resource PK to `ForeignKey(Resource)`, with deduplication and compression |
| `crop`         | `'true'`  | Whether to open the crop dialog. `'true'` or `'false'`; SVG files always skip cropping                                                                                     |
| `aspectRatio`  | `''`      | Crop ratio. Accepts `'16:9'`, `'16/9'`, `1.5`, and similar formats. Leave empty for free-form cropping                                                                     |
| `targetWidth`  | `1920`    | Maximum output width in pixels                                                                                                                                             |
| `targetHeight` | *(none)*  | Maximum output height in pixels                                                                                                                                            |
| `lockRatio`    | `'false'` | Lock the crop ratio so the user cannot change it in the dialog. `'true'` or `'false'`                                                                                      |

Cropping is implemented with Cropper.js. The parameters above are those supported by Pinmok's template. For the full list of Cropper.js
options, see the [Cropper.js documentation](https://github.com/fengyuanchen/cropperjs).

### rich_text_fields

`rich_text_fields` replaces the default textarea for the specified fields with the HugeRTE rich-text editor.

Django Admin renders `TextField` as a plain multi-line textarea. Integrating a rich-text editor typically requires installing a third-party
package, wiring up its widgets, and configuring the toolbar — a non-trivial setup. `rich_text_fields` reduces this to a single line of
configuration.

HugeRTE is an open-source fork of TinyMCE and is fully compatible with its configuration API<!-- TODO: add TinyMCE documentation link -->.
Pinmok ships with a built-in default configuration covering common plugins (lists, links, images, tables, code, fullscreen, preview, and
more) and a pre-configured toolbar, so it works out of the box. The editor language follows Django's `LANGUAGE_CODE` automatically — no
additional setup is needed.

Basic usage with the default configuration:

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    rich_text_fields = ['content']
```

To customise, pass a single-key dict with the options you want to override. User-supplied options are merged with the built-in defaults —
only the keys you specify are replaced:

```python
rich_text_fields = [
    'summary',
    {'content': {
        'min_height': 600,
        'menubar': True,
    }},
]
```

All options are serialised to JSON and passed directly to HugeRTE on initialisation. Any option supported by HugeRTE can be used here.

## Form Widgets

`PinmokModelAdmin` automatically applies Pinmok-styled widgets to common field types — no manual `widgets` configuration is needed. All
widgets are built on the Tabler design system and match the overall admin theme.

The following field types are replaced automatically:

| Field type                                        | Widget                                                |
|---------------------------------------------------|-------------------------------------------------------|
| `CharField`                                       | `PinmokTextInput`                                     |
| `TextField` / `JSONField`                         | `PinmokTextarea`                                      |
| `EmailField`                                      | `PinmokEmailInput`                                    |
| `URLField`                                        | `PinmokURLInput`                                      |
| `IntegerField` / `BigIntegerField` / `FloatField` | `PinmokNumberInput`                                   |
| `DecimalField`                                    | `PinmokDecimalInput` (with `0.00` placeholder)        |
| `UUIDField`                                       | `PinmokUUIDInput`                                     |
| `GenericIPAddressField`                           | `PinmokGenericIPAddress` (with input mask)            |
| `BooleanField`                                    | `PinmokCheckbox`                                      |
| `DateField`                                       | `PinmokDateInput`                                     |
| `TimeField`                                       | `PinmokTimeInput`                                     |
| `DateTimeField`                                   | `PinmokDateTimeInput`                                 |
| `ImageField` / `FileField`                        | `PinmokFileInput`                                     |
| Fields with `choices`                             | `PinmokSelect`                                        |
| `ForeignKey` (autocomplete enabled)               | `PinmokAutocompleteSelect`                            |
| `ManyToManyField` (autocomplete enabled)          | `PinmokAutocompleteSelectMultiple`                    |
| `ForeignKey(Resource)`                            | `ResourceWidget` (automatic, no configuration needed) |

`ForeignKey(Resource)` fields are automatically rendered as a resource picker (`ResourceWidget`), which supports selecting existing files
from the resource library or opening the upload dialog — no extra configuration required.

Recursive `ForeignKey` fields that point to the same model (common in tree-structured models) automatically have their add, change, delete,
and view buttons disabled, preventing recursive operations from being triggered on the edit page.

### Custom widgets

To use a different widget for a specific field type, set `formfield_overrides`. Pinmok merges your overrides with its own defaults — only
the field types you explicitly specify are replaced; all others keep their Pinmok defaults and do not fall back to Django's originals.

```python
from django.db import models
from pinmok.padmin.widgets import PinmokSwitch


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    formfield_overrides = {
        models.BooleanField: {'widget': PinmokSwitch},
    }
```

Pinmok also provides several widgets that are not part of the automatic replacement set but can be used manually:

| Widget                         | Use case                                                                     |
|--------------------------------|------------------------------------------------------------------------------|
| `PinmokSwitch`                 | Toggle-style boolean field, visually distinct from the default checkbox      |
| `PinmokSelectTags`             | Multi-select tag input based on Tom Select, suitable for tags and categories |
| `PinmokCheckboxSelectMultiple` | Checkbox group, suitable for multiple-choice fields with few options         |
| `PinmokRadioSelect`            | Radio button group, used via `radio_fields`                                  |
| `PinmokDatalistInput`          | Text input with suggestion dropdown; the caller provides the option list     |

Import path:

```python
from pinmok.padmin.widgets import (
    PinmokSwitch,
    PinmokSelectTags,
    PinmokCheckboxSelectMultiple,
    PinmokRadioSelect,
    PinmokDatalistInput,
)
```

## Inline Support

Pinmok provides inline base classes to match Django's native ones:

```python
from pinmok.padmin import PinmokStackedInline, PinmokTabularInline


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
```

Usage is identical to Django's `StackedInline` and `TabularInline`. Both share the full capability set of `PinmokModelAdminMixin` through
`PinmokInlineMixin` — `image_crop_fields` and `rich_text_fields` work inside inlines exactly as they do in `PinmokModelAdmin`.

!!! tip

    `PinmokInlineMixin` extends `PinmokModelAdminMixin` directly and does not go through `ModelAdmin`, consistent with how Django's
    own `InlineModelAdmin` inherits from `BaseModelAdmin`. Do not use `PinmokModelAdmin` as the base class for an inline.

## Complete Example

```python
from django.db import models
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin, PinmokStackedInline
from pinmok.padmin.enums import ImageWidgetMode
from pinmok.padmin.models import Resource
from pinmok.padmin.widgets import PinmokSwitch

from .models import Article, ArticleImage


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
    image_crop_fields = [
        {'image': {'aspectRatio': '4:3'}}
    ]


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
    back_url = reverse_lazy('admin:blog_article_changelist')

    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)

    rich_text_fields = ['content']

    image_crop_fields = [
        'thumbnail',
        {'cover': {
            'mode': ImageWidgetMode.RESOURCE,
            'aspectRatio': '16:9',
            'targetWidth': 1200,
            'lockRatio': 'true',
        }}
    ]

    formfield_overrides = {
        models.BooleanField: {'widget': PinmokSwitch},
    }

    inlines = [ArticleImageInline]
```