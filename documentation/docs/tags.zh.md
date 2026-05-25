# 内置模板标签

Pinmok 内置了一组模板标签与过滤器，供模板直接使用。按照用途，标签分别存放在两个文件中：后台专用标签位于 `pinmok_admin_tags`，前后台通用标签位于
`pinmok_tags`。

## 后台标签

后台专用标签，设计上仅供后台模板使用。

在模板中加载：

```django
{% load pinmok_admin_tags %}
```

### add_class

过滤器。Django Admin 的表单字段由 widget 负责渲染，输出的是完整的 HTML 字符串，开发者无法在模板层直接干预其属性。`add_class` 过滤器作用于渲染后的
HTML 字符串，允许在不重写 widget 逻辑的前提下，向字段元素追加 CSS 类名，适合轻量的样式调整。

**用法：**

```django
{{ field.label_tag|add_class:"form-label required" }}
{{ field.field|add_class:"form-control is-invalid" }}
```

支持任意 HTML 元素，若元素已有 `class` 属性，新类名会追加在末尾；若没有，则自动创建 `class` 属性。每次调用只作用于第一个标签。

---

### alert

inclusion tag。封装了 Tabler 的图标与 HTML 结构，快速渲染一个提示框组件，无需手写样式类和图标代码。

**用法：**

```django
{% alert "操作成功" level="success" %}
{% alert "请注意" level="warning" description="此操作不可撤销。" dismiss=True %}
{% alert "发生错误" level="danger" link_url="/help/" link_text="查看详情" %}
```

**参数说明：**

| 参数            | 类型   | 默认值        | 说明                                           |
|---------------|------|------------|----------------------------------------------|
| `title`       | str  | 必填         | 提示框标题，为空时不渲染                                 |
| `level`       | str  | `'danger'` | 类型：`danger` / `warning` / `success` / `info` |
| `description` | str  | `None`     | 可选正文，显示在标题下方                                 |
| `variant`     | str  | `''`       | 视觉变体：`important` / `minor`，留空为默认样式           |
| `dismiss`     | bool | `False`    | 为 `True` 时渲染关闭按钮                             |
| `extra_class` | str  | `''`       | 附加到 alert 元素的额外 CSS 类                        |
| `link_url`    | str  | `None`     | 操作链接 URL，需与 `link_text` 同时提供才生效              |
| `link_text`   | str  | `None`     | 操作链接文字，需与 `link_url` 同时提供才生效                 |

---

## 通用标签

前后台均可使用的标签与过滤器。

在模板中加载：

```django
{% load pinmok_tags %}
```

### truncate_filename

过滤器。截断过长的文件名，同时保留文件扩展名，用于在界面上展示文件名时避免溢出。

**用法：**

```django
{{ filename|truncate_filename }}
{{ filename|truncate_filename:30 }}
```

默认长度为 20 个字符。超出时，文件名主体会被截断并替换为省略号（`…`），扩展名始终保留。

---

### icon

simple tag。从 sprite 文件渲染一个内联 SVG 图标。图标名以 `tabler-` 开头时，使用 Pinmok 内置的 sprite 文件；其他名称使用自定义 sprite
文件，默认路径由内置常量指定，可在 `settings.py` 中通过 `CUSTOM_SPRITE_FILE` 覆盖。
> 所有图标在后台 `图标管理` 中可以查看。

**用法：**

```django
{% icon "tabler-home" %}
{% icon "tabler-user" "icon nav-icon" %}
{% icon "my-custom-icon" "icon" 20 %}
```

**参数说明：**

| 参数          | 类型  | 默认值  | 说明                    |
|-------------|-----|------|-----------------------|
| `icon_name` | str | 必填   | sprite 文件中的 symbol ID |
| `css_class` | str | `''` | 附加到 `<svg>` 元素的 CSS 类 |
| `size`      | int | `24` | SVG 的宽高，单位像素          |

---

### media_url

simple tag。将媒体文件路径解析为完整 URL。

Django 的 `FieldFile` 对象提供 `.url` 属性，可以直接在模板中使用。但在某些场景下，持有的并不是 `FieldFile` 对象，而是从数据库或缓存中取出的原始路径字符串——此时
`.url` 不可用，`media_url` 正是为这种情况而设计的。

`media_url` 内部通过 Django 的 `default_storage` 后端解析路径，因此其行为与项目配置的存储后端保持一致：

- 使用本地存储时，返回 `MEDIA_URL` 拼接后的路径
- 使用第三方存储后端（如 S3、阿里云 OSS）或 CDN 时，返回对应后端生成的完整 URL

也就是说，只要存储后端配置正确，`media_url` 在任何环境下都能返回可访问的地址，无需在模板中手动拼接路径。

**用法：**

```django
{# 路径字符串 #}
{% media_url object.image as url %}
<img src="{{ url }}">

{# 配合 site_info 使用 #}
{% site_info as site %}
{% media_url site.site_logo as logo_url %}
<img src="{{ logo_url }}">
```

绝对 URL（`http://` 或 `https://` 开头）原样返回，路径为空或无法解析时返回空字符串。

---

### site_info

simple tag。返回站点配置字典，数据来源为后台站点配置中的站点信息分类。

**用法：**

```django
{% site_info as site %}
<title>{{ site.name }}</title>
```

**可用字段：**

| 变量名                            | 说明           |
|--------------------------------|--------------|
| `site.site_name`               | 站点名称         |
| `site.site_slogan`             | 站点标语         |
| `site.site_logo`               | 站点 Logo 图片路径 |
| `site.icp`                     | ICP 备案号      |
| `site.pns`                     | 公安网备案号       |
| `site.service_phone`           | 服务电话         |
| `site.service_email`           | 服务邮箱         |
| `site.contact_address`         | 联系地址         |
| `site.wechat_qrcode`           | 微信二维码图片路径    |
| `site.wechat_mini_program`     | 微信小程序二维码图片路径 |
| `site.wechat_official_account` | 微信公众号二维码图片路径 |
| `site.facebook_link`           | Facebook 链接  |
| `site.x_link`                  | X 链接         |
| `site.linkedin_link`           | LinkedIn 链接  |
| `site.instagram_link`          | Instagram 链接 |

图片类字段返回的是存储路径，建议配合 `{% media_url %}` 标签使用。

---

### links

simple tag。返回已启用的外链列表，按 `sort_order` 排序，结果缓存以减少数据库查询。每个条目包含 `title`、`url`、`image` 字段。

**用法：**

```django
{% links as link_list %}
{% for link in link_list %}
    <a href="{{ link.url }}">{{ link.title }}</a>
{% endfor %}
```

---

### 导航标签

block tag。根据导航分组渲染导航树，支持任意层级结构。navigation 负责数据加载与递归渲染，navblock 负责定义每个层级的 HTML 模板片段，两者必须配合使用。

导航数据在后台管理，按分组区分不同导航位置（如主导航、底部导航、侧边栏等）。分组名来自模板配置变量，由用户在后台选择，详见模板配置章节。

#### 基本结构

```django
{% navigation nav.category %}
    {% navblock 1 %}
        ...第一层的 HTML...
    {% endnavblock %}
    {% navblock 2 %}
        ...第二层的 HTML...
    {% endnavblock %}
    {% navblock default %}
        ...其余层级的 HTML...
    {% endnavblock %}
{% endnavigation %}
```

#### 层级匹配规则

渲染某一层级时，优先使用该层级对应的 `navblock`；若未显式定义，则回落到 `default`；若两者都没有，该层级不渲染。利用这个规则，大多数情况下只需定义
`navblock 1` 和 `navblock default` 两个模板片段即可覆盖所有层级。

#### `navblock` 内可用变量

| 变量              | 类型   | 说明                                                |
|-----------------|------|---------------------------------------------------|
| `item.url`      | str  | 导航项链接地址，父级分组可能没有实际链接，建议使用 `item.url\|default:'#'` |
| `item.name`     | str  | 导航项显示名称                                           |
| `item.icon`     | str  | 图标名，配合 `{% icon %}` 标签使用，无图标时为空字符串，使用前应判空         |
| `item.target`   | str  | 链接的 `target` 属性，如 `_blank`，无设置时为空字符串              |
| `item.children` | list | 子节点列表，可用于判断当前项是否有子项                               |
| `children`      | str  | 子节点递归渲染后的 HTML 字符串，直接输出即可，无需手动遍历 `item.children`  |

#### 完整示例

以下示例实现了一个两级导航：第一级渲染为导航栏项目，有子项时变为下拉菜单；第二级及以下渲染为下拉菜单项，有子项时变为嵌套下拉菜单。

```django
{% navigation nav.category %}

    {% navblock 1 %}
        {% if item.children %}
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle"
                   href="{{ item.url|default:'#' }}"
                   data-bs-toggle="dropdown"
                   role="button">
                    {% if item.icon %}
                        <span class="nav-link-icon">{% icon item.icon 'icon' %}</span>
                    {% endif %}
                    <span class="nav-link-title">{{ item.name }}</span>
                </a>
                <div class="dropdown-menu">{{ children }}</div>
            </li>
        {% else %}
            <li class="nav-item">
                <a class="nav-link" href="{{ item.url }}">
                    {% if item.icon %}
                        <span class="nav-link-icon">{% icon item.icon 'icon' %}</span>
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

`children` 是递归渲染的结果——`navblock default` 在渲染第二层时，其内部的 `{{ children }}` 会再次用同一个 `navblock default` 渲染第三层，以此类推，
直到没有更深的子项为止。

---

### slider

simple tag。返回指定分组下已启用的轮播图列表，按 `sort_order` 排序，结果缓存以减少数据库查询。

轮播图数据在后台管理，按分组区分不同位置的轮播图。分组名来自模板配置变量，由用户在后台选择，详见模板配置章节。

#### 用法：

```django
{% slider 'home' as slides %}
{% for slide in slides %}
    <a href="{{ slide.link }}">
        <img src="{% media_url slide.image %}" alt="{{ slide.title }}">
        {% if slide.subtitle %}<p>{{ slide.subtitle }}</p>{% endif %}
    </a>
{% endfor %}
```

#### 返回字段：

| 字段         | 说明                                      |
|------------|-----------------------------------------|
| `title`    | 轮播图标题                                   |
| `subtitle` | 副标题，可为空                                 |
| `image`    | 图片路径，建议配合 `{% media_url %}` 标签解析为完整 URL |
| `link`     | 点击跳转链接，可为空                              |
