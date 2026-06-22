# Utility Functions

Pinmok ships with a set of ready-to-use utility functions covering system information retrieval, app enumeration, storage unit conversion,
and string formatting. If you are already familiar with what each function does, jump straight to the **Quick Start** block above.

??? abstract "Quick Start"

    **Helper functions** (in `pinmok.core.utils.helper`, require a running Django environment)

    | Function | Description | Return value example |
    |----------|-------------|----------------------|
    | `get_system_info()` | Returns OS, Python, Django, database, and project metadata | `{"os": "Windows-10...", "python_version": "3.11.4", "django_version": "4.2.1", ...}` |
    | `get_disk_info()` | Returns disk usage statistics for the partition holding `BASE_DIR` | `{"total": "476.9 GB", "used": "231.5 GB", "free": "245.4 GB", "used_percent": 48.54}` |
    | `get_db_info()` | Returns the current database vendor name and version string | `("Postgresql", "PostgreSQL 15.2 on x86_64...")` |
    | `get_valid_app_labels(exclude_prefixes=None)` | Returns installed app labels, excluding Django built-in apps by default | `{"users", "orders", "products"}` |

    **Tools functions** (in `pinmok.core.utils.tools`, pure Python, no Django dependency)

    | Function | Description | Return value example |
    |----------|-------------|----------------------|
    | `int_to_bytes(num)` | Converts a byte count to a human-readable size string | `int_to_bytes(1500)` → `"1.46 KB"` |
    | `bytes_to_int(size_str)` | Parses a human-readable size string into a byte count | `bytes_to_int("2.5 GB")` → `2684354560` |
    | `to_snake_case(text)` | Converts a string to snake_case | `to_snake_case("Site Info")` → `"site_info"` |
    | `to_compact_case(text)` | Converts a string to compact lowercase, stripping all spaces and punctuation | `to_compact_case("Site Setting")` → `"sitesetting"` |
    | `to_camel_case(text)` | Converts a string to camelCase | `to_camel_case("Site Setting")` → `"siteSetting"` |

    **Import examples:**

    ```python
    from pinmok.core.utils.helper import get_system_info, get_disk_info, get_db_info, get_valid_app_labels
    from pinmok.core.utils.tools import int_to_bytes, bytes_to_int, to_snake_case, to_compact_case, to_camel_case
    ```

---

## Helper Functions

Helper functions encapsulate logic that depends on the Django runtime environment, such as database connections, the app registry, and
settings objects. They must be called after Django initialization is complete and cannot be invoked at module import time.

### System Information

#### `get_system_info()`

```python
from pinmok.core.utils.helper import get_system_info

info = get_system_info()
```

Returns information about the current runtime environment, including the operating system, Python version, Django version,
database vendor and version, and the project name and version. This function is typically used to populate a "System Information"
page in the admin interface, giving system administrators a structured view of the runtime environment.

**Parameters:** none

**Return value:** `dict[str, str]`

| Key               | Description                       | Example                       |
|-------------------|-----------------------------------|-------------------------------|
| `os`              | Operating system platform string  | `"Windows-10-10.0.19045-SP0"` |
| `python_version`  | Python version                    | `"3.11.4"`                    |
| `django_version`  | Django version                    | `"4.2.1"`                     |
| `db_vendor`       | Database vendor name, title-cased | `"Postgresql"`                |
| `db_version`      | Database server version string    | `"PostgreSQL 15.2 on x86_64"` |
| `project_name`    | Project name                      | `"Pinmok"`                    |
| `project_version` | Project version                   | `"1.0.0"`                     |

**Example:**

```python
from pinmok.core.utils.helper import get_system_info

info = get_system_info()
print(info["os"])             # Windows-10-10.0.19045-SP0
print(info["django_version"]) # 4.2.1
print(info["db_vendor"])      # Postgresql
```

---

#### `get_disk_info()`

```python
from pinmok.core.utils.helper import get_disk_info

disk = get_disk_info()
```

Returns disk usage statistics for the partition that contains `settings.BASE_DIR`, including total capacity, used space, free space, and
usage percentage. All size values are formatted through `int_to_bytes()` into human-readable strings. The usage percentage is rounded to two
decimal places.

**Parameters:** none

**Return value:** `dict[str, str | float]`

| Key            | Type    | Description         | Example      |
|----------------|---------|---------------------|--------------|
| `total`        | `str`   | Total disk capacity | `"476.9 GB"` |
| `used`         | `str`   | Used space          | `"231.5 GB"` |
| `free`         | `str`   | Free space          | `"245.4 GB"` |
| `used_percent` | `float` | Usage percentage    | `48.54`      |

**Example:**

```python
from pinmok.core.utils.helper import get_disk_info

disk = get_disk_info()
print(disk["total"])        # 476.9 GB
print(disk["used_percent"]) # 48.54
```

---

#### `get_db_info()`

```python
from pinmok.core.utils.helper import get_db_info

vendor, version = get_db_info()
```

Returns the vendor name and version string of the database currently connected to the Django project.
The version is obtained by executing a database-specific query. If the connection fails or the query raises an error,
both values default to `"Unknown"` and the error is written to the log — no exception is propagated to the caller.

Supported databases:

| Database             | `vendor` value | Returned `vendor` (title-cased) |
|----------------------|----------------|---------------------------------|
| SQLite               | `sqlite`       | `"Sqlite"`                      |
| PostgreSQL           | `postgresql`   | `"Postgresql"`                  |
| MySQL / MariaDB      | `mysql`        | `"Mysql"`                       |
| Oracle               | `oracle`       | `"Oracle"`                      |
| Microsoft SQL Server | `microsoft`    | `"Microsoft"`                   |

MariaDB shares the MySQL backend driver in Django, so `connection.vendor` returns `mysql` for both. `get_db_info()` therefore handles
MariaDB identically to MySQL.

**Parameters:** none

**Return value:** `tuple[str, str]`

- First element: database vendor name, capitalized; `"Unknown"` if unavailable
- Second element: database version string; `"Unknown"` if unavailable

**Example:**

```python
from pinmok.core.utils.helper import get_db_info

vendor, version = get_db_info()
print(vendor)  # Postgresql
print(version) # PostgreSQL 15.2 on x86_64-pc-linux-gnu, compiled by gcc ...
```

---

### App Management

#### `get_valid_app_labels(exclude_prefixes=None)`

```python
from pinmok.core.utils.helper import get_valid_app_labels

app_labels = get_valid_app_labels()
```

Returns the set of labels for all installed apps, excluding Django built-in apps (those whose module path starts with `django.`) by default.
Pinmok uses this function internally when building menus and generating permissions to enumerate the project's business apps. You can also
call it from custom management commands or inspection scripts when you need to iterate over installed apps.

The exclusion logic matches against the full module path (`AppConfig.name`), rather than the app label (`AppConfig.label`). For example,
`django.contrib.auth` is excluded by the default rule, but `myproject.auth` is not.

**Parameters:**

| Parameter          | Type       | Default | Description                          |
|--------------------|------------|---------|--------------------------------------|
| `exclude_prefixes` | `list[str] | None`   | `None` (equivalent to `['django.']`) | List of module path prefixes to exclude |

**Return value:** `set[str]` containing the labels of all non-excluded apps.

**Example:**

```python
from pinmok.core.utils.helper import get_valid_app_labels

# Default: exclude only Django built-in apps
labels = get_valid_app_labels()
print(labels)  # {"users", "orders", "products", "pinmokadmin", ...}

# Custom: also exclude third-party apps such as debug_toolbar
labels = get_valid_app_labels(exclude_prefixes=["django.", "debug_toolbar"])
print(labels)  # {"users", "orders", "products", ...}
```

---

## Tools Functions

Tools functions are pure Python utilities with no dependency on any Django component. They can be used in any Python environment and called
at module import time.

### Storage Unit Conversion

These two functions provide bidirectional conversion between byte counts and human-readable size strings. `int_to_bytes()` and
`bytes_to_int()` are inverse operations of each other.

#### `int_to_bytes(num)`

```python
from pinmok.core.utils.tools import int_to_bytes

readable = int_to_bytes(1500)  # "1.46 KB"
```

Converts a non-negative integer (byte count) to a human-readable size string. The function automatically selects the most appropriate unit (
B, KB, MB, GB, TB, PB, EB, ZB) and strips trailing zeros from the decimal part — for example, `1.50` is displayed as `1.5`, and `1.00` as
`1`.

**Parameters:**

| Parameter | Type  | Description                      |
|-----------|-------|----------------------------------|
| `num`     | `int` | Byte count; must be non-negative |

**Return value:** `str` in the format `"<value> <unit>"`, with a space between value and unit.

**Exceptions:**

- Raises `ValueError` if the input is negative

**Example:**

```python
from pinmok.core.utils.tools import int_to_bytes

print(int_to_bytes(0))           # 0 B
print(int_to_bytes(512))         # 512 B
print(int_to_bytes(1500))        # 1.46 KB
print(int_to_bytes(1024 * 1024)) # 1 MB
print(int_to_bytes(1536 * 1024)) # 1.5 MB
```

---

#### `bytes_to_int(size_str)`

```python
from pinmok.core.utils.tools import bytes_to_int

size = bytes_to_int("2.5 GB")  # 2684354560
```

Parses a human-readable size string into a byte count. The parser is intentionally lenient: units are case-insensitive, spaces between the
value and unit are allowed, and both shorthand (`K`, `M`, `G`) and full forms (`KB`, `MB`, `GB`) are accepted. A string with no unit is
treated as a plain byte count.

**Parameters:**

| Parameter  | Type  | Description                                          |
|------------|-------|------------------------------------------------------|
| `size_str` | `str` | Size string, e.g. `"1KB"`, `"5 M"`, `"2Gb"`, `"100"` |

**Return value:** `int`, the corresponding byte count.

Supported units:

| Unit       | Meaning              |
|------------|----------------------|
| `B`        | Bytes                |
| `K` / `KB` | Kilobytes (1024 B)   |
| `M` / `MB` | Megabytes (1024² B)  |
| `G` / `GB` | Gigabytes (1024³ B)  |
| `T` / `TB` | Terabytes (1024⁴ B)  |
| `P` / `PB` | Petabytes (1024⁵ B)  |
| `E` / `EB` | Exabytes (1024⁶ B)   |
| `Z` / `ZB` | Zettabytes (1024⁷ B) |

**Exceptions:**

- Raises `TypeError` if the input is not a string
- Raises `ValueError` if the string is empty, cannot be parsed, or contains an unrecognized unit

**Example:**

```python
from pinmok.core.utils.tools import bytes_to_int

print(bytes_to_int("1KB"))     # 1024
print(bytes_to_int("1 kb"))    # 1024  (case-insensitive)
print(bytes_to_int("2.5 GB"))  # 2684354560
print(bytes_to_int("500"))     # 500   (no unit, treated as bytes)
```

---

### String Formatting

String formatting functions convert arbitrary strings into normalized identifier formats, with typical use cases including permission codes,
menu slugs, and API field names. The three functions differ in how they handle word boundaries:

| Function            | Input `"User List(Admin)"` | Characteristics                                                |
|---------------------|----------------------------|----------------------------------------------------------------|
| `to_snake_case()`   | `"user_list_admin"`        | Underscore-separated; suitable for permissions and field names |
| `to_compact_case()` | `"userlistadmin"`          | No separator; compact continuous form                          |
| `to_camel_case()`   | `"userListAdmin"`          | camelCase; suitable for JavaScript variables and API fields    |

All three functions preserve characters in the CJK Unified Ideographs block (Unicode `\u4e00`–`\u9fff`), which covers Chinese characters and
Japanese kanji. Characters in this range are kept as-is without any segmentation or splitting. For example, `to_snake_case("用户列表")`
returns `"用户列表"`, and `to_camel_case("用户 list")` returns `"用户list"`. All other non-ASCII characters — including characters from
other writing systems such as Japanese kana, Korean, and Arabic — are treated as separators or removed entirely. If your input may contain
such characters, pre-process it before calling these functions.

#### `to_snake_case(text)`

```python
from pinmok.core.utils.tools import to_snake_case

code = to_snake_case("Site Info")  # "site_info"
```

Converts a string to snake_case. The conversion rules: letters, digits, underscores, and CJK characters are kept; all other characters (
spaces, punctuation, symbols) are replaced with underscores; consecutive underscores are collapsed into one; leading and trailing
underscores are removed; the result is lowercased.

**Parameters:**

| Parameter | Type  | Description             |
|-----------|-------|-------------------------|
| `text`    | `str` | Input string to convert |

**Return value:** `str` in snake_case format.

**Example:**

```python
from pinmok.core.utils.tools import to_snake_case

print(to_snake_case("Site Info"))          # site_info
print(to_snake_case("User@List(Admin)"))   # user_list_admin
print(to_snake_case("---Config---"))       # config
print(to_snake_case("  leading spaces  ")) # leading_spaces
```

---

#### `to_compact_case(text)`

```python
from pinmok.core.utils.tools import to_compact_case

code = to_compact_case("Site Setting")  # "sitesetting"
```

Converts a string to compact lowercase by removing all spaces, punctuation, and symbols, keeping only letters, digits, and CJK characters,
then lowercasing the result. Unlike `to_snake_case()`, no separator is inserted between words — the output is a continuous string.

**Parameters:**

| Parameter | Type  | Description             |
|-----------|-------|-------------------------|
| `text`    | `str` | Input string to convert |

**Return value:** `str` in compact lowercase format.

**Example:**

```python
from pinmok.core.utils.tools import to_compact_case

print(to_compact_case("Site Setting"))     # sitesetting
print(to_compact_case("User List(Admin)")) # userlistadmin
print(to_compact_case("Hello, World!"))    # helloworld
```

---

#### `to_camel_case(text)`

```python
from pinmok.core.utils.tools import to_camel_case

name = to_camel_case("Site Setting")  # "siteSetting"
```

Converts a string to camelCase. The conversion splits the input on any character that is not a letter, digit, or CJK character; lowercases
the first word entirely; capitalizes the first letter of each subsequent word; then joins everything
without separators. Returns an empty string if the input consists entirely of separator characters.

**Parameters:**

| Parameter | Type  | Description             |
|-----------|-------|-------------------------|
| `text`    | `str` | Input string to convert |

**Return value:** `str` in camelCase format, or `""` if the input contains no word characters.

**Example:**

```python
from pinmok.core.utils.tools import to_camel_case

print(to_camel_case("Site Setting"))       # siteSetting
print(to_camel_case("User List(Admin)"))   # userListAdmin
print(to_camel_case("get user by id"))     # getUserById
print(to_camel_case("---"))                # ""  (no word characters)
```