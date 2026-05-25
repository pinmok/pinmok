# Menu System

## Overview

Django Admin's menu is entirely driven by registered models — without a corresponding model, no menu entry can be generated, making it
difficult to integrate non-data-management business functions into the admin backend. Pinmok extends this mechanism by allowing developers
to
freely define menu items pointing to any URL in `menus.py`, so that pure business logic pages, tool pages, statistics views, and other
non-model features can appear in the admin menu as well. Developers can build applications that are completely independent of models, or mix
model management with custom business views under the same menu structure.

## Defining Menus

### File Location

Create a `menus.py` file in your application directory. When synchronizing menus, the system automatically scans the `menus.py` file under
each installed application and reads the menu definitions within. This filename is a convention and cannot be changed.

### Example

Pinmok provides the `menu()` shortcut function for declaring menu structures.

> **Note:** Menu definitions are not limited in depth, but the admin interface supports a maximum of three levels. Menu items beyond the
> third level will be ignored.

```python
from pinmok.core import menu

admin_menu = [
    menu('blog', title='Blog management', icon='tabler-book', sort_order=0),
    menu('category', title='Category', url='category', parent_key='blog', sort_order=200),
    menu('posts', title='Posts', url='posts', parent_key='blog', sort_order=100),
    menu(
        key='stat',
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

The menu structure generated in the admin backend will be:

```text
Blog management
    ├─ Posts
    ├─ Category
    └─ Statistics
        ├── Data Dashboard
        └── Traffic Analysis
```

### Parameter Reference

- **`admin_menu`**: The convention variable name from which the system reads menu definitions. Must be a list.
- **`menu()`**: The menu item definition function, imported from `pinmok.core`. The first parameter `key` is a positional argument; all
  others are keyword arguments.
    - **`key`** (required): A unique identifier for the menu item, `str` type. Must be unique within the same application.
    - **`title`** (required): The menu label displayed in the admin backend, `str` type. The system automatically passes this through the
      translation layer — no need to wrap it with `gettext` at definition time; simply maintain the corresponding translation files.
    - **`url`**: The target URL when the menu item is clicked, `str` type. Two formats are supported: a value starting with `/` is treated
      as an absolute path and used as-is; otherwise it is treated as a URL name and resolved via `reverse()` at sync time. If resolution
      fails, the sync operation will raise an error immediately.
    - **`parent_key`**: The `key` of the parent menu item, `str` type. If not set, the item becomes a root-level menu entry.
    - **`sort_order`**: Sort weight, `int` type, default `10000`. Sibling menu items are sorted in ascending order — lower values appear
      higher in the list.
    - **`remark`**: Optional internal note, `str` type. Not displayed in the frontend; intended for developer reference only.

## Synchronizing Menus

After defining your menus, you need to manually run a sync to persist menu configurations to the database before it appears in the admin
backend.

### How to Sync

Log in to the admin backend with a superuser account. At the top of the left sidebar, there is a red `☰` icon — this entry is only visible
to superusers. Clicking it will display a confirmation prompt, as the sync operation clears all existing menu data and rewrites it from
scratch. This action is irreversible. After confirming, refresh the page and the updated menus will take effect.

### When to Re-sync

A re-sync is required whenever menu definitions change, for example:

- A new application is installed
- The menu definitions in `menus.py` have been modified

## Relationship with app_list

When rendering the menu, Pinmok automatically merges the menus defined in `menus.py` with Django Admin's `app_list` (i.e., model-registered
menus) on a per-application basis. For the same `app_label`, both sets of menu items are merged under a single root node rather than
appearing as two separate root entries.

The merged menu is sorted uniformly by `sort_order`. Pinmok extends `ModelAdmin` with a `menu_sort_order` attribute (default `10000`) to
control the sort position of model menu items after merging. If your admin backend contains mixed menus, make sure to set sort values
carefully across all menu items.

## Menu Caching

Pinmok applies a two-layer caching strategy to reduce database query overhead.

**Layer 1: Database Menu Cache**

Menu data loaded from the database is cached as a whole, with a 1-hour TTL. The cache key includes a version number that is automatically
incremented after each sync, automatically invalidating old cache entries.

**Layer 2: Per-user Menu Cache**

The final menu tree — after merging with `app_list` — is cached per user, also based on the version number invalidation mechanism. The cache
is cleared automatically after each sync.

> **Note for development:** After modifying `menus.py`, you must re-run the sync. The sync automatically clears the cache. If the menu does
> not reflect your changes, verify that the sync has been executed.