# 工具函数

Pinmok 内置了一组开箱即用的工具函数，覆盖系统信息查询、应用枚举、容量单位转换和字符串格式化等常见场景。如果你已经熟悉各函数的用途，
可以直接展开**快速开始**查阅。

??? abstract "快速开始"

    **Helper 函数**（位于 `pinmok.core.utils.helper`，依赖 Django 运行环境）

    | 函数 | 说明 | 返回值示例 |
    |------|------|------------|
    | `get_system_info()` | 获取操作系统、Python、Django、数据库及项目的基础信息 | `{"os": "Windows-10...", "python_version": "3.11.4", "django_version": "4.2.1", ...}` |
    | `get_disk_info()` | 获取项目根目录所在磁盘的容量使用情况 | `{"total": "476.9 GB", "used": "231.5 GB", "free": "245.4 GB", "used_percent": 48.54}` |
    | `get_db_info()` | 获取当前数据库的厂商名称与版本字符串 | `("Postgresql", "PostgreSQL 15.2 on x86_64...")` |
    | `get_valid_app_labels(exclude_prefixes=None)` | 获取项目中有效的应用标签集合，自动排除 Django 内置应用 | `{"users", "orders", "products"}` |

    **Tools 函数**（位于 `pinmok.core.utils.tools`，纯 Python，无框架依赖）

    | 函数 | 说明 | 返回值示例 |
    |------|------|------------|
    | `int_to_bytes(num)` | 将字节数转换为人类可读的容量字符串 | `int_to_bytes(1500)` → `"1.46 KB"` |
    | `bytes_to_int(size_str)` | 将容量字符串解析为字节数 | `bytes_to_int("2.5 GB")` → `2684354560` |
    | `to_snake_case(text)` | 将字符串转为 snake_case | `to_snake_case("Site Info")` → `"site_info"` |
    | `to_compact_case(text)` | 将字符串转为紧凑小写格式，移除所有空格与标点 | `to_compact_case("Site Setting")` → `"sitesetting"` |
    | `to_camel_case(text)` | 将字符串转为小驼峰格式（camelCase） | `to_camel_case("Site Setting")` → `"siteSetting"` |

    **导入示例：**

    ```python
    from pinmok.core.utils.helper import get_system_info, get_disk_info, get_db_info, get_valid_app_labels
    from pinmok.core.utils.tools import int_to_bytes, bytes_to_int, to_snake_case, to_compact_case, to_camel_case
    ```

---

## Helper 函数

Helper 函数封装了依赖 Django 运行环境的逻辑，包括数据库连接、应用注册表、配置对象等。这类函数需要在 Django 初始化完成后才能调用，不能在模块导入阶段直接执行。

### 系统信息

#### `get_system_info()` { #get-system-info }

```python
from pinmok.core.utils.helper import get_system_info

info = get_system_info()
```

获取当前运行环境的基础信息快照，包括操作系统、Python 版本、Django 版本、数据库类型与版本，以及当前项目的名称和版本号。该函数常用于管理后台的“系统信息”页面，
将运行环境信息以结构化数据形式呈现给运维人员。

**参数：** 无

**返回值：** `dict[str, str]`

| 键                 | 说明             | 示例值                           |
|-------------------|----------------|-------------------------------|
| `os`              | 操作系统平台字符串      | `"Windows-10-10.0.19045-SP0"` |
| `python_version`  | Python 版本号     | `"3.11.4"`                    |
| `django_version`  | Django 版本号     | `"4.2.1"`                     |
| `db_vendor`       | 数据库厂商名称（首字母大写） | `"Postgresql"`                |
| `db_version`      | 数据库服务器版本字符串    | `"PostgreSQL 15.2 on x86_64"` |
| `project_name`    | 项目名称           | `"Pinmok"`                    |
| `project_version` | 项目版本号          | `"1.0.0"`                     |

**示例：**

```python
from pinmok.core.utils.helper import get_system_info

info = get_system_info()
print(info["os"])             # Windows-10-10.0.19045-SP0
print(info["django_version"]) # 4.2.1
print(info["db_vendor"])      # Postgresql
```

---

#### `get_disk_info()` { #get-disk-info }

```python
from pinmok.core.utils.helper import get_disk_info

disk = get_disk_info()
```

获取项目根目录（`settings.BASE_DIR`）所在磁盘的容量统计，包括总容量、已用空间、剩余空间和使用率百分比。容量数值已通过 `int_to_bytes()`
转换为人类可读格式，使用率精确到小数点后两位。

**参数：** 无

**返回值：** `dict[str, str | float]`

| 键              | 类型      | 说明       | 示例值          |
|----------------|---------|----------|--------------|
| `total`        | `str`   | 磁盘总容量    | `"476.9 GB"` |
| `used`         | `str`   | 已用空间     | `"231.5 GB"` |
| `free`         | `str`   | 剩余空间     | `"245.4 GB"` |
| `used_percent` | `float` | 使用率（百分比） | `48.54`      |

**示例：**

```python
from pinmok.core.utils.helper import get_disk_info

disk = get_disk_info()
print(disk["total"])        # 476.9 GB
print(disk["used_percent"]) # 48.54
```

---

#### `get_db_info()` { #get-db-info }

```python
from pinmok.core.utils.helper import get_db_info

vendor, version = get_db_info()
```

获取当前 Django 项目所连接数据库的厂商名称与版本字符串。函数通过执行各数据库对应的版本查询语句获取版本信息，数据库连接失败或查询出错时均返回
`"Unknown"`，并将错误记录到日志，不会向上抛出异常。

该函数支持以下数据库：

| 数据库                  | `vendor` 值   | 返回的 `vendor`（首字母大写） |
|----------------------|--------------|---------------------|
| SQLite               | `sqlite`     | `"Sqlite"`          |
| PostgreSQL           | `postgresql` | `"Postgresql"`      |
| MySQL / MariaDB      | `mysql`      | `"Mysql"`           |
| Oracle               | `oracle`     | `"Oracle"`          |
| Microsoft SQL Server | `microsoft`  | `"Microsoft"`       |

MariaDB 在 Django 中共用 MySQL 的后端驱动，`connection.vendor` 返回 `mysql`，因此 `get_db_info()` 对 MariaDB 的处理与 MySQL 相同。

**参数：** 无

**返回值：** `tuple[str, str]`

- 第一个元素：数据库厂商名称，首字母大写，连接失败时为 `"Unknown"`
- 第二个元素：数据库版本字符串，连接失败时为 `"Unknown"`

**示例：**

```python
from pinmok.core.utils.helper import get_db_info

vendor, version = get_db_info()
print(vendor)  # Postgresql
print(version) # PostgreSQL 15.2 on x86_64-pc-linux-gnu, compiled by gcc ...
```

---

### 应用管理

#### `get_valid_app_labels(exclude_prefixes=None)` { #get-valid-app-labels }

```python
from pinmok.core.utils.helper import get_valid_app_labels

app_labels = get_valid_app_labels()
```

返回当前项目中所有已安装应用的标签集合，默认自动排除以 `django.` 开头的 Django 内置应用。该函数在 Pinmok
内部在生成菜单和权限时，会使用该函数枚举有效的业务应用，你也可以在自定义管理命令或检查脚本中使用它来遍历项目应用。

排除逻辑基于应用的完整模块路径（`AppConfig.name`）前缀匹配，而非应用标签（`AppConfig.label`）。例如 `django.contrib.auth` 会被默认规则排除，但
`myproject.auth` 不会。

**参数：**

| 参数                 | 类型         | 默认值   | 说明                        |
|--------------------|------------|-------|---------------------------|
| `exclude_prefixes` | `list[str] | None` | `None`（等效于 `['django.']`） | 需要排除的应用模块路径前缀列表 |

**返回值：** `set[str]`，包含所有未被排除的应用标签字符串。

**示例：**

```python
from pinmok.core.utils.helper import get_valid_app_labels

# 默认：仅排除 django. 前缀的内置应用
labels = get_valid_app_labels()
print(labels)  # {"users", "orders", "products", "pinmokadmin", ...}

# 自定义：同时排除 debug_toolbar 等第三方应用
labels = get_valid_app_labels(exclude_prefixes=["django.", "debug_toolbar"])
print(labels)  # {"users", "orders", "products", ...}
```

---

## Tools 函数

Tools 函数是纯 Python 工具，不依赖 Django 的任何组件，可以在任何 Python 环境中独立使用，也可以在模块导入阶段调用。

### 容量转换

容量转换函数提供字节数与人类可读字符串之间的双向转换，`int_to_bytes()` 和 `bytes_to_int()` 互为逆运算。

#### `int_to_bytes(num)` { #int-to-bytes }

```python
from pinmok.core.utils.tools import int_to_bytes

readable = int_to_bytes(1500)  # "1.46 KB"
```

将一个非负整数（字节数）转换为人类可读的容量字符串。函数会自动选择最合适的单位（B、KB、MB、GB、TB、PB、EB、ZB），结果中的小数部分会去除末尾的零（例如
`1.50` 显示为 `1.5`，`1.00` 显示为 `1`）。

**参数：**

| 参数    | 类型    | 说明          |
|-------|-------|-------------|
| `num` | `int` | 字节数，必须为非负整数 |

**返回值：** `str`，格式为 `"<数值> <单位>"`，单位以空格与数值分隔。

**异常：**

- 传入负数时抛出 `ValueError`

**示例：**

```python
from pinmok.core.utils.tools import int_to_bytes

print(int_to_bytes(0))           # 0 B
print(int_to_bytes(512))         # 512 B
print(int_to_bytes(1500))        # 1.46 KB
print(int_to_bytes(1024 * 1024)) # 1 MB
print(int_to_bytes(1536 * 1024)) # 1.5 MB
```

---

#### `bytes_to_int(size_str)` { #bytes-to-int }

```python
from pinmok.core.utils.tools import bytes_to_int

size = bytes_to_int("2.5 GB")  # 2684354560
```

将人类可读的容量字符串解析为字节数。解析规则比较宽松：单位不区分大小写，数值与单位之间允许有空格，支持 `K`、`KB`、`M`、`MB` 等简写与完整写法。不带单位时默认视为字节数。

**参数：**

| 参数         | 类型    | 说明                                      |
|------------|-------|-----------------------------------------|
| `size_str` | `str` | 容量字符串，如 `"1KB"`、`"5 M"`、`"2Gb"`、`"100"` |

**返回值：** `int`，对应的字节数。

支持的单位：

| 单位写法       | 含义           |
|------------|--------------|
| `B`        | 字节           |
| `K` / `KB` | 千字节（1024 B）  |
| `M` / `MB` | 兆字节（1024² B） |
| `G` / `GB` | 吉字节（1024³ B） |
| `T` / `TB` | 太字节（1024⁴ B） |
| `P` / `PB` | 拍字节（1024⁵ B） |
| `E` / `EB` | 艾字节（1024⁶ B） |
| `Z` / `ZB` | 泽字节（1024⁷ B） |

**异常：**

- 传入非字符串时抛出 `TypeError`
- 字符串为空、格式无法解析或包含未知单位时抛出 `ValueError`

**示例：**

```python
from pinmok.core.utils.tools import bytes_to_int

print(bytes_to_int("1KB"))     # 1024
print(bytes_to_int("1 kb"))    # 1024（不区分大小写）
print(bytes_to_int("2.5 GB"))  # 2684354560
print(bytes_to_int("500"))     # 500（无单位视为字节）
```

---

### 字符串格式化

字符串格式化函数用于将任意字符串转换为规范的标识符格式，常见场景包括权限 code、菜单 slug、API 字段名等。三个函数的转换规则有所不同，具体差异见下表：

| 函数                  | 输入 `"User List(Admin)"` | 特点                           |
|---------------------|-------------------------|------------------------------|
| `to_snake_case()`   | `"user_list_admin"`     | 下划线分隔，适合权限和字段名               |
| `to_compact_case()` | `"userlistadmin"`       | 无分隔符紧凑形式                     |
| `to_camel_case()`   | `"userListAdmin"`       | 小驼峰，适合 JavaScript 变量和 API 字段 |

三个函数都保留中文字符。如果输入包含中文，中文部分会作为一个整体保留，不做分词或拆分处理。例如 `to_snake_case("用户列表")` 返回 `"用户列表"`，
`to_camel_case("用户 list")` 返回 `"用户list"`，在标识符包含中文时，需要注意这一行为。只有 CJK 汉字区被保留，其余所有非 ASCII
字符（包括但不限于各语种字母、符号）都会被移除或视为分隔符，需要保留这些字符时，请自行预处理。。

#### `to_snake_case(text)` { #to-snake-case }

```python
from pinmok.core.utils.tools import to_snake_case

code = to_snake_case("Site Info")  # "site_info"
```

将字符串转换为 snake_case 格式。转换规则：保留字母、数字、下划线和中文字符，其余字符（空格、标点、特殊符号等）统一替换为下划线，连续的下划线合并为一个，首尾下划线去除，结果转为小写。

**参数：**

| 参数     | 类型    | 说明        |
|--------|-------|-----------|
| `text` | `str` | 待转换的原始字符串 |

**返回值：** `str`，snake_case 格式的字符串。

**示例：**

```python
from pinmok.core.utils.tools import to_snake_case

print(to_snake_case("Site Info"))          # site_info
print(to_snake_case("User@List(Admin)"))   # user_list_admin
print(to_snake_case("---Config---"))       # config
print(to_snake_case("  leading spaces  ")) # leading_spaces
```

---

#### `to_compact_case(text)` { #to-compact-case }

```python
from pinmok.core.utils.tools import to_compact_case

code = to_compact_case("Site Setting")  # "sitesetting"
```

将字符串转换为紧凑小写格式，移除所有空格、标点和特殊符号，仅保留字母、数字和中文字符，结果转为小写。与 `to_snake_case()`
的区别在于不插入任何分隔符，输出是连续的字符串。

**参数：**

| 参数     | 类型    | 说明        |
|--------|-------|-----------|
| `text` | `str` | 待转换的原始字符串 |

**返回值：** `str`，紧凑小写格式的字符串。

**示例：**

```python
from pinmok.core.utils.tools import to_compact_case

print(to_compact_case("Site Setting"))     # sitesetting
print(to_compact_case("User List(Admin)")) # userlistadmin
print(to_compact_case("Hello, World!"))    # helloworld
```

---

#### `to_camel_case(text)` { #to-camel-case }

```python
from pinmok.core.utils.tools import to_camel_case

name = to_camel_case("Site Setting")  # "siteSetting"
```

将字符串转换为小驼峰格式（camelCase）。转换规则：以非字母、非数字、非中文字符为分隔符拆分单词，第一个单词全部小写，
后续每个单词首字母大写，其余字母保持原样，最后拼接为无分隔符的驼峰字符串。

**参数：**

| 参数     | 类型    | 说明        |
|--------|-------|-----------|
| `text` | `str` | 待转换的原始字符串 |

**返回值：** `str`，小驼峰格式的字符串。输入为空字符串或全部为分隔符时返回空字符串 `""`。

**示例：**

```python
from pinmok.core.utils.tools import to_camel_case

print(to_camel_case("Site Setting"))       # siteSetting
print(to_camel_case("User List(Admin)"))   # userListAdmin
print(to_camel_case("get user by id"))     # getUserById
print(to_camel_case("---"))                # ""（全为分隔符）
```