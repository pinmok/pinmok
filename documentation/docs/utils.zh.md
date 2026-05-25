# 工具函数

## 概述

Pinmok 内置的工具函数分为 helper 和 tools 两类，二者区分规则如下：依赖系统模型、服务等框架相关能力的逻辑统一封装在 helper 中，与 Django
系统无关的纯通用工具逻辑则存放于 tools 中。

## 使用方法

### 基本用法

工具函数可直接从 helper.py 或 tools.py 中导入使用：

```python
# 直接导入指定工具函数
from pinmok.core.utils.helper import get_system_info
from pinmok.core.utils.tools import int_to_bytes

# 批量导入整个工具模块
from pinmok.core.utils import helper

# 调用模块内的工具方法
helper.get_system_info()
```

### 工具函数一览

#### get_system_info()

- **功能：** 获取系统基础信息（操作系统、Python 版本、Django 版本、数据库信息、项目名称与版本）
- **返回值：** dict[str, str]
- **用法示例：**
  ```python
  from pinmok.core.utils.helper import get_system_info
  
  info = get_system_info()
  print(info)
  ```
- **返回结构：**
  ```python
  {
      "os": "Windows-10-10.0.19045-SP0",
      "python_version": "3.11.4",
      "django_version": "4.2.1",
      "db_vendor": "Postgresql",
      "db_version": "PostgreSQL 15.2",
      "project_name": "pinmok",
      "project_version": "1.0.0"
  }

  ```

#### get_disk_info()

- **功能：** 获取项目根目录所在磁盘的使用情况（总容量、已用、剩余、使用率）
- **返回值：** dict[str, str | float]
- **用法示例：**
  ```python
  from pinmok.core.utils.helper import get_disk_info
  
  disk = get_disk_info()
  print(disk)
  ```

- **返回结构：**
  ```python
  {
      "total": "476.9G",
      "used": "231.5G",
      "free": "245.4G",
      "used_percent": 48.54
  }

  ```

#### get_db_info()

- **功能：** 获取当前项目连接的数据库类型与版本
- **返回值：** tuple[str, str] → (数据库厂商，版本字符串)
- **用法示例：**
  ```python
  from pinmok.core.utils.helper import get_db_info
  
  vendor, version = get_db_info()
  print(vendor, version)
  ```

- **返回结构：**
  ```text
  PostgreSQL PostgreSQL 15.2 on x86_64
  ```

#### get_valid_app_labels(exclude_prefixes=None)

- **功能：** 获取项目中有效的应用标签（自动排除 Django 自带应用，可自定义排除）
- **参数：**
    - exclude_prefixes: list[str]， 要排除的应用前缀，默认 ['django.']
- **返回值：** set[str]
- **用法示例：**
  ```python
  from pinmok.core.utils.helper import get_valid_app_labels
  
  # 默认排除 django 开头的应用
  apps = get_valid_app_labels()
  
  # 自定义排除
  apps = get_valid_app_labels(exclude_prefixes=['django.', 'debug'])
  ```

- **返回结构：**
  ```text
  {"users", "orders", "products"}
  ```

#### int_to_bytes(num)

- **功能：** 将字节数转换为人类可读的容量格式（自动适配 B/KB/MB/GB/TB 等单位）
- **参数：**
    - num: int， 大于 0 的整数
- **返回值：** str
- **用法示例：**
  ```python
  from pinmok.core.utils.tools import int_to_bytes
  
  print(int_to_bytes(1500))      # 1.46 KB
  print(int_to_bytes(1024*1024)) # 1 MB
  print(int_to_bytes(0))         # 0 B
  ```

#### bytes_to_int(size_str)

- **功能：** 将人类可读的容量字符串转回字节数（支持 KB/MB/G 等宽松格式）
- **参数：**
    - size_str: str， 容量字符串（如 "1KB"、"5 M"、"2Gb"、"100b"）
- **返回值：** int（总字节数）
- **用法示例：**
  ```python
  from pinmok.core.utils.tools import bytes_to_int
  
  print(bytes_to_int("1KB"))     # 1024
  print(bytes_to_int("2.5 GB"))  # 2684354560
  print(bytes_to_int("500"))     # 500
  ```

- **异常**
    - 格式异常抛出 `ValueError`
    - 非法字符输入，抛出 `TypeError`

#### to_snake_case(text)

- **功能：** 将任意字符串转换为下划线命名（snake_case），适合权限、菜单、字段标识
- **参数：**
    - text: str，原始字符串
- **返回值：** str（小写、下划线分隔、无特殊符号）
- **用法示例：**
  ```python
  from pinmok.core.utils.tools import to_snake_case
  
  print(to_snake_case("Site Info"))         # site_info
  print(to_snake_case("User@List(Admin)"))  # user_list_admin
  print(to_snake_case("---Config---"))      # config
  ```

#### to_compact_case(text)

- **功能：** 将字符串转为紧凑小写格式（移除所有空格、符号，只保留字母 / 数字 / 中文）
- **参数：**
    - text: str，原始字符串
- **返回值：** str（小写、无分隔符）
- **用法示例：**
  ```python
  from pinmok.core.utils.tools import to_compact_case
  
  print(to_compact_case("Site Setting"))    # sitesetting
  print(to_compact_case("User List(Admin)"))# userlistadmin
  ```

#### to_camel_case(text)

- **功能：** 将字符串转为小驼峰（camelCase），适合变量名、API 字段
- **参数：**
    - text: str，原始字符串
- **返回值：** str（小驼峰格式）
- **用法示例：**
  ```python
  from pinmok.core.utils.tools import to_camel_case
  
  print(to_camel_case("Site Setting"))       # siteSetting
  print(to_camel_case("User List(Admin)"))   # userListAdmin
  ```
