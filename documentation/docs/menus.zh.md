# 菜单系统

## 概述

Django Admin 的菜单完全由已注册的模型驱动，没有对应模型便无法生成菜单入口，非数据操作类的业务功能也因此难以集成到后台。Pinmok 对此进行了扩展，允许开发者在
`menus.py` 中自由定义指向任意 URL 的菜单项，使得纯逻辑业务、工具页面、统计视图等非模型功能同样能够出现在后台菜单中。开发者既可以构建完全不依赖模型的独立应用，
也可以将模型管理与自定义业务视图混合组织在同一套菜单结构下。

## 定义菜单

### 文件位置

在应用目录下新建 `menus.py` 文件。同步菜单时，系统会自动扫描每个已安装应用下的 `menus.py`，读取其中的菜单定义。该文件名为约定文件名，不可更改。

### 定义示例

Pinmok 提供了菜单定义快捷函数 `menu()`，可方便地声明菜单结构。

> **注意：** 菜单定义不限层级，但后台界面最多只支持三级显示，超过三级的菜单项将被丢弃。

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

以上定义在后台生成的菜单结构为：

```text
Blog management
    ├─ Posts
    ├─ Category
    └─ Statistics
        ├── Data Dashboard
        └── Traffic Analysis
```

### 参数说明

- **`admin_menu`**：约定变量名，系统从该变量中读取菜单定义，类型为列表。
- **`menu()`**：菜单项定义函数，从 `pinmok.core` 引入。第一个参数 `key` 为位置参数，其余均为关键字参数。
    - **`key`**（必填）：菜单项的唯一标识符，`str` 类型。同一应用内不可重复。
    - **`title`**（必填）：菜单标题，`str` 类型，显示在后台菜单上。系统会自动调用多语言翻译，无需在定义时使用 `gettext` 处理，只需维护对应的翻译语言包即可。
    - **`url`**：菜单项指向的页面地址，`str` 类型。支持两种写法：以 `/` 开头则视为绝对路径直接使用；否则视为 URL name，系统在同步时自动调用
      `reverse()` 解析为实际路径。若解析失败，同步操作将立即报错。
    - **`parent_key`**：父级菜单项的 `key`，`str` 类型。不设置则作为根菜单项。
    - **`sort_order`**：排序权重，`int` 类型，默认值为 `10000`。同级菜单按该值升序排列，数值越小越靠前。
    - **`remark`**：备注信息，`str` 类型，不显示在前端，仅供开发者记录说明。

## 同步菜单

菜单定义完成后，需要手动执行同步操作，将菜单数据写入数据库，后台才能正常显示。

### 如何同步

使用超级用户账号登录后台，在左侧菜单栏顶部有一个红色的 `☰` 图标，该入口仅超级用户可见。点击后会弹出确认提示——同步操作会清除当前所有菜单数据并重新写入，此操作不可逆。
确认后刷新页面，新菜单即可生效。

### 何时需要重新同步

凡是菜单定义发生变更，均需重新同步，例如：

- 安装了新应用
- 修改了 `menus.py` 中的菜单定义

## 与 app_list 的关系

Pinmok 在渲染菜单时，会自动将 `menus.py` 定义的菜单与 Django Admin 的 `app_list`（即模型注册菜单）按应用合并。同一 `app_label` 下，
两者的菜单项会合并在同一根节点下，而不是并列为两个独立的根菜单。

合并后的菜单统一按 `sort_order` 排序。Pinmok 在 `ModelAdmin` 上扩展了 `menu_sort_order` 属性（默认值 `10000` ），用于控制模型菜单
项在合并后的排序位置。如果后台存在混合菜单，请注意合理设置各菜单项的排序值。

## 菜单缓存

Pinmok 对菜单数据实施两层缓存，以减少数据库查询开销。

**第一层：数据库菜单缓存**

从数据库加载的菜单数据整体缓存，有效期 1 小时。缓存键带有版本号，每次同步后版本号自动递增，旧缓存立即失效。

**第二层：用户菜单缓存**

经 `app_list` 合并后的最终菜单树按用户维度缓存，同样基于版本号失效机制，同步后自动清除。

> **开发期注意：** 修改 `menus.py` 后须重新执行同步，同步会自动清除缓存。若菜单显示未更新，请确认同步是否已执行。