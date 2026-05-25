# Theme

Pinmok comes with a dedicated theme system for frontend presentation. Each application can install multiple themes and manage or switch
between them directly from the admin.

## Overview

Pinmok's theme system is organized by application. Each application can install multiple themes, but only one can be active at a time. Any
themes whose `app_label` points to the same application belong to that application and share the same activation logic.

Each theme consists of multiple templates written in accordance with Django's official template specification. Individual templates can be
paired with an optional configuration file, and configuration files support multiple languages. Pinmok also provides a set of built-in
template tags that expose common site configuration data as global template variables, accessible from any theme
template.

## Theme Structure

Pinmok theme directories must be placed inside a template directory recognized by Django, following a fixed path convention:

```text
templates/
└── themes/
    ├── default/
    │   ├── theme.json
    │   ├── index.html
    │   └── index.json
    └── nature/
        ├── theme.json
        └── ...
```

`themes/` is the fixed directory name. Each subdirectory within it is an independent theme. Every theme must include `theme.json` as its
description file; other template files can be customized freely per application.

`theme.json` contains two categories of information: basic theme metadata (name, version, author, owning application, etc.) and global
variable definitions. Global variables take effect across the entire theme, can be configured in the admin, and are available in all
templates. Template-level variables are defined in their own configuration files and apply only to the corresponding template.

## Templates and Configuration Files

Pinmok templates are fully compatible with Django's native template syntax. To support template extension and customization, each template
can be paired with a dedicated configuration file for registering the template filename, binding it to a specific action, and defining the
variables it requires.

Configuration files fall into two categories: the theme configuration file `theme.json` and template configuration files. Both support
defining variables and fieldsets. The key difference is scope: variables defined in `theme.json` are globally available across the entire
application; variables defined in a template configuration file apply only to that template.

Configuration files support multiple languages. The naming format is: **filename.language-code.json**, for example:

- `theme.json` — the default configuration file, used as a fallback when no language-specific file is matched. **This file is required.**
- `theme.zh-hans.json` — Simplified Chinese configuration, activated when the admin language is set to Simplified Chinese.
- `theme.en.json` — English configuration, activated when the admin language is set to English.

### theme.json

The theme configuration file defines the theme's properties. Every theme must include this file. Supported fields:

- `name`: Theme name, uniquely identifies the theme. **Required**
- `app_label`: Specifies the application this theme belongs to. Must be a valid app label. **Required**
- `version`: Theme version number.
- `author`: Author information.
- `description`: A detailed description of the theme.
- `preview_url`: A URL linking to a theme preview.
- `vars`: Global variable definitions. See the Variables section below.
- `fieldsets`: Fieldset variable definitions. See the Variables section below.

### Template Configuration Files

A template configuration file must share the same name as its corresponding template. For example, if the template is `list.html`, its
configuration file must be named `list.json`. Supported fields:

- `name`: Template name, used to identify the template in the admin (e.g. Home, Article List). **Required**
- `action`: Page action identifier. Indicates which type of page this configuration file corresponds to — such as a list page, detail page,
  or home page. Its value must be consistent with the `name` attribute defined in Django URL routing. Pinmok uses this to bind the
  configuration file to a specific page. **Required**
- `order`: Sort weight. An integer; lower values appear first. Defaults to `10000`.
- `vars`: Template variable definitions. See the Variables section below.
- `fieldsets`: Template fieldset variable definitions. See the Variables section below.

### Variables and Fieldsets

Variables defined in a configuration file are injected into the template context and can be used directly in templates.

**Variables (vars)**

```json
{
  "vars": {
    "company_name": {
      "title": "Company Name",
      "type": "text",
      "default": "Pinmok",
      "tip": "Displayed in the site header"
    }
  }
}
```

Each key under `vars` is a variable name, accessible in templates via `{{ company_name }}`. Field descriptions:

- `title`: The label displayed for this variable in the admin configuration page. **Required**
- `type`: The variable type. **Required**. See the table below for available values.
- `default`: Default value. For `text` and `textarea`, defaults to an empty string; for `number`, defaults to `0`; for `boolean`, defaults
  to `False`.
- `tip`: Help text displayed below the variable in the admin configuration page.

| Type         | Admin Widget      | Notes                      |
|--------------|-------------------|----------------------------|
| `text`       | Single-line input |                            |
| `textarea`   | Multi-line input  |                            |
| `number`     | Number input      |                            |
| `boolean`    | Toggle switch     |                            |
| `datasource` | Datasource picker | See the Datasource section |

**Fieldsets**

Variables can also be grouped under `fieldsets`. Each fieldset requires a `title`, displayed as the group heading in the admin configuration
page. The `vars` definition within a fieldset follows the same format as top-level variables. Fieldset variables are accessed in templates
using dot notation, e.g. `{{ sidebar.count }}`.

```json
{
  "fieldsets": {
    "sidebar": {
      "title": "Sidebar",
      "vars": {
        "count": {
          "title": "Number of Items",
          "type": "number",
          "default": 5
        }
      }
    }
  }
}
```

### Datasource

A datasource is the data provider for `datasource`-type variables. The admin configuration page renders the widget returned by the
datasource directly, allowing users to make a selection.

**Built-in Datasources**

Pinmok includes the following built-in datasources:

| Key      | Description      |
|----------|------------------|
| `nav`    | Navigation group |
| `slider` | Slider group     |

To use a datasource, set the variable `type` to `datasource` and specify the datasource key via `source`:

```json
{
  "vars": {
    "main_nav": {
      "title": "Main Navigation",
      "type": "datasource",
      "source": "nav",
      "multiple": false
    }
  }
}
```

- `source`: The datasource key. **Required**
- `multiple`: Whether multiple selection is allowed. Defaults to `false`.

**Custom Datasources**

A custom datasource needs to inherit from Django's Widget base class or its subclasses, and be registered with Pinmok's datasource registry.
The return value must be a `Widget` instance, as the admin renders it directly in the configuration interface.

**Parameter Passing Rules**

All fields in the configuration file other than `title`, `type`, `default`, and `tip` are passed as keyword arguments to the widget's
`__init__`. Custom widgets must declare the corresponding parameters in `__init__` to receive them. For example: if the configuration file
contains `"multiple": false`, the widget's `__init__` should declare `multiple=False`, and Pinmok will pass it automatically.

If the widget's `__init__` declares `**kwargs`, all extra parameters are passed through as-is. If it does not, Pinmok passes only the
parameters explicitly declared in `__init__` and silently ignores the rest.

```python
from django.forms.widgets import Select
from pinmok.padmin.datasource import datasource


@datasource.register('my_source')
class MyDataSource(Select):
    def __init__(self, attrs=None, multiple=False, category=None):
        # multiple and category come from the configuration file
        from .models import MyModel
        queryset = MyModel.objects.filter(category=category) if category else MyModel.objects.all()
        choices = [('', 'None')] + [(obj.pk, obj.name) for obj in queryset]
        super().__init__(attrs=attrs, choices=choices)
```

Once registered, the datasource can be used in any configuration file via `"source": "my_source"`. Custom fields in the configuration file
are automatically passed as arguments to the widget:

```json
{
  "vars": {
    "my_var": {
      "title": "My Variable",
      "type": "datasource",
      "source": "my_source",
      "multiple": false,
      "category": "news"
    }
  }
}
```

## Complete Example

The following example demonstrates a complete theme setup, covering the theme description file, a template configuration file, and a
template file.

**Directory Structure**

```text
templates/
└── themes/
    └── sample/
        ├── theme.json
        ├── list.html
        └── list.json
```

**theme.json**

```json
{
  "name": "Sample Theme",
  "app_label": "content",
  "version": "1.0.0",
  "author": "Crazy",
  "description": "A theme for demonstration.",
  "preview_url": "https://www.qdcrazy.cn",
  "vars": {
    "company_name": {
      "title": "Company Name",
      "type": "text",
      "default": "",
      "tip": "Displayed in the site header and browser title"
    }
  },
  "fieldsets": {
    "sidebar": {
      "title": "Sidebar",
      "vars": {
        "category": {
          "title": "Category",
          "type": "datasource",
          "source": "category"
        },
        "title": {
          "title": "Sidebar Title",
          "type": "text",
          "default": "Latest"
        },
        "count": {
          "title": "Number of Items",
          "type": "number",
          "default": 5
        },
        "show_thumbnail": {
          "title": "Show Thumbnail",
          "type": "boolean",
          "default": true
        }
      }
    }
  }
}
```

**list.json**

```json
{
  "name": "Article List",
  "action": "content_article_list",
  "vars": {
    "page_title": {
      "title": "Page Title",
      "type": "text",
      "default": "Articles",
      "tip": "Displayed at the top of the list page"
    },
    "page_size": {
      "title": "Page Size",
      "type": "number",
      "default": 10
    },
    "show_author": {
      "title": "Show Author",
      "type": "boolean",
      "default": true
    }
  }
}
```

**list.html**

```html
<h1>{{ page_title }}</h1>

<p>Page size: {{ page_size }}</p>

{% if show_author %}
<p>Author information is displayed.</p>
{% endif %}

<aside>
    <h2>{{ sidebar.title }}</h2>
    {% if sidebar.show_thumbnail %}
    {# render thumbnails #}
    {% endif %}
</aside>

<footer>{{ company_name }}</footer>
```