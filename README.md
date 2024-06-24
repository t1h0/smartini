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
    - [Introductionary example](#introductionary-example)
    - [Basic concept](#basic-concept)
      - [Slot keys](#slot-keys)
    - [Accessing and setting slots](#accessing-and-setting-slots)
      - [Automatically](#automatically)
      - [Manually](#manually)
    - [Example solution](#example-solution)
  - [Custom markers](#custom-markers)
  - [Multiline options](#multiline-options)
  - [Undefined configurations](#undefined-configurations)
- [Documentation](#documentation)
  - [smartini.**Comment**](#smartinicomment)
    - [smartini.Comment.**content**](#smartinicommentcontent)
    - [smartini.Comment.**Prefix**](#smartinicommentprefix)
    - [smartini.Comment.**to\_string**](#smartinicommentto_string)
  - [smartini.**Option**](#smartinioption)
    - [smartini.Option.**Delimiter**](#smartinioptiondelimiter)
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
    - [smartini.Section.**get\_comment\_by\_content**](#smartinisectionget_comment_by_content)
    - [smartini.Section.**get\_option**](#smartinisectionget_option)
    - [smartini.Section.**get\_options**](#smartinisectionget_options)
    - [smartini.Section.**set\_option**](#smartinisectionset_option)
  - [smartini.**SectionName**](#smartinisectionname)
  - [smartini.**SlotAccess**](#smartinislotaccess)
  - [smartini.**SlotDeciderMethods**](#smartinislotdecidermethods)
  - [smartini.**UndefinedOption**](#smartiniundefinedoption)
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
'30'
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
> As you can see, all values are currently read from file as strings, whereas assignment won't change the type. In future releases, numerical values, lists etc. will be read as their respective types from file as well.

# Advanced Usage

## Multiple configurations using *slots*

### Introductionary example

Imagine you send your news crawler (from the example above) to your dad and they configure it like so:

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

### Example solution

So how does this help us with our initial problem? Easy!

1. Load both configuration files into your project.

    ```python
    >>> config.read_ini("config.ini", slots="default")
    >>> config.read_ini("user.ini", slots="dad")
    ```
2. Access the interval option like before. By default, the `"fallback"` [SlotDeciderMethod](#smartinislotdecidermethods) is used, so smartini will automatically use the first slot for the interval option since the latest is `None`. However, `"cascade down"` would also deliver the desired result here.

    ```python
    >>> config.Crawler.interval
    '30'
    >>> config["default"].Crawler.interval
    '30'
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

## Custom markers

SmartIni allows for customization of the following markers by passing the respective argument during [Schema initialization](#smartinischema):

- **Entity delimiter**, `entity_delimiter`, default: `"\n"` (newline)

    Separates entities from each other, e.g. `opt=val`**`\n`**`; comment`
- **Option delimiter**, `option_delimiters`, default: `"="`

    Separates option key from value, e.g. `opt`**`=`**`val`. You can pass multiple if the ini file is inconsistent.
- **Comment prefix**, `comment_prefixes`, default: `";"`

    Denotes a comment, e.g. **`;`**`comment`. You can pass multiple if the ini file is inconsistent.

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

- **prefix** (`str | re.Pattern | tuple[str | re.Pattern, ...] | None`, optional)

    One or more prefixes that can denote the comment (used for `content_with_prefix`). Defaults to `None`.

- **content_with_prefix** (`str | None`, optional)

    Content including prefix. Will be ignored if `content_without_prefix` is provided. Defaults to `None`.

### smartini.Comment.**content**

```python
Comment.content
```

The comment's content.

### smartini.Comment.**Prefix**

```python
type Prefix = str | re.Pattern
```

Character(s) that prefix(es) a comment.

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
Option(key, values = None, slots = None)
```    

**Args**

- **key** (`str | int | None`, optional)

    The option key. Should be `None` if `from_string` is provided, otherwise `from_string` will be ignored. Defaults to `None`.

- **values** (`Any | list[Any] | None`, optional)

    The option value or values (one value per slot or one/same value for all slots). Should be `None` if `from_string` is provided, otherwise `from_string` will be ignored. Defaults to `None`.

- **slots** (`SlotAccess`, optional)

    Slot(s) to save value(s) in. If `None`, will create numerical slot keys starting from `0`. Otherwise, number of slots must match number of values, unless number of values is `1` (:= same value for all slots). Defaults to `None`.

### smartini.Option.**Delimiter**

```python
type Delimiter = str | re.Pattern
```

Character(s) that delimit(s) Option key from from value.

### smartini.Option.**to_string**

```python
to_string(delimiter, *, slots = None)
```

Convert the Option into an ini string.

**Args**

- **delimiter** (`str`)

    The delimiter to use for separating option key and value.

- **slot** (`SlotAccess`, optional)

    The slot to get the value from. If multiple are passed, will take the first that is not `None` (or return an empty string if all are `None`). If `None`, will take the first that is not None of all slots. Defaults to `None`.

**Returns**

- `str`

    The ini string.    

## smartini.**Parameters**

Parameters for reading and writing.

```python
Parameters(entity_delimiter = re.Pattern("\n"), comment_prefixes = ";", option_delimiters = "=", multiline_allowed = True, multiline_prefix = None, multiline_ignore = (), ignore_whitespace_lines = True, read_undefined = False)
```

**Args**
    
- **entity_delimiter** (`str | re.Pattern`, optional)

    Delimiter that delimits entities (section name, option, comment). Defaults to `re.Pattern("\n")`.

- **comment_prefixes** ([`Comment.Prefix`](#smartinicommentprefix)`| tuple[Comment.Prefix, ...]`, optional)

    Prefix character(s) that denote a comment. If multiple are given, the first will be taken for writing. `"["` is not allowed. Defaults to `";"`.

- **option_delimiters** ([`Option.Delimiter`](#smartinioptiondelimiter)`| tuple[Option.Delimiter, ...]`, optional)

    Delimiter character(s) that delimit option keys from values. If multiple are given, the first will be taken for writing. `"["` is not allowed. Defaults to `"="`.

- **multiline_allowed** (`bool`, optional)

    Whether continuations of options (i.e. multiline options) are allowed. Defaults to `True`.

- **multiline_prefix** (`str | re.Pattern | None`, optional)

    Prefix to denote continuations of multiline options. If set, will only accept continuations with that prefix (will throw a `ContinuationError` if that prefix is missing). Defaults to `None` (possible continuation after one entity delimiter).

- **multiline_ignore** (`tuple["section_name" | "option_delimiter" |
        "comment_prefix", ...] | None`, optional)
        
    Entity identifier(s) to ignore while continuing an option's value. Otherwise lines with those identifiers will be interpreted as a new entity instead of a continuation (despite possibly satisfying multiline rules). Useful if a continuation is possibly in brackets (otherwise interpreted as a section name), contains the option delimiter (e.g. URLs often include a `"="`) or starts with a comment prefix. Defaults to `None`.

- **ignore_whitespace_lines** (`bool`, optional)

    Whether to interpret lines with only whitespace characters (space or tab) as empty lines. Defaults to `True`.

- **read_undefined** (`bool | "section" | "option"`, optional)
    
    Whether undefined content should be read and stored. If `True`, will read every undefined content. If `"section"`, will read undefined sections and their content but not undefined options within defined sections. `"option"` will read undefinied options within defined sections but not undefined sections and their content. If `False`, will ignore undefined content. Defaults to `False`.

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
   
Read an ini file. If no parameters are passed (as [`Parameters`](#smartiniparameters) object or kwargs), default parameters defined on initialization will be used.

**Args**

- **path** (`str | pathlib.Path`)

    Path to the ini file.

- **parameters** ([`Parameters`](#smartiniparameters)`| None`, optional)

    Parameters for reading and writing inis, as a `Parameters` object. `Parameters` can also be passed as kwargs. Missing parameters (because parameters is `None` and no or not enough kwargs are passed) will be taken from default parameters that were defined on initialization. Defaults to `None`.

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

### smartini.Section.**get_comment_by_content**

```python
Section.get_comment_by_content(content)
```

Get a comment by its content.

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

- `Option`

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

## smartini.**UndefinedOption**

Option, that is not hard coded in the provided schema.

```python
UndefinedOption(*args,**kwargs)
```

Takes args and kwargs identical to [`Option`](#smartinioption). Can also take an Option to copy its attributes.

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

3. Send a pull request once you're done :)

> Note: SmartIni's stub files "fool" type checkers by giving them false type annotations to ensure intuitive functionality (e.g. `Schema.iloc` is annotated to return the `Schema` (`Self`) although it actually returns a `SlotIlocViewer`). For development, you should disable the stub files (i.e. ignore them in your type checker config or rename them).

By contributing to this project, you agree that your contributions will be licensed under the project's [license](/LICENSE).

# License

Smartini is licensed under the Apache-2.0 license, as found in the [LICENSE](/LICENSE) file.