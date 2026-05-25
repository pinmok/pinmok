# 主题

Pinmok 配备专属主题系统，助力前端界面呈现。一个前端应用可拥有多个主题样式，均可在后台完成管控与切换操作。

## 概述

Pinmok 的主题系统以应用为单位进行管理。每个应用可安装多个主题，但同一时间只能启用一个。只要主题配置中的 app_label 指向同一应用，
这些主题便同属该应用，共享同一套启用逻辑。

每套主题由多个模板组成，模板的编写完全遵循 Django 官方规范。单个模板可按需搭配配置文件，且配置文件支持多语言。Pinmok
还提供了一组专属模板标签，将常见的站点配置数据作为全局模板变量公开，可在任意主题模板中直接调用。

## 主题结构

Pinmok 的主题目录需放置在 Django 可识别的模板目录下，并遵循固定的路径约定：

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

`themes/` 是固定目录名，其下每个子目录即为一套独立主题。每套主题必须包含 theme.json 作为主题描述文件，其余模板文件由应用自行决定。

`theme.json` 包含两类信息：主题的基本描述（名称、版本、作者、所属应用等），以及全局变量定义。全局变量在整套主题范围内生效，可在后台进行配置，并在所有模板中使用。
模板级别的变量则定义在各自的配置文件中，仅对对应模板生效。

## 模板与配置文件

Pinmok 模板语法规则与 Django 原生规范完全兼容。为便于模板拓展与二次开发，系统为每套模板单独配套配置文件，可用于登记模板文件名、绑定对应操作、预设模板所需变量等信息。

配置文件分为主题配置文件 theme.json与模板配置文件两类。 两类文件均支持定义通用变量与分组变量，核心差异在于作用域：
theme.json 中定义的配置全局生效，可在整个项目应用内调用；模板配置文件的配置仅对当前所属模板生效。

配置文件支持多语言适配，命名格式为：**配置文件名.语言代码.json**，例如：

- theme.json 默认配置文件，当系统未匹配到对应语言配置时，将自动读取该文件。**该文件必须存在。**
- theme.zh-hans.json 简体中文配置文件，后台切换至简体中文语言时生效。
- theme.en.json 英语配置文件，后台切换至英文语言时生效。

### theme.json

主题配置文件，用于定义主题各项属性，所有主题均必须包含该文件。文件支持配置参数如下：

- name：主题名称，唯一标识主题，**必填项**
- app_label：设定主题归属应用，限定使用范围，取值需为合法应用名，**必填项**
- version：主题版本号
- author：作者相关信息
- description：主题详细说明
- preview_url：主题预览访问链接
- vars：全局变量定义，参阅变量定义部分
- fieldsets：区块变量定义，参见变量定义部分

### 模板配置文件

配置文件需与对应模板文件命名保持一致。例如模板文件为list.html，其配套配置文件命名应为list.json。该文件支持配置参数如下：

- name：模板名称，用来标识模板，例如：主页，内容页等。**必填项**
- action：页面动作标识，表示这个配置文件对应的是哪种页面类型，比如列表页、详情页、首页等。它的值与 Django URL 的 name 参数保持一致，Pinmok
  通过它将配置文件与具体页面绑定。**必填项**
- order：排序权重，整数类型，数字越小排序越靠前。默认值是 10000
- vars：模板变量定义，参阅变量定义部分
- fieldsets：模板区块变量定义，参见变量定义部分

### 变量与区块

配置文件中定义的变量会被注入模板上下文，在模板中直接使用。

**变量（vars）**

```json
{
  "vars": {
    "company_name": {
      "title": "公司名称",
      "type": "text",
      "default": "Pinmok",
      "tip": "显示在页面头部的公司名称"
    }
  }
}
```

`vars` 下的每个键即为变量名，在模板中通过 `{{ company_name }}` 直接调用。各字段说明如下：

- `title`：变量在后台配置页面中显示的标题。**必填**
- `type`：变量类型。**必填**，可选值见下表。
- `default`：默认值。`text` 和 `textarea` 类型默认为空字符串，`number` 默认为 `0`，`boolean` 默认为 `False`。
- `tip`：提示文本，显示在后台配置项下方，用于说明该变量的用途。

| 类型           | 后台控件   | 说明       |
|--------------|--------|----------|
| `text`       | 单行文本框  |          |
| `textarea`   | 多行文本框  |          |
| `number`     | 数字输入框  |          |
| `boolean`    | 开关按钮   |          |
| `datasource` | 数据源选择器 | 见下方数据源说明 |

**区块（fieldsets）**

变量也可以按组归类，定义在 `fieldsets` 中。每个区块需设置 `title`，显示为后台配置页面中的分组标题，其下的 `vars` 定义与顶层变量完全一致。区块变量在模板中以嵌套方式访问，例如
`{{ sidebar.count }}`。

```json
{
  "fieldsets": {
    "sidebar": {
      "title": "侧边栏",
      "vars": {
        "count": {
          "title": "显示数量",
          "type": "number",
          "default": 5
        }
      }
    }
  }
}
```

### 数据源

数据源是 `datasource` 类型变量的数据提供方，后台配置页面会直接渲染数据源返回的控件，供用户选择。

**使用内置数据源**

Pinmok 内置了以下数据源：

| key      | 说明    |
|----------|-------|
| `nav`    | 导航分组  |
| `slider` | 轮播图分组 |

在配置文件中，将变量 `type` 设为 `datasource`，并通过 `source` 指定数据源 key：

```json
{
  "vars": {
    "main_nav": {
      "title": "主导航",
      "type": "datasource",
      "source": "nav",
      "multiple": false
    }
  }
}
```

- `source`：数据源 key。**必填**
- `multiple`：是否允许多选，默认为 `false`。

**自定义数据源**

自定义数据源需继承 Django `Widget` 或其子类，并注册到 Pinmok 的数据源注册表。返回值必须为 Widget 实例，因为后台会直接调用它渲染配置界面。

**参数传递规则**

配置文件中，除 `title`、`type`、`default`、`tip` 之外的所有字段，都会作为参数传入 Widget 的 `__init__`。因此，自定义 Widget 需要在 `__init__`
中声明对应的参数来接收。以 `multiple` 为例：配置文件中写 `"multiple": false`，Widget 的 `__init__` 声明 `multiple=False`，Pinmok 会自动完成传递。

如果 Widget 的 `__init__` 声明了 `**kwargs`，则所有额外参数都会原样传入；如果没有声明 `**kwargs`，Pinmok 只会传入 `__init__` 中明确声明的参数，其余忽略。

```python
from django.forms.widgets import Select
from pinmok.padmin.datasource import datasource


@datasource.register('my_source')
class MyDataSource(Select):
    def __init__(self, attrs=None, multiple=False, category=None):
        # multiple、category 均来自配置文件中的同名字段
        from .models import MyModel
        queryset = MyModel.objects.filter(category=category) if category else MyModel.objects.all()
        choices = [('', '请选择')] + [(obj.pk, obj.name) for obj in queryset]
        super().__init__(attrs=attrs, choices=choices)
```

注册完成后，即可在配置文件中通过 `"source": "my_source"` 使用，配置文件中的自定义字段会自动作为参数传入 Widget：

```json
{
  "vars": {
    "my_var": {
      "title": "我的变量",
      "type": "datasource",
      "source": "my_source",
      "multiple": false,
      "category": "news"
    }
  }
}
```

## 完整示例

以下示例展示了一套完整的主题配置，涵盖主题描述文件、模板配置文件及模板文件的完整用法。

**目录结构**

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
  "author": "惠达浪",
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