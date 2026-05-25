# Model Registration

## Overview

Pinmok is fully compatible with Django Admin's native model registration system and follows the exact same usage pattern. Simply update your
import statements and keep your existing `ModelAdmin` subclasses and registration logic — no changes to your business code required. You'll
immediately gain unified form widgets, menu ordering, and other admin enhancements.

## Registering Models

### Update Imports

In your app's `admin.py`, replace the Django Admin imports with Pinmok equivalents:

```python
# Original imports
from django.contrib import admin
from django.contrib.admin import ModelAdmin

# Replace with Pinmok imports
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin
```

Registration works exactly like Django Admin — use either the decorator or the `register()` method:

```python
# Decorator style
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)


# Or register() style
padmin.register(Article, ArticleAdmin)
```

### Difference from Native Registration

Pinmok's `padmin` acts as a standalone Admin Site instance, fully isolated from Django built-in `admin.site` — each maintains its own
registry.
Models must be registered with `padmin` to appear in the Pinmok admin. Registering a model with both will cause conflicts; avoid mixing the
two.

## PinmokModelAdmin

`PinmokModelAdmin` is Pinmok's `ModelAdmin` base class. It extends Django's native `ModelAdmin`, is fully compatible with its API, and
automatically applies Tabler-styled form widgets. It also adds the following attributes:

### Extended Attributes

**`menu_sort_order`**

Controls the model's sort position in the admin menu. Accepts an `int`; defaults to `10000`. Lower values appear first. When custom menus
defined in `menus.py` and model menus coexist, they are sorted uniformly. Configure this property properly to get your desired menu
hierarchy.

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
```

**`back_url`**

Displays a **back button** on the **edit page** that navigates to the specified URL. Useful for edit views with a clear contextual
relationship to a parent list.

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    back_url = reverse_lazy('admin:blog_article_changelist')
```

**`image_crop_fields`**

`PinmokModelAdmin` includes built-in client-side image cropping. Users can visually crop an image before uploading. The feature is powered
by Cropper.js, so all configuration options follow Cropper.js conventions.

This attribute supports two forms, which may be mixed:

- Simple form — just specify the field name:

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    image_crop_fields = ['cover']
```

- Full form — specify the field name with options:

```python
image_crop_fields = [
    'thumbnail',
    {'cover': {'aspectRatio': '4:3'}}
]
```

Pinmok supports two ways to save uploaded images — to the resource library (storing the primary key of a resource record) or as a plain path
string — so this attribute also accepts a `mode` parameter:

- `path` *(default)*: stores the image path as a string in the database.
- `resource`: stores the PK of a `Resource` object; suited for centralized asset management.

A complete example:

```python
image_crop_fields = [
    'thumbnail',  # Simple form, uses default settings
    {
        'cover': {
            'mode': 'resource',  # Save mode: 'path' (default) or 'resource'
            'aspectRatio': '16:9',  # Crop ratio
            'targetWidth': '1200',  # Maximum output width
            'targetHeight': '675',  # Maximum output height
            'lockRatio': 'true',  # Lock ratio — user cannot change it
        }
    }
]
```

**`rich_text_fields`**

Pinmok integrates the HugeRTE rich text editor (an open-source fork of TinyMCE; configuration options are fully compatible). Add a field
name to this list and its input will automatically be replaced with the rich text editor. Pinmok ships with sensible defaults so it works
out of the box. Any options you provide will override the corresponding defaults:

```python
# Simple form, uses default configuration
rich_text_fields = ['content']

# With options — overrides specific defaults
rich_text_fields = [
    'summary',
    {'content': {'height': 600, 'toolbar': 'bold italic | link image'}},
]
```

### Form Widgets

`PinmokModelAdmin` automatically applies Pinmok-styled widgets to common field types — text inputs, datetime pickers, select dropdowns, file
uploads, and more — with no manual `widgets` configuration required.

## Inline Support

Pinmok provides inline base classes that mirror Django's native ones:

```python
from pinmok.padmin.options import PinmokStackedInline, PinmokTabularInline


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
```

Usage is identical to Django's native `StackedInline` and `TabularInline`.

## Complete Example

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin, PinmokStackedInline
from .models import Article, ArticleImage


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
    back_url = reverse_lazy('admin:blog_article_changelist')
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)
    rich_text_fields = ['content']
    inlines = [ArticleImageInline]
```