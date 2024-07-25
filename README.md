# **SmartIni** #

[![Python versions](https://img.shields.io/pypi/pyversions/smartini.svg)](https://pypi.org/project/smartini/) [![PyPI version](https://img.shields.io/pypi/v/smartini.svg)](https://pypi.org/project/smartini/) [![License](https://img.shields.io/github/license/t1h0/smartini)](https://raw.githubusercontent.com/t1h0/smartini/master/LICENSE)

SmartIni is a simple, yet fully-featured python library to work with INI configuration files. It aims at providing easy access to configurations saved in the INI file structure while eliminating the drawbacks of existing approaches like configparser.

### Contents

- [**SmartIni**](#smartini)
    - [Contents](#contents)
- [Getting started](#getting-started)
  - [Installation](#installation)
  - [Setting up a configuration file](#setting-up-a-configuration-file)
  - [Setting up the configuration Schema](#setting-up-the-configuration-schema)
  - [Using the configurations in your code](#using-the-configurations-in-your-code)
- [Advanced Usage](#advanced-usage)
  - [Multiple configurations using *slots*](#multiple-configurations-using-slots)
    - [Introduction](#introduction)
    - [Basic concept](#basic-concept)
      - [Slot keys](#slot-keys)
    - [Accessing and setting slots](#accessing-and-setting-slots)
      - [Automatically](#automatically)
      - [Manually](#manually)
    - [Introduction solution](#introduction-solution)
  - [Type hinting and type conversion](#type-hinting-and-type-conversion)
    - [Introduction](#introduction-1)
    - [Basic concept](#basic-concept-1)
    - [Built-in `TypeConverters`](#built-in-typeconverters)
    - [Creating your own `TypeConverter`](#creating-your-own-typeconverter)
    - [Assigning `TypeConverters` via type hinting](#assigning-typeconverters-via-type-hinting)
    - [Introduction solution](#introduction-solution-1)
  - [Custom markers](#custom-markers)
  - [Multiline options](#multiline-options)
  - [Undefined configurations](#undefined-configurations)
- [Documentation](#documentation)
  - [smartini.**Comment**](#smartinicomment)
    - [smartini.Comment.**content**](#smartinicommentcontent)
    - [smartini.Comment.**to\_string**](#smartinicommentto_string)
  - [smartini.**Option**](#smartinioption)
    - [smartini.Option.**to\_string**](#smartinioptionto_string)
  - [smartini.**Parameters**](#smartiniparameters)
  - [smartini.**Schema**](#smartinischema)
    - [smartini.Schema.**export**](#smartinischemaexport)
    - [smartini.Schema.**get\_section**](#smartinischemaget_section)
    - [smartini.Schema.**get\_sections**](#smartinischemaget_sections)
    - [smartini.Schema.**read\_ini**](#smartinischemaread_ini)
    - [smartini.Schema.**with\_slot**](#smartinischemawith_slot)
  - [smartini.**Section**](#smartinisection)
    - [smartini.Section.**add\_entity**](#smartinisectionadd_entity)
    - [smartini.Section.**get\_comments\_by\_content**](#smartinisectionget_comments_by_content)
    - [smartini.Section.**get\_option**](#smartinisectionget_option)
    - [smartini.Section.**get\_options**](#smartinisectionget_options)
    - [smartini.Section.**set\_option**](#smartinisectionset_option)
  - [smartini.**SectionName**](#smartinisectionname)
  - [smartini.**SlotAccess**](#smartinislotaccess)
  - [smartini.**SlotDeciderMethods**](#smartinislotdecidermethods)
  - [smartini.**TYPE**](#smartinitype)
  - [smartini.**type\_converters**](#smartinitype_converters)
    - [smartini.type\_converters.**converters**](#smartinitype_convertersconverters)
      - [smartini.type\_converters.converters.**bool\_converter**](#smartinitype_convertersconvertersbool_converter)
      - [smartini.type\_converters.converters.**ConvertibleTypes**](#smartinitype_convertersconvertersconvertibletypes)
      - [smartini.type\_converters.converters.**DEFAULT\_BOOL\_CONVERTER**](#smartinitype_convertersconvertersdefault_bool_converter)
      - [smartini.type\_converters.converters.**DEFAULT\_GUESS\_CONVERTER**](#smartinitype_convertersconvertersdefault_guess_converter)
      - [smartini.type\_converters.converters.**DEFAULT\_LIST\_CONVERTER**](#smartinitype_convertersconvertersdefault_list_converter)
      - [smartini.type\_converters.converters.**DEFAULT\_NUMERIC\_CONVERTER**](#smartinitype_convertersconvertersdefault_numeric_converter)
      - [smartini.type\_converters.converters.**guess\_converter**](#smartinitype_convertersconvertersguess_converter)
      - [smartini.type\_converters.converters.**list\_converter**](#smartinitype_convertersconverterslist_converter)
      - [smartini.type\_converters.converters.**new\_converter**](#smartinitype_convertersconvertersnew_converter)
      - [smartini.type\_converters.converters.**numeric\_converter**](#smartinitype_convertersconvertersnumeric_converter)
      - [smartini.type\_converters.converters.**TypeConverter**](#smartinitype_convertersconverterstypeconverter)
      - [smartini.type\_converters.converters.**WrongType**](#smartinitype_convertersconverterswrongtype)
    - [smartini.type\_converters.**type\_hints**](#smartinitype_converterstype_hints)
      - [smartini.type\_converters.type\_hints.**BOOL**](#smartinitype_converterstype_hintsbool)
      - [smartini.type\_converters.type\_hints.**GUESS**](#smartinitype_converterstype_hintsguess)
      - [smartini.type\_converters.type\_hints.**LIST**](#smartinitype_converterstype_hintslist)
      - [smartini.type\_converters.type\_hints.**NUMERIC**](#smartinitype_converterstype_hintsnumeric)
      - [smartini.type\_converters.type\_hints.**STR**](#smartinitype_converterstype_hintsstr)
  - [smartini.**UndefinedOption**](#smartiniundefinedoption)
  - [smartini.**VALID\_MARKERS**](#smartinivalid_markers)
- [Why still ini?](#why-still-ini)
- [Contributing](#contributing)
- [License](#license)


# Getting started

## Installation

SmartIni runs on python 3.12+.

## Setting up a configuration file

Say you want to distribute a news service that crawls a specific news website periodically and sends a summary of the crawled news per mail. This is what your `config.ini` file might look like:

```ini
[News Crawler]
; Settings for the news crawler

; crawl interval in minutes
interval = 30

; news website to crawl from
news-source = my-favorite-news-source.com

[Mailer]
; Settings for the mailer

; mail address to send to
news-receiver = emma@geller-greene.com
```

Let's break this down. INI files consist of three possible *entities*:
- **Section Name**: In \[brackets\]. Denotes the beginning of a new section (and ending of the one before). E.g. `[News Crawler]`.
- **Comment**: Preceded by a prefix (usually `;`or `#`). Adds explanation to the other entities. E.g. `; Settings for the news crawler`.
- **Option**: Consists of a *key*, a *delimiter* (usually `=` or `:`) and a *value*. Holds an actual setting. E.g. `interval = 30`.

## Setting up the configuration Schema

To use the configurations in your project, your code ideally needs to know what to access. We therefore **mirror the configurations** in your project:

```python
import smartini

class Config(smartini.Schema):

    class Crawler(smartini.Section):
        _name = "News Crawler"
        interval = "interval"
        source = "news-source"

    class Mailer(smartini.Section):
        receiver = "news-receiver"
```
Let's break this down:

- Your *schema class* needs to inherit from [`smartini.Schema`](#smartinischema).
- Each section gets its own *section class* within this schema class, inheriting from [`smartini.Section`](#smartinisection).
- **`Important!`** If the actual section name differs from the section class name, it's assigned to the `_name` class attribute.
- Each option of a section gets its key assigned to an arbitrary string attribute. The variable name **must not start with a leading underscore**.

## Using the configurations in your code

All that's left to do now is, to initialize the schema class and load the ini file.

```python
config = Config()
config.read_ini("config.ini")
```

You can now use the stored configurations by simply accessing them through your schema instance:

```python
>>> config.Crawler.interval
30
>>> config.Mailer.receiver
'emma@geller-greene.com'
```

Similarly, you can assign new values to existing configurations:

```python
>>> config.Crawler.interval = 15
>>> config.Crawler.interval
15
>>> config.Mailer.receiver = "rachel@geller-greene.com"
>>> config.Crawler.receiver
'rachel@geller-greene.com'
```

# Advanced Usage

## Multiple configurations using *slots*

### Introduction

Imagine you send your news crawler (from the [documentation's introduction](#setting-up-a-configuration-file)) to your dad and they configure it like so:

```ini
[News Crawler]
; Settings for the news crawler

; crawl interval in minutes
interval =

; news website to crawl from
news-source = paleontology-papers.com

[Mailer]
; Settings for the mailer

; mail address to send to
news-receiver = ross@geller-greene.com
```

There are two problems with this file:

1. The `interval` option has no value.
2. The `news-source` value does not offer an actual news source.

SmartIni offers an easy solution for this: **Slots**!

### Basic concept

You can think of a *Slot* as a configuration profile: Each configuration file you read is saved into a Slot with its structure (the order in which the entities appear in the file) and all its comments and options. SmartIni intelligently decides which slot to use when you access an option to ensure your code always uses a valid setting.

#### Slot keys

Each slot has a unique slot key. By default, SmartIni generates numerical slot keys starting from 0 upwards. However, you can also choose your own slot key (`int` or `str`) when [reading an ini file](#smartinischemaread_ini).

### Accessing and setting slots

#### Automatically

By default, SmartIni chooses the slot to access or set using one of the [`SlotDeciderMethods`](#smartinislotdecidermethods). The desired method can be passed during [Schema initialization](#smartinischema) and defaults to `"fallback"`, resulting in the latest slot unless that is `None`, then the first slot.

Automatic slot access will also work for any smartini method that receives an argument of type [`SlotAccess`](#smartinislotaccess).

#### Manually

However, you can also access or set slots manually using their slot keys or by index:

- To access or set a slot directly by key, simply use python's item accessing / setting on your schema class.
- To access or set by index, use the same logic on the schema classes iloc indexer.

```python
# Slot access by slot key
config[0].Crawler.interval

# Slot access by index
config.iloc[0].Crawler.interval
```

### Introduction solution

So how does this help us with our initial problem? Easy!

1. Load both configuration files into your project.

    ```python
    >>> config.read_ini("config.ini", slots="default")
    >>> config.read_ini("user.ini", slots="dad")
    ```
2. Access the interval option like before. By default, the `"fallback"` [SlotDeciderMethod](#smartinislotdecidermethods) is used, so smartini will automatically use the first slot for the interval option since the latest is `None`. However, `"cascade down"` would also deliver the desired result here.

    ```python
    >>> config.Crawler.interval
    30
    >>> config["default"].Crawler.interval
    30
    >>> config["dad"].Crawler.interval
    >>> None
    ```

3. For the news-source option, you could verify your dad's input and if that fails, change his configured website to a news source he'd likely find interesting.

    ```python
    >>> if not is_news_source(config["dad"].Crawler.source):
    ...     config["dad"].Crawler.source = "paleantologytoday.com"
    ...     # or config.Crawler.source = ...
    >>> config.Crawler.source
    'paleantologytoday.com'
    ```

## Type hinting and type conversion

By default, SmartIni tries to guess the type of each option value and return it in the respective type or fallback to string representation. However, you can change that behavior for all options or each option individually.

### Introduction

Let's assume you add more Mailer settings to your news crawler (from the [documentation's introduction](#setting-up-a-configuration-file)) like so:

```ini
[Mailer]
; Settings for the mailer

; mail address to send to
news-receiver = ross@geller-greene.com

; Whether the Mail should have a greeting in the beginning.
; + for yes, - for no.
welcome = +

; Time of the day the mail should be sent in 24h format.
time = 15

; Days of the week the mail should be sent.
days = mon, wed, fri
```

By default, `news-receiver`, `welcome`, `time` and `days` will be read as `str`, `str`, `int` and `list[str]`, respectively. However, those types are either wrong (in the case of `welcome`) or can be misleading depending on the input. That's where SmartIni's type converters come into play!

### Basic concept

Smartini's type conversion is based on its [`TypeConverters`](#smartinitype_convertersconverterstypeconverter). Each option's assigned `TypeConverter` is applied on its value with the conversion result saved separately. `TypeConverters` always return the unchanged input if they can't convert it. Thus, if conversion is not successful, converted value and input string are equal.

By default, SmartIni assigns the [default Guess-TypeConverter](#smartinitype_convertersconvertersdefault_guess_converter) to each option. This `TypeConverter` tries to match the value to one of the [`ConvertibleTypes`](#smartinitype_convertersconvertersconvertibletypes). You can change the default `TypeConverter` to one of the other [built-in `TypeConverters`](#built-in-typeconverters), to [your own `TypeConverter`](#creating-your-own-typeconverter) or disable default type conversion all along by setting the respective [parameter](#smartiniparameters) during [Schema initialization](#smartinischema).


You can also define a specific type - and thus a specific type converter - separately for one or more options using [simple python typing](#assigning-typeconverters-via-type-hinting). This can be helpful to ensure each option is of correct type or if your ini differs from SmartIni's default conversion behavior.

### Built-in `TypeConverters`

SmartIni comes with the following [built-in `TypeConverters`](#smartinitype_convertersconverters), that can be used with their default arguments or customized using the respective creator functions:

| `TypeConverter` | Default                                                                                    | Creator function                                                             |
| --------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| **Bool**        | [`DEFAULT_BOOL_CONVERTER`](#smartinitype_convertersconvertersdefault_bool_converter)       | [`bool_converter()`](#smartinitype_convertersconvertersbool_converter)       |
| **Guess**       | [`DEFAULT_GUESS_CONVERTER`](#smartinitype_convertersconvertersdefault_guess_converter)     | [`guess_converter()`](#smartinitype_convertersconvertersguess_converter)     |
| **List**        | [`DEFAULT_LIST_CONVERTER`](#smartinitype_convertersconvertersdefault_list_converter)       | [`list_converter()`](#smartinitype_convertersconverterslist_converter)       |
| **Numeric**     | [`DEFAULT_NUMERIC_CONVERTER`](#smartinitype_convertersconvertersdefault_numeric_converter) | [`numeric_converter()`](#smartinitype_convertersconvertersnumeric_converter) |

### Creating your own `TypeConverter`

You can also create your own [`TypeConverter`](#smartinitype_convertersconverterstypeconverter) by passing a `Callable` to [`type_converters.new_converter`](#smartinitype_convertersconvertersnew_converter). The Callable takes a `str` as input and returns the converted value or raises [`type_converters.WrongType`](#smartinitype_convertersconverterswrongtype) if conversion was unsuccessful. 

### Assigning `TypeConverters` via type hinting

You can set an option's type and thus its [`TypeConverter`](#smartinitype_convertersconverterstypeconverter) by annotating it in your [`Schema`](#smartinischema) definition using [`smartini.TYPE[]`](#smartinitype) in one of the following ways:

| Type annotation                                                                          | Explanation                                                                                                                                                                                |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TYPE` \| [`GUESS`](#smartinitype_converterstype_hintsguess)                             | Assigns the [`Guess-TypeConverter`](#smartinitype_convertersconvertersguess_converter).                                                                                                    |
| [Pre-defined type hint](#smartinitype_converterstype_hints)                              | Assigns [built-in type converters](#built-in-typeconverters). E.g. [`BOOL`](#smartinitype_converterstype_hintsbool).                                                                       |
| `TYPE[type[`[`ConvertibleTypes`](#smartinitype_convertersconvertersconvertibletypes)`]]` | Assigns a `TypeConverter` matching the type. E.g. `TYPE[int]` will assign a [`Numeric-TypeConverter`](#smartinitype_convertersconvertersdefault_numeric_converter) that converts to `int`. |
| `TYPE[type[TypeConverter]]`                                                              | Assigns the annotated `TypeConverter` (e.g. your own).                                                                                                                                     |

Alternatively, SmartIni also comes with [pre-defined type hints](#smartinitype_converterstype_hints) for its built-in `TypeConverters`.

### Introduction solution

Let's look at our Mailer options again. We want `welcome` to be represented as a boolean and we might want `time` to be represented as a `datetime.time` object. Here's how we can do it:

1. Create a [boolean converter](#smartinitype_convertersconvertersbool_converter) that interprets `"+"` as `True` and `"-"` as `False`.

    ```python
    from smartini.type_converters.converters import bool_converter
    
    bool_type = bool_converter(true="+", false="-")
    ```
2. Create a custom converter that converts a value to a `datetime.time` object.

    ```python
    from smartini.type_converters.converters import new_converter, WrongType
    from datetime import time

    def convert_to_time(string:str) -> time:
        try:
            return time(int(string))
        except ValueError:
            raise WrongType
    
    time_type = new_converter(convert_to_time)
    ```
3. Assign both converters respectively.

    ```python
    from smartini import Schema, Section, TYPE
    from smartini.type_converters.type_hints import STR

    class Config(Schema):

        ...

        class Mailer(Section):
            receiver: STR = "news-receiver"
            welcome: TYPE[bool_type] = "welcome"
            time: TYPE[time_type] = "time"
            days: TYPE[list[str]] = "days"

    ```

    > Note:
    > - The type annotations for `receiver` and `days` are not really necessary here as SmartIni already guesses the correct types.
    > - For `list` type annotations, SmartIni will guess each list item's type if no item type annotation is provided in brackets.

## Custom markers

SmartIni allows for customization of the following markers by passing the respective argument during [Schema initialization](#smartinischema):

| Marker               | argument            | default | Explanation                                                                                                     |
| -------------------- | ------------------- | ------- | --------------------------------------------------------------------------------------------------------------- |
| **Option delimiter** | `option_delimiters` | `"="`   | Separates option key from value, e.g. `opt`**`=`**`val`. You can pass multiple if the ini file is inconsistent. |
| **Comment prefix**   | `comment_prefixes`  | `";"`   | Denotes a comment, e.g. **`;`**`comment`. You can pass multiple if the ini file is inconsistent.                |

> For further information see [Parameters](#smartiniparameters).

## Multiline options

SmartIni by default allows for multiline option values, so for the whole value to span over multiple lines. Every line after the first line is called a *continuation*. You can control this behavior by specifying the three multiline parameters during [Schema initialization](#smartinischema).

> For further information see [Parameters](#smartiniparameters).

## Undefined configurations

Smartini can also read configurations that are not defined in-code in your [Schema](#smartinischema) class. To do so, simply pass `read_undefined = True` to your [Schema initialization](#smartinischema). To access undefined content, use [get_sections](#smartinischemaget_sections) and [get_options](#smartinisectionget_options) with `include_undefined="only"`.

> Note: If you leave `read_undefined = False` (default), smartini will throw an `IniStructureError` if it encounters undefined content.

# Documentation

## smartini.**Comment**

Comment object holding a comment's content.

```python
Comment(content_without_prefix = None, prefix = None, content_with_prefix = None)
```

**Args**

- **content_without_prefix** (`str | None`, optional)

    Content with prefix removed. Should be `None` if `content_with_prefix` is provided, otherwise the latter will be ignored. Defaults to `None`.

- **prefix** ([`VALID_MARKERS`](#smartinivalid_markers)` | tuple[VALID_MARKERS, ...] | None`, optional)

    One or more prefixes that can denote the comment (used for content_with_prefix). Defaults to `None`.

- **content_with_prefix** (`str | None`, optional)

    Content including prefix. Will be ignored if `content_without_prefix` is provided. Defaults to `None`.

### smartini.Comment.**content**

```python
Comment.content
```

The comment's content.

### smartini.Comment.**to_string**

```python
Comment.to_string(prefix)
```

Convert the Comment into an ini string.

**Args**

- **prefix** (`str | None`, optional)

    Prefix to use for the string. Returns to None.

**Returns**

- `str`

    The ini string.

## smartini.**Option**

Option object holding an option's value (per slot) and key.

```python
Option(key, values = None, type_converter = None, slots = None)
```    

**Args**

- **key** (`str | int | None`, optional)

    The option key. Should be `None` if `from_string` is provided, otherwise `from_string` will be ignored. Defaults to `None`.

- **values** (`Any | list[Any] | None`, optional)

    The option value or values (one value per slot or one/same value for all slots). Should be `None` if `from_string` is provided, otherwise `from_string` will be ignored. Defaults to `None`.

- **type_converter** (`type[`[`TypeConverter`](#smartinitype_convertersconverterstypeconverter)` | `[`ConvertibleTypes`](#smartinitype_convertersconvertersconvertibletypes)`] | None`, optional)

    TypeConverter to apply to every option value (and continuation) that is not explicitly annotated. Alternatively one of the `ConvertibleTypes` that the option values should be interpreted as (will be matched to a `TypeConverter`). If `None`, will save all values (and continuations) as strings. Defaults to [`DEFAULT_GUESS_CONVERTER`](#smartinitype_convertersconvertersdefault_guess_converter).

- **slots** (`SlotAccess`, optional)

    Slot(s) to save value(s) in. If `None`, will create numerical slot keys starting from `0`. Otherwise, number of slots must match number of values, unless number of values is `1` (:= same value for all slots). Defaults to `None`.

### smartini.Option.**to_string**

```python
to_string(delimiter, *, slots = None)
```

Convert the Option into an ini string.

**Args**

- **delimiter** ([`VALID_MARKERS`](#smartinivalid_markers))

    The delimiter to use for separating option key and value.

- **slot** (`SlotAccess`, optional)

    The slot to get the value from. If multiple are passed, will take the first that is not `None` (or return an empty string if all are `None`). If `None`, will take the first that is not None of all slots. Defaults to `None`.

**Returns**

- `str`

    The ini string.    

## smartini.**Parameters**

Parameters for reading and writing.

```python
Parameters(comment_prefixes = ";", option_delimiters = "=", multiline_allowed = True, multiline_prefix = None, multiline_ignore = (), ignore_whitespace_lines = True, read_undefined = False, default_type_converter = smartini.type_converters.DEFAULT_GUESS_CONVERTER)
```

**Args**

- **comment_prefixes** ([`VALID_MARKERS`](#smartinivalid_markers)`| tuple[VALID_MARKERS, ...]`, optional)

    Prefix character(s) that denote a comment. If multiple are given, the first will be taken for writing. If None, will treat every line as comment that is not an option or section name. Defaults to `";"`.

- **option_delimiters** ([`VALID_MARKERS`](#smartinivalid_markers)`| tuple[VALID_MARKERS, ...]`, optional)

    Delimiter character(s) that delimit option keys from values. If multiple are given, the first will be taken for writing. Defaults to `"="`.

- **multiline_allowed** (`bool`, optional)

    Whether continuations of options (i.e. multiline options) are allowed. Defaults to `True`.

- **multiline_prefix** (`VALID_MARKERS | Literal["\t"] | None`, optional)

    Prefix to denote continuations of multiline options. If set, will only accept continuations with that prefix (will throw a `ContinuationError` if that prefix is missing). Defaults to `None` (possible continuation without prefix).

- **multiline_ignore** (`tuple["section_name" | "option_delimiter" |
        "comment_prefix", ...] | None`, optional)
        
    Entity identifier(s) to ignore while continuing an option's value. Otherwise lines with those identifiers will be interpreted as a new entity instead of a continuation (despite possibly satisfying multiline rules). Useful if a continuation is possibly in brackets (otherwise interpreted as a section name), contains the option delimiter (e.g. URLs often include a `"="`) or starts with a comment prefix. Defaults to `None`.

- **ignore_whitespace_lines** (`bool`, optional)

    Whether to interpret lines with only whitespace characters (space or tab) as empty lines. Defaults to `True`.

- **read_undefined** (`bool | "section" | "option"`, optional)
    
    Whether undefined content should be read and stored. If `True`, will read every undefined content. If `"section"`, will read undefined sections and their content but not undefined options within defined sections. `"option"` will read undefined options within defined sections but not undefined sections and their content. If `False`, will ignore undefined content. Defaults to `False`.

- **default_type_converter** (`type[`[`TypeConverter`](#smartinitype_convertersconverterstypeconverter)`] | None`, optional):

    `TypeConverter` class to apply to every option value (and continuation) that is not annotated otherwise. If `None`, will save all values (and continuations) as strings. Defaults to `smartini.type_converters.DEFAULT_GUESS_CONVERTER`.    

## smartini.**Schema**

Schema class to define configuration schema and access loaded configurations.

```python
Schema(parameters = None, method = "fallback", **kwargs)
```

Parameters will be stored as default read and write parameters.

**Args**

- **parameters** ([`Parameters`](#smartiniparameters)`| None`, optional)

    Default parameters for reading and writing inis, as an `Parameters` object. `Parameters` can also be passed as kwargs. Missing parameters (because parameters is `None` and no or not enough kwargs are passed) will be taken from default parameters. Defaults to `None`.

- **method** ([`SlotDeciderMethods`](#smartinislotdecidermethods), optional)

    Method for choosing the slot. Defaults to `"fallback"`.

- **\*\*kwargs** (optional)

    [`Parameters`](#smartiniparameters) as kwargs.

### smartini.Schema.**export**

```python
Schema.export(path = None, decider_method = None, include_undefined = True, export_comments = False, *, content_slots = None)
```

Export the saved configuration to a file.

**Args**

- **path** (`str | Path`)
    
    Path to the file to export to.

- **structure** (`"schema" | "content" | None`, optional)

    Slot to use for structuring the output (including comments). If `"schema"`, will use original schema definition. If `"content"`, will use slot that is used as content slot (if multiple content slots are given will use the first). If `None` will use `"schema"` if `content_slots` is `None` and `"content"` otherwise. Defaults to `None`.

- **decider_method** ([`SlotDeciderMethods`](#smartinislotdecidermethods)`| None`, optional)

    Either a decider method to use or `None` to use the initial decider method. Defaults to `None`.

- **include_undefined** (`bool`, optional)

    Whether to include undefined entities. Defaults to `True`.

- **export_comments** (`bool`, optional)

    Whether to export comments. Will use first content slot to get comments from. Comments will be matched to following entities (e.g. all comments above option_a will be above option_a in the exported ini). Defaults to `False`.

- **content_slots** ([`SlotAccess`](#smartinislotaccess), optional)

    Slot(s) to use for content (sections and options). If multiple are given, first slot has priority, then second (if first is `None`) and so on. If `None`, will use decider method. Defaults to `None`.

### smartini.Schema.**get_section**

```python
Schema.get_section(section_name)
```

Get a section by its name.

**Args**

- **section_name** ([`SectionName`](#smartinisectionname)` | str | None`)

    The name of the section to get.

**Returns**

- `tuple[str, `[`Section`](#smartinisection)`]`

    Tuple of variable name and section object.

### smartini.Schema.**get_sections**

```python
Schema.get_sections(include_undefined = True, *, slots = None)
```

Get configuration section(s).

**Args**

- **include_undefined** (`bool`, optional)
  
    Whether to also include undefined sections. Defaults to `True`.
- **slots** ([`SlotAccess`](#smartinislotaccess), optional)

    Which slot(s) to get sections from. If multiple are given, will return the intersection. If `None`, will return all. Defaults to `None`.

**Returns**

- `OrderedDict[str, `[`Section`](#smartinisection)`]`

    Variable names as keys and the Sections as values. Order is that of the slot structure if `len(slots) == 1`. Otherwise, order matches defined schema structure with undefined sections at the end.

### smartini.Schema.**read_ini**

```python
Schema.read_ini(path, parameters = None, parameters_as_default = False, *, slots = False, **kwargs)
```
   
Read an INI file. If no parameters are passed (as [`Parameters`](#smartiniparameters) object or kwargs), default parameters defined on initialization will be used.

**Args**

- **path** (`str | pathlib.Path`)

    Path to the INI file.

- **parameters** ([`Parameters`](#smartiniparameters)`| None`, optional)

    Parameters for reading and writing INIs, as a `Parameters` object. `Parameters` can also be passed as kwargs. Missing parameters (because parameters is `None` and no or not enough kwargs are passed) will be taken from default parameters that were defined on initialization. Defaults to `None`.

- **parameters_as_default** (`bool`, optional)

    Whether to save the parameters for this read as default parameters. Defaults to `False`.

- **\*\*kwargs** (optional)

    [Parameters](#smartiniparameters) as kwargs.

- **slots** ([`SlotAccess`](#smartinislotaccess)`| False`, optional)

    Slot(s) to save the content in. If `False` will create new slot. Defaults to `False`.

### smartini.Schema.**with_slot**

```python
Schema.with_slot(slot)
```

Access the ini using a specific slot. Equivalent to item access via brackets (i.e. `Schema[slot]`).

**Args**

- slot ([`SlotAccess`](#smartinislotaccess))

    The slot to use.

**Example**

```python
>>> class Config(smartini.Schema):
...     class Section(smartini.Section):
...         option = "option-name"
>>> config = Config()
>>> config.read_ini("config1.ini")
>>> config.read_ini("config2.ini")
>>> config.with_slot(1).Section.option == config[1].Section.option
True
```

## smartini.**Section**

A configuration section. Holds [Options](#smartinioption) and [Comments](#smartinicomment). **If the actual section name differs from class variable, it needs to be assigned to the *_name* class attribute! Furthermore, class attributes holding options must not start with a leading underscore!**

### smartini.Section.**add_entity**

```python
Section.add_entity(entity, positions = None, *, slots = None)
```    
Add a new entity to the section.

**Args**
    
- **entity** ([`UndefinedOption`](#smartiniundefinedoption)` | `[`Option`](#smartinioption)` | `[`Comment`](#smartinicomment))

    The entity to add.

- **positions** (`int | list[int | None]`, optional)

    Where to put the entity in the section's structure. Either one position for all slots or a `list` with one position per slot. If `None`, will append to the end in every slot. Defaults to `None`.

 - **slots** ([`SlotAccess`](#smartinislotaccess), optional)
  
    Slot(s) to add the entity to. Must match positions. Defaults to `None`.

**Returns**

- ([`UndefinedOption`](#smartiniundefinedoption)` | `[`Comment`](#smartinicomment))

    The newly created entity.

### smartini.Section.**get_comments_by_content**

```python
Section.get_comments_by_content(content)
```

Get comments matching the content.

**Args**

- **content** (`str | re.Pattern`)

    The content of the comment.

**Returns**

- `dict[str, `[`Comment`](#smartinicomment)`]`

    All comments that fit the content argument with variable names as keys and the [`Comment`](#smartinicomment) objects as values.    

### smartini.Section.**get_option**

```python
Section.get_option(name = None, key = None)
```
Get an option by variable name or option key.

**Args**

- **name** (`str | None`, optional)

    Name of the option variable. Defaults to `None`.

- **key** (`SlotKey | None`, optional)

    The option key. Will be ignored if `name` is not `None`. Defaults to `None`.

**Returns**

- [`Option`](#smartinioption)

    The requested option.

### smartini.Section.**get_options**

```python
Section.get_options(include_undefined = True, *, slots = None)
```
Get options of the section.

**Args**

- **include_undefined** (`bool | "only"`, optional)

    Whether to include undefined options. If `"only"`, will return only undefined options. Always `False` if slots is not `None`.

- **slots** ([`SlotAccess`](#smartinislotaccess), optional)

    Which slot(s) to get options from. If multiple are given, will return the intersection. If `None` will return all. Defaults to `None`.

**Returns**

- `OrderedDict[str, Option]`

    Variable names as keys and Options as values. Order is that of the slot structure if `len(slots) == 1`. Otherwise, order matches original schema structure with undefined options at the end.

### smartini.Section.**set_option**

```python
Section.set_option(name, value, positions = None, key = None, *, slots = None)
```
Set an option's value by accessing it via variable name or option key.

**Args**

- **name** (`str | None`)

    The variable name of the option. Must be `None` if key should be used.

- **value** (`OptionValue`)

    The new value for the option.    

- **positions** (`int | list[int | None] | None`)

    Position in slots the entity should take. Either `int` for same position in all slots or one position per slot. If `None` and for every slot that `None` is specified for, will take previous position of the Option in the respective slot and will append to slots where Option didn't exist before. Defaults to `None`.

 - **key** (`str | None`, optional)

    The option key. Defaults to `None`.

- **slots** ([`SlotAccess`](#smartinislotaccess), optional)

    The slot(s) to use. Defaults to `None` (all slots).

## smartini.**SectionName**

A configuration section's name.

```python
SectionName(name = None, name_with_brackets = None)
```

**Args**

- **name** (`str | None`, optional)

    Name of the section. Should be `None` if `name_with_brackets` is provided, otherwise `name_with_brackets` will be ignored. Defaults to `None`.

- **name_with_brackets** (`str | None`, optional)

    The name of the section within brackets (to extract the name from). If provided, `name` argument should be `None`, otherwise will be ignored. Defaults to `None`.


## smartini.**SlotAccess**

```python
type SlotAccess = int | str | list[int | str] | None
```

Identifier for which slot(s) to access.

- `int | str`

    Identifier for a single slot.

- `list[int | str]`

    Identifier for multiple slots.

- `None`

    All slots.

## smartini.**SlotDeciderMethods**

```python
type SlotDeciderMethods = "fallback" | "first" | "cascade up" | "latest" | "cascade down"
```

Method to decide which slot to use.

- `"fallback"`

    Uses first slot whenever latest slot is `None`, otherwise latest slot. This is especially useful if the first slot provides default fallback values for your configuration.
- `"first"`

    Uses first slot.

- `"cascade up"`

    Uses the first slot that is not `None` from first to latest.

- `"latest"`

    Uses latest slot.

- `"cascade down"`

    Uses first slot that is not `None` from latest to first.

## smartini.**TYPE**

Type annotation for type converters. All types passed in brackets will be tried for conversion, first successful conversion will be applied.

**Example**:

```python
option_1: TYPE[int,bool] = "option-1"
```

SmartIni will try to convert into `int` first, then into `bool`, then interpret as `str`.

## smartini.**type_converters**

SmartIni's type conversion logic.

### smartini.type_converters.**converters**

Converter classes and functions.

#### smartini.type_converters.converters.**bool_converter**

```python
type_converters.bool_converter(true = ("1", "true", "yes", "y"), false = ("0", "false", "no", "n"))
```

Create a new `bool` converter.

**Args**

- **true** (`str | tuple[str, ...]`, optional)

    String(s) that should be regarded as `True`. Defaults to `("1", "true", "yes", "y")`.
- **false** (`str | tuple[str, ...]`, optional)

    String(s) that should be regarded as `False`. Defaults to `("0", "false", "no", "n")`.

**Returns**

- `type[TypeConverter[bool]]`

    The `bool` type converter.

#### smartini.type_converters.converters.**ConvertibleTypes**

```python
ConvertibleTypes = int | float | complex | bool | list
```

Types that SmartIni can convert the input strings into.

> Note: SmartIni also allows for annotating the item type of a `list`, e.g. `list[int]`.

#### smartini.type_converters.converters.**DEFAULT_BOOL_CONVERTER**

```python
DEFAULT_BOOL_CONVERTER = smartini.type_converters.bool_converter()
```

[Bool converter](#smartinitype_convertersconvertersbool_converter) with default conversion parameters.

#### smartini.type_converters.converters.**DEFAULT_GUESS_CONVERTER**

```python
DEFAULT_GUESS_CONVERTER = smartini.type_converters.guess_converter()
```

[Guess converter](#smartinitype_convertersconvertersguess_converter) with default conversion parameters.

#### smartini.type_converters.converters.**DEFAULT_LIST_CONVERTER**

```python
DEFAULT_LIST_CONVERTER = smartini.type_converters.list_converter()
```

[List converter](#smartinitype_convertersconverterslist_converter) with default conversion parameters.

#### smartini.type_converters.converters.**DEFAULT_NUMERIC_CONVERTER**

```python
DEFAULT_NUMERIC_CONVERTER = smartini.type_converters.numeric_converter()
```

[Numeric converter](#smartinitype_convertersconvertersnumeric_converter) with default conversion parameters.

#### smartini.type_converters.converters.**guess_converter**

```python
type_converters.guess_converter(*types)
```

Create a new type converter that guesses the type.

**Args**
- **\*types** (`type`)

    The types to guess. If not provided, will guess all of [`type_converters.ConvertibleTypes`](#smartinitype_convertersconvertersconvertibletypes).

**Returns**

- `type[`[`TypeConverter`](#smartinitype_convertersconverterstypeconverter)`]`

    The new Guess-TypeConverter.

#### smartini.type_converters.converters.**list_converter**

```python
type_converters.list_converter(delimiter = ",", remove_whitespace = True, item_converter = None)
```

Create a new `list` type converter.

**Args**
    
- **delimiter** (`str`, optional)

    Delimiter that separates list items. Defaults to `","`.

- **remove_whitespace** (`bool`, optional)

    Whether whitespace between items and delimiter should be removed. Defaults to `True`.

- **item_converter** (`type[TypeConverter[Any]]`)

    [`TypeConverter`](#smartinitype_convertersconverterstypeconverter) to convert each list item with. If `None`, will use [Guess-TypeConverter](#smartinitype_convertersconvertersguess_converter). Defaults to `None`.

**Returns**

- `type[TypeConverter[list]]`

    The new `list` type converter.

#### smartini.type_converters.converters.**new_converter**

```python
type_converters.new_converter(processor, name = None)
```

Create a new [TypeConverter](#smartinitype_convertersconverterstypeconverter).

**Args**

- **processor** (`Callable[[str], T]`)

    Callable to process the string input and convert it into an instance of arbitrary type. If conversion is not possible, should raise [WrongType](#smartinitype_convertersconverterswrongtype).

- **name** (`str | None`, optional)

    Name for the new [`TypeConverter`](#smartinitype_convertersconverterstypeconverter). Will be appended to result into `TypeConverter_{name}`. If `None`, will take the processor function's name. Defaults to `None`.

**Returns**

- `type[TypeConverter[T]]`

    [`TypeConverter`](#smartinitype_convertersconverterstypeconverter) that will return the processed input on call or the input itself if conversion was not possible.

#### smartini.type_converters.converters.**numeric_converter**

```python
type_converters.numeric_converter(numeric_type = (int, float, complex), decimal_sep = ".", thousands_sep = ",")
```

Create a new numeric type converter.

**Args**

- **numeric_type** (`type[int | float | complex] | tuple[type[int | float | complex], ...]`, optional)

    The type to convert to. If multiple are given, the type converter will return the first type that the conversion was successful for. Defaults to `(int, float, complex)`.

- **decimal_sep** (`str`, optional)

    Possible decimal separator inside the string. Defaults to `"."`.

- **thousands_sep** (`str`, optional)

    Possible thousands separator inside the string. Defaults to `","`.

**Returns**

* `type[TypeConverter[int | float | complex]]`

    The numeric type converter.

#### smartini.type_converters.converters.**TypeConverter**

Parent class for type converters. To create a type converter, use [`new_converter()`](#smartinitype_convertersconvertersnew_converter).    

#### smartini.type_converters.converters.**WrongType**

Exception. Raised when a value could not be converted.

### smartini.type_converters.**type_hints**

Pre-defined type hints for built-in type converters.

#### smartini.type_converters.type_hints.**BOOL**

```python
BOOL = TYPE[DEFAULT_BOOL_CONVERTER]
```

Boolean type converter.

#### smartini.type_converters.type_hints.**GUESS**

```python
GUESS = TYPE[DEFAULT_GUESS_CONVERTER]
```

Type converter that will guess the type.

#### smartini.type_converters.type_hints.**LIST**

```python
LIST = TYPE[DEFAULT_LIST_CONVERTER]
```

List type converter.

#### smartini.type_converters.type_hints.**NUMERIC**

```python
STR = TYPE[str]
```

Annotation for a string option value.

#### smartini.type_converters.type_hints.**STR**

```python
NUMERIC = TYPE[DEFAULT_NUMERIC_CONVERTER]
```

Numeric type converter.

## smartini.**UndefinedOption**

Option, that is not hard coded in the provided schema.

```python
UndefinedOption(*args,**kwargs)
```

Takes args and kwargs identical to [`Option`](#smartinioption). Can also take an Option to copy its attributes.

## smartini.**VALID_MARKERS**

```python
VALID_MARKERS = Literal["\\","!",'"',"§","%","&","/","(",")","?",":",";","#","'","*",">","<","=",]
```

Valid characters for markers (option delimiter, comment prefix or multiline prefix).


# Why still ini?

**a word from the creator**

SmartIni started from a simple problem: I had built this awesome project that I wanted my non-coder friends to be able to use and set up to their needs. However, I didn't have the capacity to build a GUI and didn't want to use JSON or YAML either as they too use concepts foreign to non-coders (like quotation of strings).

INI files provide an intuitive approach to text-based settings, therefore seemed to be the best option for my needs. The only problem left was, that existing modules for handling INI files (like the built-in configparser) suffer from several drawbacks. Luckily, now we have SmartIni :) 

# Contributing

As of now, this has been a one person project. If you want to contribute to it, you're very invited to do so by:

1. Cloning the repository

    ```shell
    git clone git@github.com:t1h0/smartini.git
    ```

2. Installing the repositories into an python 3.12+ environment

    ```shell
    cd smartini
    pip install -r requirements.txt
    ```

3. Add appropriate test files to `./tests` and make sure `pytest .` finishes without a warning or exception.

4. Send a pull request once you're done :)

> Note: SmartIni's stub files "fool" type checkers by giving them false type annotations to ensure intuitive functionality (e.g. `Schema.iloc` is annotated to return the `Schema` (`Self`) although it actually returns a `SlotIlocViewer`). For development, you should disable the stub files (i.e. ignore them in your type checker config or rename them).

By contributing to this project, you agree that your contributions will be licensed under the project's [license](/LICENSE).

# License

Smartini is licensed under the Apache-2.0 license, as found in the [LICENSE](/LICENSE) file.