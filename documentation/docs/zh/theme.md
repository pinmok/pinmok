# 主题

如果你已经熟悉了主题机制，可以展开**快速开始**，进行快速查阅。

??? abstract "快速开始"

    1. **创建主题目录**

        在 Django 能够找到的模板目录中，按以下结构新建主题文件夹：
    
        ```text
        templates/              → Django 模板文件夹
        └── themes/             → 主题文件夹，名称必须为 themes
            └── mytheme/        → 你的模板文件夹
                ├── theme.json  → 主题描述文件
                ├── index.html  → 主题模板文件
                └── index.json  → 模板配置文件
        ```

    2. **编写主题描述文件 theme.json**

        每个主题目录下都必须包含一个 主题配置文件（theme.json），用于描述该主题的元信息、变量定义和页面模板映射。在该文件中定义的变量是全局可用的，
        即任何模板都可以直接调用。

        ```json
        {
          "name": "My Theme",
          "app_label": "myapp",
          "version": "1.0.0",
          "vars": {
            "site_title": {
              "title": "站点标题",
              "type": "text",
              "default": "我的站点"
            }
          }
        }
        ```

    3. **编写模板配置文件**

        配置文件名须与模板文件名一致（仅扩展名不同）。action 的值须与渲染该模板的视图所对应的 URL name 一致。
        
        ```json
        {
          "name": "首页",
          "action": "myapp_index",
          "vars": {
            "banner_text": {
              "title": "横幅文字",
              "type": "text",
              "default": "欢迎访问"
            }
          },
          "fieldsets": {
            "sidebar": {
              "title": "侧边栏",
              "vars": {
                "title": {
                  "title": "侧边栏标题",
                  "type": "text",
                  "default": "最新文章"
                },
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

    4. **编写模板文件**

        配置文件中声明的变量可在模板中直接使用：

        ```html
        <title>{{ site_title }}</title>
        <h1>{{ banner_text }}</h1>

        <aside>
            <h2>{{ sidebar.title }}</h2>
            <p>显示数量：{{ sidebar.count }}</p>
        </aside>
        ```

    5. **注册自定义数据源（可选）**

        如需使用自定义数据源，在应用根目录创建 datasource.py，将数据源注册为 Django Widget 的子类。Pinmok 会直接调用它渲染后台配置控件，
        因此注册的类必须是可实例化的 Widget 子类。

        ```python
        # myapp/datasource.py
        from django.forms.widgets import Select
        from pinmok.padmin.datasource import datasource

        @datasource.register('my_source')
        class MyDataSource(Select):
            def __init__(self, attrs=None):
                choices = [('', '请选择'), ('a', '选项 A'), ('b', '选项 B')]
                super().__init__(attrs=attrs, choices=choices)
        ```

    6. **在后台安装并激活主题**

        进入后台主题管理页面，找到 mytheme，依次点击安装和激活，主题即刻生效。激活后即可在配置页面对各模板变量进行设置。

## 概述

Pinmok 提供了一整套主题管理机制，方便开发者为具体应用搭建可配置的前端界面。主题以 Django 模板为载体，配套结构化的 JSON
配置文件，通过后台可视化界面管理模板变量，Pinmok 在渲染时自动将当前配置值注入模板上下文，无需修改视图代码。

配置文件的引入是为了解决一类特定问题：某些数据在开发阶段无法确定，只有在实际部署使用时才能由使用者决定，例如侧边栏显示哪个文章分类、导航绑定哪组链接。
配置文件将这类决策从代码中剥离，交由使用者在后台自行设定，模板代码本身无需改动。配置文件并非必须，不需要后台配置的模板可以不提供。

主题系统以应用为单位进行管理。每个应用可以独立安装多套主题，同一时间只能启用一套。配置文件支持多语言，Pinmok 会根据当前激活的语言自动选择对应版本。

## 主题结构

主题目录需放置在 Django 可识别的模板搜索路径下，并遵循固定的路径约定：

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

`themes/` 是固定目录名，其下每个子目录对应一套独立主题，目录名即为该主题的标识符。每套主题必须包含 `theme.json` 作为主题描述文件，
其余模板文件及配置文件由开发者根据实际需要自行决定。

将主题目录放置到位后，进入后台主题管理页面（若已在该页面，刷新一次），系统会自动扫描 `themes/` 目录并列出所有已识别的主题，之后即可在界面上执行安装和激活操作。

## 主题管理

### 安装与激活

![安装主题](/assets/images/theme_install.zh.jpg)

主题放置到位并被系统识别后，在后台主题管理页面点击**安装**，Pinmok 会读取 `theme.json` 及所有模板配置文件，将主题信息和变量初始值写入数据库。安装完成后，点击
**激活**即可将该主题设为当前生效的主题。

同一应用下只能有一套主题处于激活状态。激活新主题时，同应用下原有的激活主题会自动停用，无需手动操作。

![管理主题](/assets/images/theme_config.zh.jpg)

卸载主题只删除数据库记录，不会删除文件。已激活的主题不能卸载，需先激活其他主题后再执行卸载。

### 重置主题

!!! danger "重置会清空所有已配置的变量值"

    重置操作会删除主题在数据库中的全部记录，并重新从 JSON 文件读取初始值写入。**所有在后台配置页面中修改过的变量值都会丢失，且无法恢复。**

    配置一套主题的变量可能需要投入大量时间，请在确认不再需要当前配置时，再执行重置操作。如果只是更新了模板文件，无需重置；只有当 JSON 配置文件的结构发生变化
    （新增或删除了变量），才需要通过重置同步到数据库。

## 配置文件

Pinmok 的配置文件分为两类：主题配置文件 `theme.json` 和模板配置文件。两类文件均支持定义变量（`vars`）和区块变量（`fieldsets`），核心区别在于作用域——
`theme.json` 中的变量在整套主题范围内全局生效，模板配置文件中的变量仅对对应模板生效。

模板配置文件是可选的。没有配置文件的模板可以被视图直接调用渲染，但不参与变量注入，也不会出现在后台配置页面中。
action 字段的作用是在运行时将配置与具体页面绑定——Pinmok 通过它找到对应的模板配置并合并变量。同一 action 可以对应多个模板配置文件，开发者可以据此实现
同一页面的多模板切换，例如为不同状态的内容分别配置独立的展示模板。

### 多语言支持

配置文件支持按语言提供不同内容，命名格式为 `文件名.语言代码.json`。以主题配置文件为例：

- `theme.json`：默认配置文件，**必须存在**。当系统未匹配到当前语言对应的配置文件时，自动回退到此文件。
- `theme.zh-hans.json`：简体中文配置文件，后台切换至简体中文时生效。
- `theme.en.json`：英语配置文件，后台切换至英文时生效。

模板配置文件遵循相同规则，例如 `index.json`、`index.zh-hans.json`、`index.en.json`。

!!! tip "提示"

    语言代码请必须使用 Django 系统内的语言编码（如 zh-hans、en-us），因为 Pinmok 会获取当前语言编码，并根据该编码查找对应的配置文件。

### theme.json

`theme.json` 是主题描述文件，所有主题均必须包含。支持的字段如下：

| 字段            | 必填 | 说明                                      |
|---------------|----|-----------------------------------------|
| `name`        | 是  | 主题名称，用于在后台界面中标识主题                       |
| `app_label`   | 是  | 主题归属应用，必须是已安装的合法应用名                     |
| `version`     |    | 主题版本号                                   |
| `author`      |    | 作者信息                                    |
| `description` |    | 主题说明                                    |
| `preview_url` |    | 主题预览链接                                  |
| `vars`        |    | 全局变量定义，参见[变量与区块](#vars-and-fieldsets)   |
| `fieldsets`   |    | 全局区块变量定义，参见[变量与区块](#vars-and-fieldsets) |

### 模板配置文件

模板配置文件与对应的模板文件**必须同名**，仅扩展名不同。例如模板文件为 `list.html`，其配置文件应命名为 `list.json`。Pinmok
在安装主题时，会取配置文件名去掉扩展名的部分作为模板标识，并据此在运行时定位对应的 HTML 文件（路径为 `themes/{主题目录}/{模板标识}.html`）。

!!! note "命名一致性"

    模板文件（`.html`）与配置文件（`.json`）的文件名（不含扩展名）必须保持一致，否则 Pinmok 无法正确关联两者。

模板配置文件支持的字段如下：

| 字段          | 必填 | 说明                                                           |
|-------------|----|--------------------------------------------------------------|
| `name`      | ✓  | 模板名称，例如"文章列表"、"首页"，显示在后台配置界面                                 |
| `action`    | ✓  | 页面动作标识，与该模板对应的 Django URL `name` 保持一致，Pinmok 通过此字段将配置与具体页面绑定 |
| `order`     |    | 排序权重，整数类型，数字越小排序越靠前，默认值为 `10000`                             |
| `vars`      |    | 模板变量定义，参见[变量与区块](#vars-and-fieldsets)                        |
| `fieldsets` |    | 模板区块变量定义，参见[变量与区块](#vars-and-fieldsets)                      |

> order 决定的是后台主题配置页面中模板列表的展示顺序，数值越小越靠前。如果不设置该字段，系统按数据库记录的写入顺序排列，也就是安装主题时各模板被扫描到的顺序，
> 这个顺序通常不直观，建议有多个模板时显式设置 order。

### 变量与区块 {#vars-and-fieldsets}

配置文件中定义的变量会在主题激活后，由 Pinmok 在渲染对应模板时注入上下文，可以在模板中直接使用。

#### 变量（vars）

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

| 字段        | 必填 | 说明                                                                     |
|-----------|----|------------------------------------------------------------------------|
| `title`   | ✓  | 变量在后台配置页面中显示的标题                                                        |
| `type`    | ✓  | 变量类型，可选值见下表                                                            |
| `default` |    | 默认值。`text` 和 `textarea` 默认为空字符串，`number` 默认为 `0`，`boolean` 默认为 `false` |
| `tip`     |    | 提示文本，显示在后台配置项下方，用于说明变量用途                                               |

| 类型           | 后台控件   | 说明                                     |
|--------------|--------|----------------------------------------|
| `text`       | 单行文本框  |                                        |
| `textarea`   | 多行文本框  |                                        |
| `number`     | 数字输入框  |                                        |
| `boolean`    | 开关按钮   |                                        |
| `datasource` | 数据源选择器 | 需配合 `source` 字段使用，参见[数据源](#datasource) |

#### 区块（fieldsets）

变量也可以按组归类，定义在 `fieldsets` 中。每个区块需设置 `title`，作为后台配置页面中的分组标题。区块内的 `vars` 定义规则与顶层变量完全一致，但在模板中以嵌套方式访问，例如
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

### 数据源 {#datasource}

前面介绍的变量类型（text、number、boolean 等）取值方式都很简单：在后台配置页面里由用户直接填写一个文本、数字或开关状态即可，
Pinmok 内置了固定的渲染方式。但有些变量的取值不是靠用户手动输入产生的，而是需要通过某种业务逻辑获取——例如"侧边栏显示哪个文章分类"，
这个值要从 Category 表中查询得到；也可能来自与数据库无关的其他业务逻辑。这类变量没办法简单地用一个输入框来配置，
必须先执行查询或逻辑运算，再把结果提供给用户选择。

datasource（数据源）就是为此设计的变量类型，"数据源"这个名字也由此而来——它代表的不是某种固定输入方式，而是一个"数据从哪里来"的
逻辑来源。Pinmok 已经内置了部分常用的数据源，可以直接在配置文件中通过 source 字段指定使用；如果内置数据源无法满足需求，
开发者也可以自行编写并注册新的数据源，详见[自定义数据源](#custom_datasource)。

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

| 字段         | 必填 | 说明                 |
|------------|----|--------------------|
| `source`   | ✓  | 数据源 key            |
| `multiple` |    | 是否允许多选，默认为 `false` |

## 完整示例

以下示例展示了一套完整主题的目录结构、配置文件及模板文件的用法。

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
      "title": "公司名称",
      "type": "text",
      "default": "",
      "tip": "显示在站点头部和浏览器标题中"
    }
  },
  "fieldsets": {
    "sidebar": {
      "title": "侧边栏",
      "vars": {
        "category": {
          "title": "分类",
          "type": "datasource",
          "source": "category"
        },
        "title": {
          "title": "侧边栏标题",
          "type": "text",
          "default": "最新文章"
        },
        "count": {
          "title": "显示数量",
          "type": "number",
          "default": 5
        },
        "show_thumbnail": {
          "title": "显示缩略图",
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
  "name": "文章列表",
  "action": "content_article_list",
  "vars": {
    "page_title": {
      "title": "页面标题",
      "type": "text",
      "default": "文章",
      "tip": "显示在列表页顶部"
    },
    "page_size": {
      "title": "每页数量",
      "type": "number",
      "default": 10
    },
    "show_author": {
      "title": "显示作者",
      "type": "boolean",
      "default": true
    }
  }
}
```

**list.html**

```html
<h1>{{ page_title }}</h1>

<p>每页显示：{{ page_size }} 条</p>

{% if show_author %}
<p>显示作者信息</p>
{% endif %}

<aside>
    <h2>{{ sidebar.title }}</h2>
    {% if sidebar.show_thumbnail %}
    {# 渲染缩略图 #}
    {% endif %}
</aside>

<footer>{{ company_name }}</footer>
```

---

## 后端开发

本节内容面向编写视图、模型或其他 Python 代码的开发者，模板开发者无需关心这部分内容。

### 自定义数据源 {#custom_datasource}

当内置数据源（`nav`、`slider`）无法满足需求时——例如变量需要关联开发者自己应用中的模型，或取值依赖某些业务逻辑——就需要自定义数据源。
整个过程分为两步：编写一个继承自 Django `Widget`（或其子类）的类，在其中实现具体的数据获取逻辑；然后通过 `@datasource.register`
装饰器将这个类注册到 Pinmok 的数据源注册表中，之后即可在配置文件里通过 `source` 字段引用它。

后台主题配置页面在渲染时，会直接调用注册的类生成的 Widget 实例完成渲染，因此注册的类必须是合法可实例化的 Widget 子类。

#### 注册位置约定

Pinmok 在启动时会自动扫描所有已安装应用下的 `datasource.py`。因此，**自定义数据源必须定义在应用根目录下的 `datasource.py` 文件中**，
才能被 Pinmok 正确加载。

#### 代码示例

以一个简单的例子说明完整的实现过程。假设业务中有一个 `MyModel` 模型，需要在后台配置页面中提供一个选择框，让用户从 MyModel 的现有数据中选取一项：

```python
# myapp/datasource.py

from django.forms.widgets import Select
from pinmok.padmin.datasource import datasource


@datasource.register('my_source')
class MyDataSource(Select):
    def __init__(self, attrs=None, multiple=False, category=None):
        from .models import MyModel
        queryset = MyModel.objects.filter(category=category) if category else MyModel.objects.all()
        choices = [('', '请选择')] + [(obj.pk, obj.name) for obj in queryset]
        super().__init__(attrs=attrs, choices=choices)
```

这段代码做了以下几件事：

1. `@datasource.register('my_source')` 将这个类注册为 key 为 `my_source` 的数据源，之后配置文件中通过该 key 引用它。
2. `MyDataSource` 继承自 Django 内置的 `Select`，因此它本身就是一个合法的下拉选择框 Widget，无需额外实现渲染逻辑。
3. `__init__` 中执行实际的查询逻辑：根据传入的 `category` 参数过滤 `MyModel`，并组装成 (值, 显示文本) 形式的 choices 列表，
   这正是数据源“动态获取数据”的核心所在。
4. `multiple` 和 `category` 是这个数据源自定义的参数，并非 Django Widget 的标准参数，它们的值来自配置文件，具体传递规则见下文。

注册完成后，即可在配置文件中通过 "source": "my_source" 引用该数据源：

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

!!! tip "保持视觉风格统一"

    后台配置页面整体采用 Tabler 样式。自定义 Widget 如果直接继承 Django 内置的原生类，渲染出来的样式可能与后台其他部分不一致。可以优先使用 Pinmok
    提供的 Widget（完整列表见模型管理[表单控件](model-admin.md#form_widget)一节），也可以根据需要自行编写符合 Tabler 规范的 HTML。

#### 参数传递规则

配置文件中，除 `title`、`type`、`default`、`tip` 之外的所有字段，均会作为关键字参数传入 Widget 的 `__init__`。以上例中的 `multiple` 和 `category`
为例：配置文件写 `"multiple": false`，Pinmok 会自动将其作为 `multiple=False` 传入 `__init__`。

- 如果 `__init__` 声明了 `**kwargs`，所有额外参数都会原样传入。
- 如果没有声明 `**kwargs`，Pinmok 只传入 `__init__` 中明确声明的参数，其余忽略。

### 在视图中使用主题服务

主题的模板路径解析和变量注入并非自动发生，需要开发者在视图中显式调用 `ThemeService` 提供的接口完成。Pinmok 提供了三个面向视图开发的方法：
`get_template_path`、`get_vars_context`、`get_template_choices`。

#### get_template_path

**获取模板路径**

```python
ThemeService.get_template_path(app_label: str, filename: str) -> str | None
```

根据模板文件名返回该主题下对应模板的完整路径，供视图直接传给 render() 使用。这个方法只负责拼接路径字符串，不读取文件、不做任何校验。

参数

- `app_label`：应用名称。Pinmok 根据该值查找此应用当前激活的主题，不同应用的主题相互独立。
- `filename`：模板文件名（不含扩展名），需要与该主题下某个模板文件的实际文件名对应，也对应该模板配套的配置文件名（如果有）。

返回值

如果该应用存在激活主题，返回形如 `themes/{主题目录}/{filename}.html` 的字符串路径；如果该应用当前没有激活的主题，返回 `None`。
调用方需要自行处理 `None` 的情况，通常是回退到应用自带的默认模板。

示例代码

```python
from pinmok.padmin.service.theme import ThemeService


def article_list(request):
    # 获取 content 应用当前激活主题下，list 模板的完整路径
    template_path = ThemeService.get_template_path('content', 'list')

    if template_path is None:
        # 没有激活主题时，回退到应用自带的默认模板，保证页面始终可渲染
        template_path = 'content/list.html'

    return render(request, template_path, {})
```

---

#### get_vars_context

**获取变量上下文**

```python
ThemeService.get_vars_context(app_label: str, filename: str) -> dict
```

返回某个模板文件（由 filename 标识）在当前激活主题下配置的全部变量值，用于注入模板渲染上下文。开发者无需自己读取 JSON 配置文件、
合并全局变量与页面变量，调用这一个方法即可拿到渲染所需的全部数据。

参数

- `app_label`：应用名称，决定查找哪个应用下的激活主题。
- `filename`：模板文件名（不含扩展名），与 `get_template_path` 接收的 `filename` 含义完全一致，用于精确定位某一条模板配置。
  `filename` 在一套主题内是唯一的，因此即便多个模板共享同一个 `action`，也能准确取到对应那一份变量，不会出现歧义。

返回值

返回一个字典，合并了 `theme.json` 中的全局变量与该 `filename` 对应模板配置文件中的页面变量。两者键名冲突时，页面变量覆盖全局变量。
顶层变量以普通键值对形式存在于字典中，可在模板里直接以 `{{ 变量名 }}` 访问；区块变量（`fieldsets`）以嵌套字典形式存在，模板中以
`{{ 区块名.变量名 }}` 访问。如果该应用没有激活主题，或者找不到对应 `filename` 的模板配置，对应部分会被跳过，不会抛出异常，调用方可以安全地直接使用返回值。

示例代码

```python
from pinmok.padmin.service.theme import ThemeService


def article_list(request):
    # 获取 list 这个模板文件对应的全部变量值
    # 返回的字典里既包含顶层变量（如 company_name），也包含区块变量（如 sidebar）
    context = ThemeService.get_vars_context('content', 'list')

    # 业务数据正常加入 context，与主题变量互不冲突
    context['articles'] = Article.objects.all()

    # 模板中可以直接访问 context['sidebar']['title']，即模板里的 {{ sidebar.title }}
    template_path = ThemeService.get_template_path('content', 'list')
    return render(request, template_path or 'content/list.html', context)
```

---

#### get_template_choices

**获取可选模板列表**

```python
ThemeService.get_template_choices(app_label: str, action: str) -> list[tuple[str, str]]
```

返回某个 action 下所有可用的模板文件名列表。这个方法用于实现"同一页面允许使用多套模板"的场景。

参数

- `app_label`：应用名称，决定查找哪个应用下的激活主题。
- `action`：页面动作标识，与模板配置文件中的 action 字段对应。

返回值

返回一个 (`filename`, 名称) 元组列表，可直接用作下拉框的 choices。列表第一项固定为 `(action, '默认')`，代表与 `action`
同名的默认模板；其余项来自配置文件中 `action` 相同但 `filename` 不同的模板配置，元组第二项取自这些配置文件中的 `name` 字段。

示例代码

```python
from pinmok.padmin.service.theme import ThemeService


def template_settings(request):
    # 获取 shop_product_detail 这个 action 下所有可选模板
    choices = ThemeService.get_template_choices('shop', 'shop_product_detail')
    # 返回示例：[('shop_product_detail', '默认'), ('product_promo', '促销商品详情')]

    return render(request, 'shop/admin/template_settings.html', {'choices': choices})
```

---

#### 小结

`get_template_path` 负责定位模板文件，`get_vars_context` 负责取出该模板对应的变量，`get_template_choices` 负责列出某个 `action` 下有哪些模板可选。
三者各自独立，具体如何在业务代码中组合使用，由开发者根据实际场景决定。