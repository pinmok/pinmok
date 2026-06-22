# Menu System

If you're already familiar with how Pinmok menus work, expand the **Quick Start** below and skip the rest.

??? abstract "Quick Start"

    **1. Create `menus.py` in your app's root directory**

    **2. Define your menus**

    ```python
    # Import the menu definition function
    from pinmok.core import menu

    # admin_menu is a reserved variable — do not change it
    admin_menu = [
        menu('blog', title='Blog', icon='tabler-book', sort_order=0),  # root item, no parent_key
        menu('posts', title='Posts', url='posts', parent_key='blog', sort_order=100),  # child item
        menu('category', title='Category', url='category', parent_key='blog', sort_order=200),
    ]
    ```

    Parameters:

    - `key`: First positional argument. Unique identifier for the menu item, must be unique within the same app.
    - `title`: Menu label shown in the admin navigation. Write plain strings — i18n is handled automatically at render time. Just maintain the translations in your `.po` files.
    - `url`: Page URL. Accepts a URL name or an absolute path starting with `/`. Can be omitted for root items with no direct link.
    - `parent_key`: The `key` of the parent item. Omit to make this a root item.
    - `sort_order`: Sort weight. Lower values appear first. Default is `10000`.
    - `icon`: Icon name from the admin icon library or a custom icon, e.g. `tabler-book`.
    - `remark`: Developer note. Not displayed in the frontend.

    **3. Log in to the admin, click the red `☰` icon at the top of the left sidebar, and confirm the sync**

    Refresh the page — your menus will appear.

---

## Overview

Django Admin's navigation is entirely driven by registered models. Without a corresponding model, there is no menu entry, making it
difficult to integrate non-CRUD business functions into the admin. Pinmok extends this by allowing developers to define menu items in
`menus.py` that can point to any URL, so pure business logic pages, utility views, statistics dashboards, and other non-model functions can
all appear in the admin navigation. You can build apps that have no models at all, or mix model management and custom business views within
the same menu structure.

## Defining Menus

### File Location

Create a `menus.py` file in your app's root directory. During menu synchronization, Pinmok scans the root directory of each installed app
for a menus.py file and loads the definitions. The file must be in the app root — placing it in a subdirectory or sub-package will
prevent it from being discovered. The filename is a system convention and cannot be changed.

### Basic Structure

The structure of `menus.py` is straightforward: import the `menu()` function from `pinmok.core`, define all menu items as a list, and assign
it to the reserved variable name `admin_menu`. The system reads menu definitions from this variable during synchronization. The variable
name cannot be changed.

```python
from pinmok.core import menu

admin_menu = [
    menu('blog', title='Blog Management', icon='tabler-book', sort_order=0),
    menu('posts', title='Posts', url='posts', parent_key='blog', sort_order=100),
    menu('category', title='Category', url='category', parent_key='blog', sort_order=200),
    menu(
        'stat',
        title='Statistics',
        url='post_stat',
        parent_key='blog',
        sort_order=300,
        remark='Relevant data statistics of the posts.',
    ),
    menu('dashboard', title='Data Dashboard', url='post_dashboard', parent_key='stat', sort_order=100),
    menu('traffic', title='Traffic Analysis', url='post_traffic', parent_key='stat', sort_order=200),
]
```

The menu structure this produces in the admin:

```text
Blog Management
    ├─ Posts
    ├─ Category
    └─ Statistics
        ├── Data Dashboard
        └── Traffic Analysis
```

An app can define multiple root menu items — there is no requirement to nest everything under a single root.

### Parameters

The first argument to `menu()` is `key`, a positional parameter. All others are keyword arguments:

**`key`** (required)

A unique identifier for the menu item, `str` type. Must be unique within the same app. Used to establish parent-child relationships via
`parent_key` and for internal indexing.

**`title`** (required)

The menu label displayed in the admin navigation, `str` type. Write plain strings — do not wrap with `gettext`. Internationalization is
automatic — Pinmok translates titles at render time using Django's standard i18n system. Simply add the translations to your `.po` files.`

**`url`**

The URL the menu item points to, `str` type, default `None`. Two formats are supported:

- Starting with `/` — treated as an absolute path and used as-is
- Otherwise, treated as a URL name; the system calls `reverse()` at sync time to resolve it to an actual path

If the URL name cannot be resolved, the sync operation will fail immediately with an error. Root items with no direct link typically do not
need a `url`.

**`parent_key`**

The `key` of the parent menu item, `str` type, default `None`. Omit to make this a root item.

**`sort_order`**

Sort weight, `int` type, default `10000`. Items at the same level are sorted in ascending order — lower values appear first.

**`icon`**

Menu icon, `str` type, default `None`. Specify an icon name from the admin icon library or your custom icon set, e.g. `tabler-book`.

**`permissions`**

Permission list, `list[str]` type, default `None`. Uses Django's standard permission string format, e.g. `["app.view_model"]`.

> **Note:** The `permissions` parameter is reserved for future use. Permission filtering is not implemented in the current version and has
> no effect.

**`remark`**

Developer note, `str` type, default `None`. Not displayed in the frontend — for internal documentation only.

### Depth Limit

The admin interface renders menus up to 3 levels deep (root → child → grandchild). Menu definitions themselves have no depth limit, but
items nested beyond the third level will not appear. Keep this in mind when designing your menu structure.

## Synchronizing Menus

Once you have defined your menus, you need to run a manual sync to write the menu data to the database before the admin can display them.

### How to Sync

Log in to the admin with a superuser account. At the top of the left sidebar, there is a red `☰` icon — this entry is only visible to
superusers. Clicking it will show a confirmation prompt. The sync operation clears all existing menu data and rewrites it from scratch; this
cannot be undone. After confirming, refresh the page and your new menus will be active.

### When to Re-sync

Any time your menu definitions change, you need to re-sync. Common cases include:

- Installing a new app
- Modifying menu definitions in `menus.py`

The sync operation automatically clears the menu cache — no manual cache management is needed.

## Relationship with Model Menus

When rendering the admin navigation, Pinmok automatically merges the menus defined in `menus.py` with Django Admin's model registration
menus (`app_list`). Under the same `app_label`, both sources are merged under a single root node rather than appearing as two separate root
menus.

If an app defines multiple root menu items, model menus will be merged under the first root item in the list. The current version does not
support specifying a different merge target — if you need to control which root item receives the model menus, adjust the order of root
items in your `admin_menu` list.

After merging, all items are sorted by `sort_order`. For model menu items, Pinmok adds a `menu_sort_order` attribute to `ModelAdmin` to
control their position within the merged menu. The default value is `10000`:

```python
@padmin.register(EmailConfig)
class EmailConfigAdmin(ConfigModelAdmin):
    menu_sort_order = 2000
```

If your admin has a mixed menu, make sure to set `sort_order` values thoughtfully to avoid unexpected ordering.

## Menu Caching

Pinmok applies two layers of caching to reduce database query overhead.

**Layer 1: Database menu cache**

The full set of menu data loaded from the database is cached as a whole, with a TTL of one hour. The cache key includes a version number
that increments automatically after each sync, immediately invalidating the previous cache.

**Layer 2: Per-user menu cache**

The final merged menu tree — after combining with `app_list` — is cached per user, also using the version-based invalidation mechanism. It
is cleared automatically after each sync.

> **During development:** After modifying `menus.py`, always re-sync. The sync will clear the cache automatically. If your menu changes are
> not showing up, check whether the sync has been run.