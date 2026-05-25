# 模型注册

## 概述

Pinmok 深度兼容 Django Admin 原生模型注册体系，使用方式和官方逻辑完全一致。你只需修改导入语句，沿用原本继承 ModelAdmin
的开发写法与注册逻辑，无需改动原有业务代码，就能直接启用统一风格表单组件、菜单排序及各类后台增强能力。

## 注册模型

### 替换导入

在应用的 `admin.py` 中，将 Django 原生后台相关导入，替换为 Pinmok 提供的对应类即可：

```python
# 原生导入
from django.contrib import admin
from django.contrib.admin import ModelAdmin

# 替换为 Pinmok 导入
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin
```

注册方式与 Django Admin 完全一致，使用装饰器或 `register()` 方法均可：

```python
# 装饰器方式
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)


# 或者 register() 方式
padmin.register(Article, ArticleAdmin)
```

### 与原生注册的区别

Pinmok 的 padmin 是一个独立的 Admin Site 实例，与 Django 原生的 admin.site 相互隔离，拥有各自独立的注册表。模型必须注册到 `padmin`，才能出现在
Pinmok 后台中。将模型同时注册到两者会导致冲突，请避免混用。

## PinmokModelAdmin

`PinmokModelAdmin` 是 Pinmok 提供的 `ModelAdmin` 基类，继承自 Django 原生 `ModelAdmin`，完全兼容原生用法，同时自动套用 Tabler 风格表单控件。
并扩展了以下属性：

### 扩展属性

**`menu_sort_order`**

控制该模型在后台菜单中的排序位置，`int` 类型，默认值为 `10000`。数值越小越靠前。当后台存在由 `menus.py`
定义的自定义菜单与模型菜单混合时，两者参与统一排序，请合理设置该值以保证菜单顺序符合预期。

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
```

**`back_url`**

在**编辑页面**显示**返回按钮**，点击跳转到指定的 URL。适用于有明确上下文关系的编辑场景。

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin import PinmokModelAdmin


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    back_url = reverse_lazy('admin:blog_article_changelist')
```

**`image_crop_fields`**

PinmokModelAdmin 内置图片前端裁切上传功能，支持用户在上传图片前完成可视化裁切。该功能是在使用了 Cropper.js 实现，因此配置参数完全沿用
Cropper.js 原生规范。

该属性支持两种用法，支持混合定义。示例如下：

- 简单使用，指定需要裁切的字段

```python
@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    image_crop_fields = ['cover']
```

- 正式用法，指定字段，传入参数

```python
image_crop_fields = [
    'thumbnail',
    {'cover': {'aspectRatio': '4:3'}}
]
```

由于 Pinmok 对上传的图片有两种保存方式：保存到资源库（数据库保存资源表的主键）和普通保存，因此该属性还提供了一个参数 `mode`，取值固定为：

- `path`: （默认值），数据库中保存图片地址字符串。
- `resource`: 保存为 Resource 对象的 PK，适用于统一管理资源的场景。

一个完整的示例如下：

```python
image_crop_fields = [
    'thumbnail',  # 简单写法，使用默认配置
    {
        'cover': {
            'mode': 'resource',  # 保存方式，'path'（默认）或 'resource'
            'aspectRatio': '16:9',  # 裁剪比例
            'targetWidth': '1200',  # 输出最大宽度
            'targetHeight': '675',  # 输出最大高度
            'lockRatio': 'true',  # 锁定比例，用户无法修改
        }
    }
]
```

**`rich_text_fields`**

Pinmok 集成了 HugeRTE 富文本编辑器（TinyMCE 开源 fork，配置参数完全兼容）。只需将目标字段名写入该列表，对应输入框便会自动替换为富文本编辑器。
Pinmok 内置了完善的默认配置，开箱即用。如需自定义，传入的配置项会覆盖对应的默认值：

```python
# 简单写法，使用默认配置
rich_text_fields = ['content']

# 带参数写法，覆盖默认配置
rich_text_fields = [
    'summary',
    {'content': {'height': 600, 'toolbar': 'bold italic | link image'}},
]
```

### 表单控件

`PinmokModelAdmin` 会自动为常见字段类型应用 Pinmok 风格的控件，包括文本输入、日期时间选择、下拉选择、文件上传等，无需手动配置 `widgets`。

## Inline 支持

Pinmok 提供了与原生对应的 Inline 基类：

```python
from pinmok.padmin.options import PinmokStackedInline, PinmokTabularInline


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0
```

用法与 Django 原生 `StackedInline` 和 `TabularInline` 完全一致。

## 完整示例

```python
from django.urls import reverse_lazy
from pinmok import padmin
from pinmok.padmin.options import PinmokModelAdmin, PinmokStackedInline
from .models import Article, ArticleImage


class ArticleImageInline(PinmokStackedInline):
    model = ArticleImage
    extra = 0


@padmin.register(Article)
class ArticleAdmin(PinmokModelAdmin):
    menu_sort_order = 100
    back_url = reverse_lazy('admin:blog_article_changelist')
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title',)
    rich_text_fields = ['content']
    inlines = [ArticleImageInline]
```