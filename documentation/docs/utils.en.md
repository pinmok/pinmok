# Utility Functions

## Overview

Pinmok provides two categories of built-in utility functions: `helper` and `tools`. The distinction is as follows: logic that depends on
framework-level capabilities such as system models or services is encapsulated in `helper`; pure general-purpose logic with no dependency on
Django is placed in `tools`.

## Usage

### Basic Usage

Utility functions can be imported directly from `helper.py` or `tools.py`:

```python
# Import a specific utility function
from pinmok.core.utils.helper import get_system_info
from pinmok.core.utils.tools import int_to_bytes

# Import the entire utility module
from pinmok.core.utils import helper

# Call a function from the module
helper.get_system_info()
```

### Function Reference

#### get_system_info()

- **Description:** Returns basic system information, including OS, Python version, Django version, database info, and project name and
  version.
- **Returns:** `dict[str, str]`
- **Example:**
  ```python
  from pinmok.core.utils.helper import get_system_info
  
  info = get_system_info()
  print(info)
  ```
- **Return structure:**
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

- **Description:** Returns disk usage for the volume containing the project root directory, including total size, used space, free space,
  and usage percentage.
- **Returns:** `dict[str, str | float]`
- **Example:**
  ```python
  from pinmok.core.utils.helper import get_disk_info
  
  disk = get_disk_info()
  print(disk)
  ```
- **Return structure:**
  ```python
  {
      "total": "476.9G",
      "used": "231.5G",
      "free": "245.4G",
      "used_percent": 48.54
  }
  ```

#### get_db_info()

- **Description:** Returns the type and version of the database the project is currently connected to.
- **Returns:** `tuple[str, str]` → (vendor, version string)
- **Example:**
  ```python
  from pinmok.core.utils.helper import get_db_info
  
  vendor, version = get_db_info()
  print(vendor, version)
  ```
- **Return structure:**
  ```text
  PostgreSQL PostgreSQL 15.2 on x86_64
  ```

#### get_valid_app_labels(exclude_prefixes=None)

- **Description:** Returns the app labels of all user-defined apps in the project, automatically excluding Django built-in apps. Additional
  prefixes can be excluded via the parameter.
- **Parameters:**
    - `exclude_prefixes`: `list[str]`, prefixes to exclude; defaults to `['django.']`
- **Returns:** `set[str]`
- **Example:**
  ```python
  from pinmok.core.utils.helper import get_valid_app_labels
  
  # Exclude Django built-in apps (default)
  apps = get_valid_app_labels()
  
  # Custom exclusions
  apps = get_valid_app_labels(exclude_prefixes=['django.', 'debug'])
  ```
- **Return structure:**
  ```text
  {"users", "orders", "products"}
  ```

#### int_to_bytes(num)

- **Description:** Converts a byte count to a human-readable size string, automatically selecting the appropriate unit (B / KB / MB / GB /
  TB, etc.).
- **Parameters:**
    - `num`: `int`, a non-negative integer
- **Returns:** `str`
- **Example:**
  ```python
  from pinmok.core.utils.tools import int_to_bytes
  
  print(int_to_bytes(1500))       # 1.46 KB
  print(int_to_bytes(1024*1024))  # 1 MB
  print(int_to_bytes(0))          # 0 B
  ```

#### bytes_to_int(size_str)

- **Description:** Converts a human-readable size string back to a byte count. Accepts loose formats such as KB / MB / G, etc.
- **Parameters:**
    - `size_str`: `str`, a size string (e.g. `"1KB"`, `"5 M"`, `"2Gb"`, `"100b"`)
- **Returns:** `int` (total bytes)
- **Example:**
  ```python
  from pinmok.core.utils.tools import bytes_to_int
  
  print(bytes_to_int("1KB"))      # 1024
  print(bytes_to_int("2.5 GB"))   # 2684354560
  print(bytes_to_int("500"))      # 500
  ```
- **Exceptions:**
    - Raises `ValueError` for malformed input
    - Raises `TypeError` for invalid characters

#### to_snake_case(text)

- **Description:** Converts any string to snake_case. Useful for permission codenames, menu identifiers, and field keys.
- **Parameters:**
    - `text`: `str`, the input string
- **Returns:** `str` (lowercase, underscore-separated, no special characters)
- **Example:**
  ```python
  from pinmok.core.utils.tools import to_snake_case
  
  print(to_snake_case("Site Info"))          # site_info
  print(to_snake_case("User@List(Admin)"))   # user_list_admin
  print(to_snake_case("---Config---"))       # config
  ```

#### to_compact_case(text)

- **Description:** Converts a string to a compact lowercase format by removing all spaces and symbols, retaining only letters, digits, and
  Chinese characters.
- **Parameters:**
    - `text`: `str`, the input string
- **Returns:** `str` (lowercase, no separators)
- **Example:**
  ```python
  from pinmok.core.utils.tools import to_compact_case
  
  print(to_compact_case("Site Setting"))     # sitesetting
  print(to_compact_case("User List(Admin)")) # userlistadmin
  ```

#### to_camel_case(text)

- **Description:** Converts a string to lowerCamelCase. Useful for variable names and API field keys.
- **Parameters:**
    - `text`: `str`, the input string
- **Returns:** `str` (lowerCamelCase)
- **Example:**
  ```python
  from pinmok.core.utils.tools import to_camel_case
  
  print(to_camel_case("Site Setting"))       # siteSetting
  print(to_camel_case("User List(Admin)"))   # userListAdmin
  ```