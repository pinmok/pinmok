# Template Tags

If you are already familiar with Pinmok template tags, expand the **Quick Start** above for a concise reference.

??? abstract "Quick Start"

    **Loading Tag Libraries**

    Pinmok provides two tag libraries: one exclusively for the admin interface, and one for general
    use in both admin and frontend templates.

    ```django
    {% load pinmok_admin_tags %}  {# Admin templates only #}
    {% load pinmok_tags %}        {# Admin and frontend templates #}
    ```

    **Admin-Only Tags** `{% load pinmok_admin_tags %}`

    - `add_class`: Filter. Appends CSS class names to a rendered HTML element.

        ```django
        {{ field.label_tag|add_class:"form-label required" }}
        ```

    - `alert`: Renders an alert component. `title` is a positional argument; all others are keyword arguments.

        | Parameter | Type | Default | Description |
        |---|---|---|---|
        | `title` | str | required | Alert heading; positional argument |
        | `level` | str | `'danger'` | Alert type: `danger` / `warning` / `success` / `info` |
        | `description` | str | `None` | Optional body text |
        | `variant` | str | `''` | Visual intensity: `''` / `important` saturated solid color / `minor` very light |
        | `dismiss` | bool | `False` | Whether to show a close button |
        | `extra_class` | str | `''` | Additional CSS classes on the alert element |
        | `link_text` | str | `None` | Link label; must be used together with `link_url` |
        | `link_url` | str | `None` | Link URL; must be used together with `link_text` |

        ```django
        {% alert "An error occurred!" %}
        {% alert "Success" level="success" %}
        {% alert "Heads up" level="warning" description="This action cannot be undone." variant="important" %}
        {% alert "Welcome, member" level="info" description="You now have access to all member features." dismiss=True link_text="Log in" link_url="/login" %}
        ```

    **General Tags** `{% load pinmok_tags %}`

    - `truncate_filename`: Filter. Truncates long filenames while preserving the extension. The specified length includes the extension; default is 20.

        ```django
        {{ filename|truncate_filename }}
        {{ filename|truncate_filename:10 }}
        ```

    - `icon`: Renders an inline SVG icon. All parameters are positional.

        | Parameter | Type | Default | Description |
        |---|---|---|---|
        | `icon_name` | str | required | Symbol ID in the sprite file |
        | `css_class` | str | `''` | CSS classes added to the `<svg>` element |
        | `size` | int | `24` | Icon width and height in pixels |

        ```django
        {% icon "tabler-home" %}
        {% icon "tabler-user" "icon nav-icon" %}
        {% icon "my-custom-icon" "icon" 20 %}
        ```

    - `media_url`: Resolves a media file path to a full URL, following the configured storage backend.

        ```django
        {% media_url object.image as url %}
        <img src="{{ url }}">

        or
        <img src="{% media_url object.image %}">
        ```

    - `site_info`: Returns a dictionary of site configuration, including name, ICP filing, contact info, and social accounts.
        Typically assigned to a variable before use.

        ```django
        {% site_info as site %}
        {{ site.site_name }}
        ```

    - `links`: Returns the list of enabled Partner Links, ordered by `sort_order`. Each item has `title`, `url`,
        and `image` fields. Typically assigned to a variable before use.

        ```django
        {% links as link_list %}
        {% for link in link_list %}
            <a href="{{ link.url }}">{{ link.title }}</a>
        {% endfor %}
        ```

    - `navigation` / `navblock`: Block tags for rendering a navigation tree by group. The two tags must be used together.

        ```django
        {% navigation nav.group %}
            {% navblock 1 %}
                <li><a href="{{ item.url }}">{{ item.name }}</a>{{ children }}</li>
            {% endnavblock %}
            {% navblock default %}
                <a href="{{ item.url }}">{{ item.name }}</a>{{ children }}
            {% endnavblock %}
        {% endnavigation %}
        ```

    - `slider`: Returns the list of active slider items for a given group, ordered by `sort_order`.
        Each item has `title`, `subtitle`, `image`, and `link` fields.

        ```django
        {% slider nav.slide_group as slides %}
        {% for slide in slides %}
            {% media_url slide.image as slide_url %}
            <img src="{{ slide_url }}" alt="{{ slide.title }}">
        {% endfor %}
        ```

Template development often involves data and components that need to appear across multiple templates. Pinmok provides a set of built-in
template tags that expose commonly used data directly to the template layer, eliminating the need to pass context variables manually from
every view. If the built-in tags do not cover your needs, you can write additional tag libraries following Django's standard conventions.

Pinmok ships two tag libraries. `pinmok_admin_tags` is intended exclusively for admin templates and contains UI components specific to the
admin interface. `pinmok_tags` can be used in both admin and frontend templates, and provides general-purpose tags for site configuration,
navigation, media files, and more.

| Library             | Load Statement                 | Scope                        |
|---------------------|--------------------------------|------------------------------|
| `pinmok_admin_tags` | `{% load pinmok_admin_tags %}` | Admin templates only         |
| `pinmok_tags`       | `{% load pinmok_tags %}`       | Admin and frontend templates |

Load the libraries you need at the top of your template. In admin templates, both can be loaded together:

```django
{% load pinmok_admin_tags pinmok_tags %}
```

---

## Admin-Only Tags

The following tags are intended for use in admin templates only. Using them in theme or frontend templates serves no purpose.

### add_class

Filter. Django Admin renders form fields through widgets, producing complete HTML strings that cannot be modified at the template layer.
`add_class` operates on these rendered HTML strings and appends CSS class names to the first tag it finds — a lightweight way to adjust
styling without rewriting widget logic.

If the element already has a `class` attribute, the new class names are appended to it. If not, a `class` attribute is created
automatically.

**Syntax:**

```django
{{ field.label_tag|add_class:"classname" }}
{{ field.field|add_class:"classname1 classname2" }}
```

**Example:**

```django
{{ field.label_tag|add_class:"form-label required" }}
{{ field.field|add_class:"form-control is-invalid" }}
```

### alert

Inclusion tag. Renders an alert component using Tabler's icon set and HTML structure, so you do not need to write the markup or class names
manually.

**Syntax:**

```django
{% alert title [level="danger"] [description=""] [variant=""] [dismiss=False] [extra_class=""] [link_url=""] [link_text=""] %}
```

**Parameters:**

| Parameter     | Type | Default    | Description                                                                                      |
|---------------|------|------------|--------------------------------------------------------------------------------------------------|
| `title`       | str  | required   | Alert heading; not rendered if empty                                                             |
| `level`       | str  | `'danger'` | Alert type: `danger` / `warning` / `success` / `info`                                            |
| `description` | str  | `None`     | Optional body text, displayed below the heading                                                  |
| `variant`     | str  | `''`       | Visual intensity. `important` uses a high-saturation solid color; `minor` uses a very light tint |
| `dismiss`     | bool | `False`    | If `True`, renders a close button                                                                |
| `extra_class` | str  | `''`       | Additional CSS classes appended to the alert element                                             |
| `link_url`    | str  | `None`     | Action link URL; requires `link_text` to take effect                                             |
| `link_text`   | str  | `None`     | Action link label; requires `link_url` to take effect                                            |

**Example:**

```django
{% alert "An error occurred!" %}
{% alert "Success" level="success" %}
{% alert "Heads up" level="warning" description="This action cannot be undone." variant="important" %}
{% alert "Welcome, member" level="info" description="You now have access to all member features." dismiss=True link_text="Log in" link_url="/login" %}
```

---

## General Tags

The following tags and filters can be used in both admin and frontend templates.

### truncate_filename

Filter. Truncates long filenames for display, while always preserving the file extension. When the filename exceeds the specified length,
the base name is shortened and an ellipsis (`…`, Unicode U+2026, language-neutral) is inserted. The specified length includes the extension
and the ellipsis character.

**Syntax:**

```django
{{ filename|truncate_filename }}
{{ filename|truncate_filename:length }}
```

The default maximum length is 20 characters.

**Example:**

Given the filename `8a8456b22afa451480a17038b9e51c51.jpg` with a length of 10:

```django
{{ filename|truncate_filename:10 }}
```

Output: `8a845….jpg`

---

### icon

Simple tag. Renders an inline SVG icon from a sprite file.

Pinmok includes a sprite file containing a subset of the Tabler icon set. Icon names prefixed with `tabler-` are served from this built-in
file. Any other name is treated as a custom icon and resolved from a custom sprite file. The default path for the custom sprite is defined
by the built-in constant `CUSTOM_SPRITE_FILE`; to use a different path, override it in `settings.py`:

```python
CUSTOM_SPRITE_FILE = 'path/to/your/sprite.svg'
```

All available icons can be browsed in the **Icons Management** page in the admin.

**Syntax:**

```django
{% icon icon_name [css_class] [size] %}
```

**Parameters:**

| Parameter   | Type | Default  | Description                              |
|-------------|------|----------|------------------------------------------|
| `icon_name` | str  | required | Symbol ID in the sprite file             |
| `css_class` | str  | `''`     | CSS classes added to the `<svg>` element |
| `size`      | int  | `24`     | Icon width and height in pixels          |

> All parameters are positional; parameter names are not required.

**Example:**

```django
{% icon "tabler-home" %}
{% icon "tabler-user" "icon nav-icon" %}
{% icon "my-custom-icon" "icon" 20 %}
```

---

### media_url

Simple tag. Resolves a media file path to a full URL.

Django's `FieldFile` objects expose a `.url` property that can be used directly in templates. However, when working with raw path strings
retrieved from the database or cache — rather than `FieldFile` objects — `.url` is not available. `media_url` is designed for exactly this
situation.

The tag resolves paths using Django's `default_storage` backend, so its behavior is consistent with your project's storage configuration:
local storage returns a path prefixed with `MEDIA_URL`; third-party backends such as S3 or Alibaba Cloud OSS return the full URL generated
by that backend. Absolute URLs are returned as-is, and empty or unresolvable paths return an empty string.

**Syntax:**

```django
{% media_url path %}
{% media_url path as var %}
```

**Example:**

```django
<img src="{% media_url object.image %}">

{# Assign to a variable first #}
{% media_url object.image as url %}
<img src="{{ url }}">
```

---

### site_info

Simple tag. Returns a dictionary of site configuration data, sourced from the site information settings in the admin. The dictionary
includes the site name, ICP filing number, contact details, social media links, and more. Results are cached at the `ConfigService` layer,
so calling this tag multiple times in a template does not trigger additional database queries.

**Syntax:**

```django
{% site_info as var %}
```

**Example:**

```django
{% site_info as site %}
<title>{{ site.site_name }}</title>
<p>{{ site.icp }}</p>
```

**Available fields:**

| Field                     | Description                                |
|---------------------------|--------------------------------------------|
| `site_name`               | Site name                                  |
| `site_slogan`             | Site slogan                                |
| `site_logo`               | Site logo image path                       |
| `icp`                     | ICP filing number                          |
| `pns`                     | Public security filing number              |
| `service_phone`           | Service phone number                       |
| `service_email`           | Service email address                      |
| `contact_address`         | Contact address                            |
| `wechat_qrcode`           | WeChat QR code image path                  |
| `wechat_mini_program`     | WeChat Mini Program QR code image path     |
| `wechat_official_account` | WeChat Official Account QR code image path |
| `facebook_link`           | Facebook profile URL                       |
| `x_link`                  | X (Twitter) profile URL                    |
| `linkedin_link`           | LinkedIn profile URL                       |
| `instagram_link`          | Instagram profile URL                      |

Image fields return storage paths. Use `{% media_url %}` to resolve them to full URLs.

---

### links

Simple tag. Returns the list of enabled Partner Links, ordered by `sort_order`. Results are cached to avoid repeated database queries.
Partner Links are managed in the **Partner Links** section of the admin.

**Syntax:**

```django
{% links as var %}
```

Each item contains the following fields:

| Field   | Description              |
|---------|--------------------------|
| `title` | Link name                |
| `url`   | Link URL                 |
| `image` | Image path; may be empty |

**Example:**

```django
{% links as link_list %}
{% for link in link_list %}
    <a href="{{ link.url }}">{{ link.title }}</a>
{% endfor %}
```

---

### Navigation Tags

`navigation` and `navblock` are a pair of block tags used together to render a navigation tree for a given group. Any depth of nesting is
supported.

#### The Group Field

Pinmok uses a plain string field to distinguish between different navigation locations, such as the main menu, footer, or sidebar. Each
navigation item in the admin has a **Group** field; items with the same value belong to the same navigation.

There are no predefined group names — you decide on the values yourself (for example `main`, `footer`, or `sidebar`). To make data entry
more convenient and avoid typos, the Group field in the admin uses a `<datalist>` control, which lets you type freely or pick from
previously entered values.

In templates, the group name is passed as an argument to `{% navigation %}`. In most cases, it comes from a variable defined in the theme
configuration file (see the Theme chapter), where the theme developer declares the variable and the site operator fills in the actual value
through the admin:

```django
{# nav.group is a fieldset variable defined in the theme config, filled in by the site operator #}
{% navigation nav.group %}
    ...
{% endnavigation %}
```

If the group name is known at development time — for example, when a team has agreed on a fixed naming convention — you can also pass it as
a string literal:

```django
{% navigation "main" %}
    ...
{% endnavigation %}
```

#### Structure

```django
{% navigation group %}
    {% navblock 1 %}
        ...HTML for level 1...
    {% endnavblock %}
    {% navblock 2 %}
        ...HTML for level 2...
    {% endnavblock %}
    {% navblock default %}
        ...HTML for all other levels...
    {% endnavblock %}
{% endnavigation %}
```

The `navblock` argument is a level number starting at 1, or `default` to match any level without an explicit definition. When rendering a
given level, Pinmok uses the matching `navblock` if one exists; otherwise it falls back to `default`. If neither is defined, that level is
not rendered. In practice, defining `navblock 1` and `navblock default` is enough to handle any depth.

#### Variables Available Inside navblock

| Variable        | Type | Description                                                                                                 |
|-----------------|------|-------------------------------------------------------------------------------------------------------------|
| `item.url`      | str  | Navigation item URL; may be empty for parent groups — use `item.url                                         |default:'#'`                           |
| `item.name`     | str  | Display name of the navigation item                                                                         |
| `item.icon`     | str  | Icon name for use with `{% icon %}`; empty string if no icon is set — check before use                      |
| `item.target`   | str  | The `target` attribute for the link; empty string if not set                                                |
| `item.children` | list | List of child nodes; useful for checking whether the current item has children                              |
| `children`      | str  | Recursively rendered HTML of all child nodes; output directly — no need to iterate `item.children` manually |

#### Full Example

The following example renders a two-level navigation: first-level items appear as navbar entries and become dropdown menus when they have
children; second-level items and deeper appear as dropdown items and become nested dropdowns when they have children.

```django
{% navigation nav.group %}

    {% navblock 1 %}
        {% if item.children %}
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle"
                   href="{{ item.url|default:'#' }}"
                   data-bs-toggle="dropdown"
                   role="button">
                    {% if item.icon %}
                        <span class="nav-link-icon">{% icon item.icon "icon" %}</span>
                    {% endif %}
                    <span class="nav-link-title">{{ item.name }}</span>
                </a>
                <div class="dropdown-menu">{{ children }}</div>
            </li>
        {% else %}
            <li class="nav-item">
                <a class="nav-link" href="{{ item.url }}">
                    {% if item.icon %}
                        <span class="nav-link-icon">{% icon item.icon "icon" %}</span>
                    {% endif %}
                    <span class="nav-link-title">{{ item.name }}</span>
                </a>
            </li>
        {% endif %}
    {% endnavblock %}

    {% navblock default %}
        {% if item.children %}
            <div class="dropend">
                <a class="dropdown-item dropdown-toggle"
                   href="{{ item.url|default:'#' }}"
                   data-bs-toggle="dropdown"
                   role="button">
                    {{ item.name }}
                </a>
                <div class="dropdown-menu">{{ children }}</div>
            </div>
        {% else %}
            <a class="dropdown-item" href="{{ item.url }}">{{ item.name }}</a>
        {% endif %}
    {% endnavblock %}

{% endnavigation %}
```

`children` is the result of recursive rendering. When `navblock default` renders level 2, the `{{ children }}` inside it renders level 3
using the same `navblock default` template — and so on until there are no more child items.

---

### slider

Simple tag. Returns the list of active slider items for a given group, ordered by `sort_order`. Results are cached to avoid repeated
database queries. Slider items are managed in the **Sliders** section of the admin; the group field works the same way as it does for
navigation — items with the same group value belong to the same slider.

As with navigation, the group name typically comes from a variable defined in the theme configuration file, filled in by the site operator
through the admin.

**Syntax:**

```django
{% slider group as var %}
```

Each item contains the following fields:

| Field      | Description                                                |
|------------|------------------------------------------------------------|
| `title`    | Slide title                                                |
| `subtitle` | Subtitle; may be empty                                     |
| `image`    | Image path; use `{% media_url %}` to resolve to a full URL |
| `link`     | Click-through URL; may be empty                            |

**Example:**

```django
{% slider nav.slide_group as slides %}
{% for slide in slides %}
    <a href="{{ slide.link }}">
        {% media_url slide.image as slide_url %}
        <img src="{{ slide_url }}" alt="{{ slide.title }}">
        {% if slide.subtitle %}<p>{{ slide.subtitle }}</p>{% endif %}
    </a>
{% endfor %}
```