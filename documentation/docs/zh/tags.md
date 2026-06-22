# 模板标签

如果你已经熟悉 Pinmok 的模板标签，可以直接展开**快速开始**查阅。

??? abstract "快速开始"

    **加载标签库**
    
    Pinmok 提供了两个标签库，一个是后台专用的，一个是前后台通用的。
    
    ```django
    {% load pinmok_admin_tags %}  {# 后台模板专用 #}
    {% load pinmok_tags %}        {# 前后台均可使用 #}
    ```


    **后台专用标签** `{% load pinmok_admin_tags %}`

    - `add_class`：过滤器，向渲染后的 HTML 元素追加 CSS 类名。

        ```django
        {{ field.label_tag|add_class:"form-label required" }}
        ```

    - `alert`：渲染一个提示框组件，除 `title` 为位置参数外，其余均为关键字参数。

        | 参数 | 类型 | 默认值 | 说明 |
        |---|---|---|---|
        | `title` | str | 必填 | 提示框标题，位置参数 |
        | `level` | str | `'danger'` | 提示框类型：`danger` / `warning` / `success` / `info` |
        | `description` | str | `None` | 正文内容，可选 |
        | `variant` | str | `''` | 视觉样式：`''` / `important` 高饱和实色 / `minor` 浅色 |
        | `dismiss` | bool | `False` | 是否显示关闭按钮 |
        | `extra_class` | str | `''` | 附加到提示框元素的 CSS 类名 |
        | `link_text` | str | `None` | 链接文本，需与 `link_url` 同时提供 |
        | `link_url` | str | `None` | 链接地址，需与 `link_text` 同时提供 |

        ```django
        {% alert "发生错误！" %}
        {% alert "操作成功" level="success" %}
        {% alert "请注意" level="warning" description="此操作不可撤销。" variant="important" %}
        {% alert "已成为会员" level="info" description="您可以享受全部会员功能。" dismiss=True link_text="登录" link_url="/login" %}
        ```

    **通用标签** `{% load pinmok_tags %}`
    
    - `truncate_filename`：过滤器，截断过长的文件名，保留扩展名。指定的字符数包含扩展名，默认为 20。

        ```django
        {{ filename|truncate_filename }}
        {{ filename|truncate_filename:10 }}
        ```
    
    - `icon`：渲染一个内联 SVG 图标，所有参数均为位置参数。

        | 参数          | 类型  | 默认值  | 说明                    |
        |-------------|-----|------|-----------------------|
        | `icon_name` | str | 必填   | sprite 文件中的 symbol ID |
        | `css_class` | str | `''` | 附加到 `<svg>` 元素的 CSS 类 |
        | `size`      | int | `24` | SVG 的宽高，单位像素          |
        
        ```django
        {% icon "tabler-home" %}
        {% icon "tabler-user" "icon nav-icon" %}
        {% icon "my-custom-icon" "icon" 20 %}
        ```

    - `media_url`：将媒体文件路径解析为完整 URL，行为与项目配置的存储后端保持一致。
    
        ```django
        {% media_url object.image as url %}
        <img src="{{ url }}">

        或
        <img src="{% media_url object.image %}">
        ```

    - `site_info`：返回站点配置字典，包含站点名称、备案信息、联系方式、社交账号等字段。通常先赋值给变量后使用。

        ```django
        {% site_info as site %}
        {{ site.site_name }}
        ```

    - `links`：返回已启用的友情链接列表，按 `sort_order` 排序。每个条目包含 `title`、`url`、`image` 字段。通常先赋值给变量后使用。

        ```django
        {% links as link_list %}
        {% for link in link_list %}
            <a href="{{ link.url }}">{{ link.title }}</a>
        {% endfor %}
        ```

    - `navigation` / `navblock`：block tag，根据分组渲染导航树，两者配合使用。

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

    - `slider`：返回指定分组下已启用的轮播图列表，按 `sort_order` 排序。每个条目包含 `title`、`subtitle`、`image`、`link` 字段。

        ```django
        {% slider nav.slide_group as slides %}
        {% for slide in slides %}
            {% media_url slide.image as slide_url %}
            <img src="{{ slide_url }}" alt="{{ slide.title }}">
        {% endfor %}
        ```

在模板开发中，往往会有很多操作或功能，需要在多个模板中重复使用。因此，Pinmok 内置了一组模板标签，将这些常用数据直接暴露给模板层，
避免在每个视图中手动传递上下文。如果内置标签不能满足需求，开发者可按 Django 标准方式编写自定义标签库。

Pinmok 按用途提供两个标签库：`pinmok_admin_tags` 仅供后台模板使用，包含后台界面专用的组件标签；`pinmok_tags` 前后台均可使用，
提供站点配置、导航、媒体文件等通用功能。

| 标签库                 | 加载方式                           | 适用范围      |
|---------------------|--------------------------------|-----------|
| `pinmok_admin_tags` | `{% load pinmok_admin_tags %}` | 后台模板专用    |
| `pinmok_tags`       | `{% load pinmok_tags %}`       | 前后台模板均可使用 |

在模板顶部加载对应的标签库即可使用，后台模板可以两个库同时加载：

```django
{% load pinmok_admin_tags pinmok_tags %}
```

---

## 后台专用标签

以下标签仅供后台模板使用，在主题模板或前台模板中调用无意义。

### add_class

过滤器。Django Admin 的表单字段由 widget 负责渲染，输出的是完整的 HTML 字符串，无法在模板层直接修改元素属性。`add_class` 作用于渲染后的 HTML
字符串，向第一个标签追加 CSS 类名，适合轻量的样式调整，无需重写 widget 逻辑。

若元素已有 `class` 属性，新类名追加在末尾；若没有，自动创建 `class` 属性。

**语法：**

```django
{{ field.label_tag|add_class:"类名" }}
{{ field.field|add_class:"类名 类名2" }}
```

**示例：**

```django
{{ field.label_tag|add_class:"form-label required" }}
{{ field.field|add_class:"form-control is-invalid" }}
```

### alert

inclusion tag。渲染一个提示框组件，封装了 Tabler 的图标与 HTML 结构，无需手写样式类和图标代码。

**语法：**

```django
{% alert title [level="danger"] [description=""] [variant=""] [dismiss=False] [extra_class=""] [link_url=""] [link_text=""] %}
```

**参数说明：**

| 参数            | 类型   | 默认值        | 说明                                           |
|---------------|------|------------|----------------------------------------------|
| `title`       | str  | 必填         | 提示框标题，为空时不渲染                                 |
| `level`       | str  | `'danger'` | 类型：`danger` / `warning` / `success` / `info` |
| `description` | str  | `None`     | 可选正文，显示在标题下方                                 |
| `variant`     | str  | `''`       | 视觉强度。默认为半透明样式；important 为高饱和实色；minor 为极淡的浅色  |
| `dismiss`     | bool | `False`    | 为 `True` 时渲染关闭按钮                             |
| `extra_class` | str  | `''`       | 附加到 alert 元素的额外 CSS 类                        |
| `link_url`    | str  | `None`     | 操作链接 URL，需与 `link_text` 同时提供才生效              |
| `link_text`   | str  | `None`     | 操作链接文字，需与 `link_url` 同时提供才生效                 |

**示例：**

```django
{% alert "发生错误！" %}
{% alert "操作成功" level="success" %}
{% alert "请注意" level="warning" description="此操作不可撤销。" variant="important" %}
{% alert "已成为会员" level="info" description="您可以享受全部会员功能。" dismiss=True link_text="登录" link_url="/login" %}
```

---

## 通用标签

以下标签与过滤器前后台模板均可使用。

### truncate_filename

过滤器。截断过长的文件名，同时保留文件扩展名，用于在界面上展示文件名时避免溢出。超出长度时，文件名主体被截断并替换为省略号
（…，Unicode U+2026，与语言环境无关），扩展名始终保留。注意，指定的最大长度包含扩展名和省略号在内。

**语法：**

```django
{{ filename|truncate_filename }}
{{ filename|truncate_filename:长度 }}
```

默认最大长度为 20 个字符。

**代码示例：**

文件名 8a8456b22afa451480a17038b9e51c51.jpg，指定长度为 10：

```django
{{ filename|truncate_filename:10 }}
```

输出：8a845….jpg

---

### icon

simple tag。从 sprite 文件渲染一个内联 SVG 图标。

Pinmok 内置了部分 Tabler 图标集的 sprite 文件。图标名以 `tabler-` 开头时，使用该内置文件；其他名称则被视为自定义图标，从自定义 sprite 文件中读取。
自定义文件的保存路径由框架内置常量 `CUSTOM_SPRITE_FILE` 指定，如需修改，在 `settings.py` 中覆盖该配置即可。

```python
CUSTOM_SPRITE_FILE = 'path/to/your/sprite.svg'
```

所有可用图标可在后台的**图标管理**页面查看。

**语法：**

```django
{% icon icon_name [css_class] [size] %}
```

**参数说明：**

| 参数          | 类型  | 默认值  | 说明                    |
|-------------|-----|------|-----------------------|
| `icon_name` | str | 必填   | sprite 文件中的 symbol ID |
| `css_class` | str | `''` | 附加到 `<svg>` 元素的 CSS 类 |
| `size`      | int | `24` | SVG 图标的宽高，单位像素        |

> 所有参数均为位置参数，无需指定参数名

**示例：**

```django
{% icon "tabler-home" %}
{% icon "tabler-user" "icon nav-icon" %}
{% icon "my-custom-icon" "icon" 20 %}
```

---

### media_url

simple tag。将媒体文件路径解析为完整 URL。

Django 的 `FieldFile` 对象提供 `.url` 属性，可以直接在模板中使用。但在某些场景下，持有的并不是 `FieldFile` 对象，而是从数据库或缓存中取出的原始路径字符串——此时
`.url` 不可用，`media_url` 正是为这种情况而设计的。

`media_url` 内部通过 Django 的 `default_storage` 后端解析路径，因此其行为与项目配置的存储后端保持一致：本地存储时返回 `MEDIA_URL`
拼接后的路径；使用第三方存储后端（如 S3、阿里云 OSS）或 CDN 时，返回对应后端生成的完整 URL。绝对 URL 原样返回，路径为空或无法解析时返回空字符串。

**语法：**

```django
{% media_url path %}
{% media_url path as var %}
```

**示例：**

```django
<img src="{% media_url path %}">


{# 也可以赋值给变量后使用 #}
{% media_url object.image as url %}
<img src="{{ url }}">
```

---

### site_info

simple tag。返回站点配置字典，数据来源为后台的站点信息配置，包含站点名称、备案信息、联系方式、社交账号等字段。数据在 `ConfigService`
层缓存，模板中频繁调用不会产生额外的数据库查询。

**语法：**

```django
{% site_info as var %}
```

**示例：**

```django
{% site_info as site %}
<title>{{ site.site_name }}</title>
<p>{{ site.icp }}</p>
```

**可用字段：**

| 字段                        | 说明           |
|---------------------------|--------------|
| `site_name`               | 站点名称         |
| `site_slogan`             | 站点标语         |
| `site_logo`               | 站点 Logo 图片路径 |
| `icp`                     | ICP 备案号      |
| `pns`                     | 公安网备案号       |
| `service_phone`           | 服务电话         |
| `service_email`           | 服务邮箱         |
| `contact_address`         | 联系地址         |
| `wechat_qrcode`           | 微信二维码图片路径    |
| `wechat_mini_program`     | 微信小程序二维码图片路径 |
| `wechat_official_account` | 微信公众号二维码图片路径 |
| `facebook_link`           | Facebook 链接  |
| `x_link`                  | X 链接         |
| `linkedin_link`           | LinkedIn 链接  |
| `instagram_link`          | Instagram 链接 |

图片类字段返回的是存储路径，建议配合 `{% media_url %}` 使用。

---

### links

simple tag。返回已启用的友情链接列表，按 `sort_order` 排序，结果缓存以减少数据库查询。友情链接数据在后台的**友情链接**中维护。

**语法：**

```django
{% links as var %}
```

每个条目包含以下字段：

| 字段      | 说明       |
|---------|----------|
| `title` | 链接名称     |
| `url`   | 链接地址     |
| `image` | 图片路径，可为空 |

**示例：**

```django
{% links as link_list %}
{% for link in link_list %}
    <a href="{{ link.url }}">{{ link.title }}</a>
{% endfor %}
```

---

### 导航标签

`navigation` 与 `navblock` 是一对配合使用的 block tag，用于根据导航分组渲染导航树，支持任意层级结构。

#### 分组概念

Pinmok 用一个字符串字段区分不同的导航位置（如主导航、底部导航、侧边栏等）。后台导航项管理界面中，每条导航项都有一个**分组**字段，字段值相同的导航项属于同一个导航。

分组字段没有预定义的枚举值，由使用者自行约定（如 `main`、`footer`、`sidebar`）。为方便输入，后台的分组字段使用 `<datalist>`
控件——既可以自由输入，也可以从已有值中选择，避免拼写不一致。

在模板中，分组名作为参数传给 `{% navigation %}`。通常情况下，分组名来自主题配置文件中定义的变量（详见主题章节），由主题开发者在配置文件中声明、由使用者在后台填写具体值：

```django
{# nav.group 是主题配置文件中定义的 fieldset 变量，由后台使用者填写 #}
{% navigation nav.group %}
    ...
{% endnavigation %}
```

如果分组名在开发阶段已经确定（例如团队内部约定），也可以直接使用字符串字面量：

```django
{% navigation "main" %}
    ...
{% endnavigation %}
```

#### 基本结构

```django
{% navigation 分组名 %}
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

`navblock` 的参数是层级编号（从 1 开始），`default` 匹配所有未显式定义的层级。渲染某一层级时，优先使用该层级对应的 `navblock`；若未定义，则回落到
`default`；若两者都没有，该层级不渲染。大多数情况下，只需定义 `navblock 1` 和 `navblock default` 即可覆盖所有层级。

#### navblock 内可用变量

| 变量              | 类型   | 说明                                               |
|-----------------|------|--------------------------------------------------|
| `item.url`      | str  | 导航项链接地址，父级分组可能为空，建议使用 `item.url                  |default:'#'`    |
| `item.name`     | str  | 导航项显示名称                                          |
| `item.icon`     | str  | 图标名，配合 `{% icon %}` 使用，无图标时为空字符串，使用前应判空          |
| `item.target`   | str  | 链接的 `target` 属性，无设置时为空字符串                        |
| `item.children` | list | 子节点列表，可用于判断当前项是否有子项                              |
| `children`      | str  | 子节点递归渲染后的 HTML 字符串，直接输出即可，无需手动遍历 `item.children` |

#### 完整示例

以下示例实现了一个两级导航：第一级渲染为导航栏项目，有子项时变为下拉菜单；第二级及以下渲染为下拉菜单项，有子项时变为嵌套下拉菜单。

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

`children` 是递归渲染的结果——`navblock default` 在渲染第二层时，其内部的 `{{ children }}` 会再次用同一个 `navblock default`
渲染第三层，以此类推，直到没有更深的子项为止。

---

### slider

simple tag。返回指定分组下已启用的轮播图列表，按 `sort_order` 排序，数据会被缓存以减少数据库查询。轮播图数据在后台的**幻灯片**中维护，按分组区分不同位置的轮播图。

与导航标签类似，分组名通常来自主题配置文件中定义的变量，由使用者在后台填写具体值。

**语法：**

```django
{% slider 分组名 as var %}
```

每个条目包含以下字段：

| 字段         | 说明                                    |
|------------|---------------------------------------|
| `title`    | 轮播图标题                                 |
| `subtitle` | 副标题，可为空                               |
| `image`    | 图片路径，建议配合 `{% media_url %}` 解析为完整 URL |
| `link`     | 点击跳转链接，可为空                            |

**示例：**

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