# 模型管理

如果你非常熟悉 Django Admin 的模型注册，或是仅需快速查阅用法，可展开**快速开始**，不必阅读完整文档。

??? abstract "快速开始"

    Pinmok 接管了 Django Admin 的模型注册，将 admin.register 替换为 padmin.register，将 ModelAdmin 替换为 PinmokModelAdmin，除了 Pinmok 提供的
    扩展，其余写法与原生完全一致。

    **替换导入**

    ```python
    # 原来
    from django.contrib import admin
    from django.contrib.admin import ModelAdmin

    # 替换为
    from pinmok import padmin
    from pinmok.padmin import PinmokModelAdmin
    ```
    
    > 如果需要开发自己的 ModelAdmin 而不使用 PinmokModelAdmin，可以混入 PinmokModelAdminMixin，它只负责后台界面的样式和控件替换，不引入其他扩展行为。

    **注册模型**

    ```python
    @padmin.register(Article) # 使用 padmin.register
    class ArticleAdmin(PinmokModelAdmin):
        # 原生 ModelAdmin 的所有属性照常使用
        list_display = ('title', 'author', 'created_at')
        search_fields = ('title',)

        # Pinmok 扩展：菜单排序，数值越小越靠前
        menu_sort_order = 100

        # Pinmok 扩展：编辑页返回按钮
        back_url = reverse_lazy('admin:blog_article_changelist')

        # Pinmok 扩展：富文本编辑器，列出需要启用的字段名
        rich_text_fields = ['content']

        # Pinmok 扩展：图片上传（含裁切），列出需要启用的字段名
        # 默认启用裁切弹窗，path 模式将路径写入字段
        image_crop_fields = [
            'thumbnail',
            {'cover': {
                'mode': 'resource',   # resource 模式写入 Resource PK，有去重
                'aspectRatio': '16:9',
                'lockRatio': 'true',
            }}
        ]
    ```

    **Inline**

    ```python
    from pinmok.padmin import PinmokStackedInline, PinmokTabularInline

    class ArticleImageInline(PinmokStackedInline):
        model = ArticleImage
        extra = 0
        # image_crop_fields、rich_text_fields 在 Inline 中同样可用
        image_crop_fields = [{'image': {'aspectRatio': '4:3'}}]
    ```

    **自定义控件**

    ```python
    from pinmok.padmin.widgets import PinmokSwitch

    class ArticleAdmin(PinmokModelAdmin):
        # 只需写出要覆盖的字段类型，其余保留 Pinmok 默认
        formfield_overrides = {
            models.BooleanField: {'widget': PinmokSwitch},
        }
    ```

## 概述

### padmin 与 admin

Django Admin 的核心是 `admin.site`——一个全局的 `AdminSite` 实例，所有模型注册、URL 挂载、权限校验都围绕它运转。Pinmok 延续了这个设计，并将其扩展，提供了自己的
`AdminSite` 实例，并通过 padmin.register 对外暴露注册入口。

`padmin` 的设计目标是让开发者的使用习惯不变。原来写 `admin.register`，现在写 `padmin.register`；原来继承 `ModelAdmin`，现在继承
`PinmokModelAdmin`。API 保持一致，Pinmok 在背后完成主题替换、控件注入和菜单集成。

**兼容原生注册**

Pinmok 在启动时会扫描 `admin.site` 中已注册的全部模型，自动将它们迁移到 `padmin`，并动态混入 `PinmokModelAdminMixin`，使其获得 Pinmok
的样式和控件。这意味着即使保留原生的 `admin.register` 写法，模型也会出现在 Pinmok 后台。

但这种兼容方式有明确的局限：动态生成的类只混入了 `PinmokModelAdminMixin`，无法获得 `PinmokModelAdmin` 独有的能力，例如 `back_url`。对于新项目，建议直接使用
`padmin.register` + `PinmokModelAdmin`，以完整使用 Pinmok 的所有特性。

### PinmokModelAdmin 的定位

`PinmokModelAdmin` 不是在 `ModelAdmin` 基础上打补丁，而是一次完整的替换。它接管了 Django Admin 的表单渲染、控件注入和模板层，将整个后台界面统一为
Tabler 风格（全面兼容 Bootstrap 5）。

这个替换对开发者几乎是透明的。原有的 `list_display`、`search_fields`、`fieldsets`、`inlines` 等配置全部照常工作，Pinmok 在渲染层完成替换，不干预业务逻辑。

#### 模板层

Pinmok 覆盖了 Django Admin 的大量内置模板，包括列表页、编辑页、登录页、弹窗等，统一替换为 Tabler 主题。这一替换自动生效，无需任何配置。

Pinmok 同样提供了 `base.html` 和 `base_site.html` 两个基础模板，与 Django Admin 的同名文件职责一致：

- `base.html`：纯基础骨架，负责加载必要的静态资源（CSS、JS）
- `base_site.html`：继承自 `base.html`，带有完整的后台布局，包括菜单、面包屑、页头等

开发自定义后台页面时，通常继承 `base_site.html`，以获得完整的后台外观和导航结构；但是，如果需要空白页面，或特有的布局，则可以继承 `base.html`。

#### 覆盖模板

如果需要替换 Pinmok 的模板，在任意应用的 `templates/admin/` 目录下放置同名文件即可。Django 的模板加载器会按 `INSTALLED_APPS`
的顺序查找模板，找到第一个匹配的文件就停止，因此该应用必须在 `INSTALLED_APPS` 中排在 `pinmok.padmin` 之前，否则覆盖不会生效。

```python
INSTALLED_APPS = [
    'your_app',  # 排在 pinmok.padmin 之前，模板才能生效
    'pinmok.padmin',
    'django.contrib.admin',
    ...
]
```

同理，如果需要覆盖 Django 原生模板，应用也需要排在 `django.contrib.admin` 之前。

#### 继承结构

Pinmok 模型管理相关的类均基于 PinmokModelAdminMixin 构建：

```
PinmokModelAdminMixin（继承自 BaseModelAdmin）
    ├── PinmokModelAdmin（组合 ModelAdmin）      ← 普通模型注册，本章重点
    └── PinmokInlineMixin
            ├── PinmokStackedInline（组合 StackedInline）
            └── PinmokTabularInline（组合 TabularInline）
```

`PinmokModelAdminMixin` 承载所有公共能力：统一风格控件、`image_crop_fields`、`rich_text_fields`、`menu_sort_order`。`PinmokModelAdmin`
在此基础上扩展了编辑页相关能力（`back_url` 等）。Inline 基类通过 `PinmokInlineMixin` 共享同一套能力，不经过 `ModelAdmin`，与 Django 原生
`InlineModelAdmin` 直接继承 `BaseModelAdmin` 的结构保持一致。

## 注册模型

### 替换导入

在应用的 `admin.py` 中，将 Django 原生后台相关导入替换为 Pinmok 提供的对应类：

```python
# 原生导入
from django.contrib import admin
from django.contrib.admin import ModelAdmin

# 替换为 Pinmok 导入
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin
```

`padmin` 是 Pinmok 的后台站点命名空间，其中的 `register` 与 Django 原生的 `admin.register` 用法完全一致，直接替换即可，无需修改注册逻辑。

### 注册方式

装饰器和 `register()` 方法均可，与原生保持一致：

```python
# 装饰器方式（推荐）
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)


# register() 方式
padmin.register(Article, ArticleAdmin)
```

### 兼容原生注册

Pinmok 会在 `AppConfig.ready()` 阶段自动扫描 `admin.site` 中的已注册模型，统一将其动态迁移至 `padmin`。迁移过程中，系统会为每个模型生成全新的
Admin 类、混入 `PinmokModelAdminMixin`，同时注销 `admin.site` 中原有的注册记录。

!!! warning "注意"

    兼容机制适用于标准的模型注册场景——只包含列表、搜索、排序等业务配置，未重写 formfield_for_foreignkey、formfield_for_manytomany 等字段渲染方法，也未自定义
    widget。在这种场景下，混入后换肤完全生效，业务逻辑不受影响。
    
    如果原有代码中已有界面定制，混入后可能与 Pinmok 的控件注入逻辑产生冲突，导致部分样式失效或自定义 widget 被覆盖。此类情况建议主动迁移，将基类替换为
    PinmokModelAdmin，以获得可预期的行为。

基于该机制，采用原生写法的模型仍可在 Pinmok 后台正常加载，并自动适配 Tabler 风格及 Pinmok 专属控件。需要注意：动态生成的类无法拥有
`PinmokModelAdmin` 的全部能力，`back_url` 等扩展属性与功能均不可用，且后续所有版本的功能扩展也都将围绕 `PinmokModelAdmin` 进行。

因此，若非有明确的特殊需求，建议将代码中的 `admin.register` 替换为 `padmin.register`，并将 Admin 基类改为 `PinmokModelAdmin`，从而解锁 Pinmok
的全部功能。

## PinmokModelAdmin

`PinmokModelAdmin` 继承自 `PinmokModelAdminMixin` 和 Django 原生 `ModelAdmin`，是 Pinmok 模型管理的核心类。它完全兼容原生 `ModelAdmin`
的所有用法，同时扩展了以下属性。

### menu_sort_order

`menu_sort_order` 控制该模型在后台菜单中的排序位置，类型为 `int`，默认值为 `10000`。数值越小，菜单项越靠前。

Django Admin 本身没有提供细粒度的菜单排序机制，模型的显示顺序由注册顺序和 app 顺序决定，开发者难以控制。`menu_sort_order`
解决了这个问题，允许为每个模型单独指定排序权重。

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
```

`menus.py` 中定义的自定义菜单与模型菜单参与统一排序。如果后台同时存在自定义菜单项和模型菜单项，建议统一规划各项的排序值，确保菜单顺序符合预期。
菜单系统的详细说明参见 [菜单系统](menus.md) 章节。

### back_url

`back_url` 在编辑页面（change form）显示一个返回按钮，点击后跳转至指定 URL。

Django Admin 的编辑页面默认没有返回按钮，用户只能通过浏览器后退或手动导航返回列表页。`back_url`
为有明确上下文关系的编辑场景提供了便捷的返回路径，例如从某个筛选后的列表进入编辑，完成后希望回到原列表，而不是默认的 changelist 根路径。

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    back_url = reverse_lazy('admin:blog_article_changelist')
```

`back_url` 使用 `reverse_lazy` 而非 `reverse`，是因为类属性在模块加载时就会被求值，而 URL 配置可能尚未完成初始化。

### image_crop_fields

Django Admin 对 `ImageField` 的默认处理是渲染一个普通的文件输入框，上传后将路径写入字段，没有预览、没有裁切、没有去重。`image_crop_fields`
替换了这一行为，为指定字段启用 `PinmokImageFileInput` widget，提供带预览的图片上传界面，并根据配置决定上传模式和裁切行为。

`image_crop_fields` 是 Pinmok 图片上传的核心入口。它不仅提供裁切功能，更重要的是为图片字段接入了 Pinmok 的上传体系，包括去重、压缩和资源管理能力。

#### 两种上传模式

Pinmok 通过 `mode` 参数提供两种上传模式，对应不同的字段类型和使用场景：

- path 模式

`path` 模式（默认）适用于 `ImageField` 或 `CharField`。上传完成后，图片路径字符串直接写入字段。上传过程不经过资源表，也不做去重处理。
该模式会返回上传文件的相对路径，页面渲染时需自行拼接资源地址，可搭配 `media_url` 模板标签或字段自带的 `.url` 属性使用。该模式适合对图片复用需求不高的简单场景。

```python
# path 模式对应的 Model 字段
class Article(models.Model):
    cover = models.ImageField(upload_to='covers/')
    # 或者
    thumbnail = models.CharField(max_length=255)
```

!!! tip "path 模式与 ImageField"

    `path` 模式下，如果字段是 `ImageField`，Pinmok 会自动将表单字段替换为 `PinmokImagePathField`，允许字符串路径通过 Django 的表单验证。这一处理对开发者透明，无需额外配置。

- resource 模式

为集中管理上传资源，系统内置 `Resource` 数据表。若图片存在多处复用、需要自动去重，可通过外键关联该表，`resource` 模式适用于
`ForeignKey(Resource)`。上传完成后，`Resource` 记录的主键写入字段。上传通过 `UploadService` 处理，基于 SHA-256
哈希自动去重——同一张图片无论上传多少次，只保存一份文件，返回已有记录的主键。同时，上传过程会对图片进行压缩：PNG 保留透明通道并优化，其余格式转换为
JPEG（quality=85）。`resource` 模式适合图片需要多处复用、或需要统一管理后台资源的场景。

```python
# resource 模式对应的 Model 字段
from pinmok.padmin.models import Resource


class Article(models.Model):
    cover = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True, blank=True)
```

!!! note "注意"

    如需在代码中指定上传模式，推荐使用内置枚举 ImageWidgetMode，包含 PATH、RESOURCE 两个常量，分别对应 path、resource 模式，避免手写字符串产生拼写错误。例：
    ```python
    from pinmok.padmin.enums import ImageWidgetMode
    ```
    使用时为 `ImageWidgetMode.PATH` 和 `ImageWidgetMode.RESOURCE`

#### 裁切行为

`image_crop_fields` 默认开启裁切弹窗（`crop: 'true'`）。用户选择图片后，会进入裁切界面，支持自由裁切、固定比例裁切、旋转、翻转等操作，确认后图片暂存于内存，表单提交时统一上传。

如果只需要上传功能而不需要裁切，将 `crop` 设为 `'false'`，用户选择图片后直接进入上传流程，不打开裁切弹窗。无论 `crop` 如何设置，`resource`
模式的去重和压缩逻辑始终生效。

SVG 文件无论 `crop` 如何设置，始终跳过裁切直接上传。SVG 是矢量格式，基于像素的裁切操作对其没有意义。

#### 用法

该属性为列表类型，支持传入多个字段。仅填写字段名字符串时，表示启用默认配置（开启裁切，`path` 模式）：

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    image_crop_fields = ['cover']
```

需要自定义裁切参数时，可传入单键字典，字段名字符串与配置字典支持混合书写：

```python
image_crop_fields = [
    'thumbnail',  # thumbnail 字段，简单写法，使用默认配置
    {'cover': {  # cover 字段，自定义参数写法
        'mode': 'resource',  # 启用资源模式
        'aspectRatio': '16:9',  # 固定裁切比例
        'lockRatio': 'true',  # 锁定比例，用户不可在弹窗中修改
        'targetWidth': 1200,  # 输出最大宽度（像素）
    }}
]
```

`mode` 同样可以使用枚举常量，避免魔法字符串：

```python
from pinmok.padmin.enums import ImageWidgetMode

image_crop_fields = [
    {'cover': {'mode': ImageWidgetMode.RESOURCE}}
]
```

#### 参数说明

| 参数             | 默认值       | 说明                                                                                                         |
|----------------|-----------|------------------------------------------------------------------------------------------------------------|
| `mode`         | `'path'`  | 上传模式。`'path'` 将路径写入 `ImageField` 或 `CharField`；`'resource'` 将 Resource PK 写入 `ForeignKey(Resource)`，有去重和压缩 |
| `crop`         | `'true'`  | 是否启用裁切弹窗。`'true'` 或 `'false'`，SVG 文件始终跳过裁切                                                                 |
| `aspectRatio`  | `''`      | 裁切比例。支持 `'16:9'`、`'16/9'`、`1.5` 等格式，留空为自由裁切                                                                |
| `targetWidth`  | `1920`    | 输出图片的最大宽度（像素）                                                                                              |
| `targetHeight` | 无         | 输出图片的最大高度（像素）                                                                                              |
| `lockRatio`    | `'false'` | 是否锁定裁切比例。锁定后用户无法在弹窗中修改比例，`'true'` 或 `'false'`                                                              |

裁切功能基于 Cropper.js 实现，上述参数是 Pinmok 模板中支持的配置项。如需使用 Cropper.js
的其他原生参数，请参考 [Cropper.js 文档](https://github.com/fengyuanchen/cropperjs)。

### rich_text_fields

`rich_text_fields` 将指定字段的输入框替换为 HugeRTE 富文本编辑器。

Django Admin 对 `TextField` 的默认处理是渲染一个多行文本框，对于需要富文本编辑能力的内容字段（文章正文、产品描述等），开发者通常需要自行集成第三方编辑器，配置过程繁琐。
`rich_text_fields` 将这一过程简化为一行配置。

HugeRTE 是 TinyMCE 的开源 fork，配置参数完全兼容 TinyMCE<!-- TODO: 补充 TinyMCE 文档链接 -->。Pinmok 内置了一套默认配置，
包含常用插件（列表、链接、图片、表格、代码、全屏、预览等）和工具栏，开箱即用。编辑器语言跟随 Django 的 `LANGUAGE_CODE` 自动切换，
无需配置，原生支持多语言。

简单写法，使用内置默认配置：

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    rich_text_fields = ['content']
```

需要自定义时，使用单键字典传入配置项。用户配置会与内置默认配置合并，只有显式指定的键会被覆盖，其余保留默认值：

```python
rich_text_fields = [
    'summary',
    {'content': {
        'min_height': 600,
        'menubar': True,
    }},
]
```

传入的配置项直接序列化为 JSON 传给 HugeRTE 初始化，所有 HugeRTE 原生支持的配置项均可使用。

## 表单控件 {#form_widget}

`PinmokModelAdmin` 会为常见字段类型自动应用 Pinmok 风格控件，无需手动配置 `widgets`。这些控件统一基于 Tabler 样式体系，在视觉上与后台主题保持一致。

自动替换的字段类型如下：

| 字段类型                                              | 替换控件                               |
|---------------------------------------------------|------------------------------------|
| `CharField`                                       | `PinmokTextInput`                  |
| `TextField` / `JSONField`                         | `PinmokTextarea`                   |
| `EmailField`                                      | `PinmokEmailInput`                 |
| `URLField`                                        | `PinmokURLInput`                   |
| `IntegerField` / `BigIntegerField` / `FloatField` | `PinmokNumberInput`                |
| `DecimalField`                                    | `PinmokDecimalInput`（带 `0.00` 占位符） |
| `UUIDField`                                       | `PinmokUUIDInput`                  |
| `GenericIPAddressField`                           | `PinmokGenericIPAddress`（带输入掩码）    |
| `BooleanField`                                    | `PinmokCheckbox`                   |
| `DateField`                                       | `PinmokDateInput`                  |
| `TimeField`                                       | `PinmokTimeInput`                  |
| `DateTimeField`                                   | `PinmokDateTimeInput`              |
| `ImageField` / `FileField`                        | `PinmokFileInput`                  |
| 有 `choices` 的字段                                   | `PinmokSelect`                     |
| `ForeignKey`（启用 autocomplete）                     | `PinmokAutocompleteSelect`         |
| `ManyToManyField`（启用 autocomplete）                | `PinmokAutocompleteSelectMultiple` |
| `ForeignKey(Resource)`                            | `ResourceWidget`（自动，无需配置）          |

`ForeignKey(Resource)` 字段会自动渲染为资源选择器（`ResourceWidget`），支持从资源库选择已有文件或触发上传弹窗，无需任何额外配置。

指向自身的递归 `ForeignKey`（常见于树形结构模型）会自动禁用关联对象的增删改查按钮，避免在编辑页面触发递归操作。

### 自定义控件

如果需要对某个字段使用不同的控件，通过 `formfield_overrides` 覆盖即可。Pinmok 对合并逻辑做了处理：用户自定义的配置与 Pinmok
默认配置合并，只有显式指定的字段类型会被覆盖，其余字段类型仍保留 Pinmok 的默认控件，不会退回 Django 原始行为。

```python
from django.db import models
from pinmok.padmin.widgets import PinmokSwitch


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    formfield_overrides = {
        models.BooleanField: {'widget': PinmokSwitch},
    }
```

Pinmok 还提供了一些不在自动替换范围内、可以手动选用的控件：

| 控件                             | 适用场景                             |
|--------------------------------|----------------------------------|
| `PinmokSwitch`                 | 开关样式的布尔字段，视觉上区别于默认的复选框           |
| `PinmokSelectTags`             | 基于 Tom Select 的多选标签输入，适合标签、分类等场景 |
| `PinmokCheckboxSelectMultiple` | 复选框组，适合选项较少的多选场景                 |
| `PinmokRadioSelect`            | 单选按钮组，配合 `radio_fields` 使用       |
| `PinmokDatalistInput`          | 带候选提示的文本输入，需调用方提供候选数据            |

引入路径：

```python
from pinmok.padmin.widgets import (
    PinmokSwitch,
    PinmokSelectTags,
    PinmokCheckboxSelectMultiple,
    PinmokRadioSelect,
    PinmokDatalistInput,
)
```

## Inline 支持

Pinmok 提供了与原生对应的 Inline 基类：

```python
from pinmok.padmin import PinmokStackedInline, PinmokTabularInline


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
```

用法与 Django 原生 `StackedInline` 和 `TabularInline` 完全一致。两者通过 `PinmokInlineMixin` 共享 `PinmokModelAdminMixin` 的全部能力，
`image_crop_fields` 和 `rich_text_fields` 在 Inline 中的用法与 `PinmokModelAdmin` 相同。

!!! tip "提示"

    `PinmokInlineMixin` 继承自 `PinmokModelAdminMixin`，不经过 `ModelAdmin`，与 Django 原生 `InlineModelAdmin` 直接继承 `BaseModelAdmin`
    的结构保持一致。请不要在 Inline 中使用 `PinmokModelAdmin` 作为基类。

## 完整示例

```python
from django.db import models
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin, PinmokStackedInline
from pinmok.padmin.enums import ImageWidgetMode
from pinmok.padmin.models import Resource
from pinmok.padmin.widgets import PinmokSwitch

from .models import Article, ArticleImage


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
    image_crop_fields = [
        {'image': {'aspectRatio': '4:3'}}
    ]


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
    back_url = reverse_lazy('admin:blog_article_changelist')

    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)

    rich_text_fields = ['content']

    image_crop_fields = [
        'thumbnail',
        {'cover': {
            'mode': ImageWidgetMode.RESOURCE,
            'aspectRatio': '16:9',
            'targetWidth': 1200,
            'lockRatio': 'true',
        }}
    ]

    formfield_overrides = {
        models.BooleanField: {'widget': PinmokSwitch},
    }

    inlines = [ArticleImageInline]
```