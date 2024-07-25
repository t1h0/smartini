from .base import Base
from smartini import exceptions_warnings, Parameters, VALID_MARKERS
from smartini.utils import _str_to_var
import pytest
from typing import get_args
from itertools import combinations, product
from contextlib import nullcontext

multiline_warning = pytest.warns(exceptions_warnings.MultilineWarning)
undefined_section_warning = pytest.warns(exceptions_warnings.UndefinedSectionWarning)
undefined_option_warning = pytest.warns(exceptions_warnings.UndefinedOptionWarning)
attribute_error = pytest.raises(AttributeError)


class TestParameters:

    # ----------
    # set parameters to test
    # ----------

    # -----
    # basic access and type conversion with basic args
    # -----
    test_parameters = []
    basic_tests = [
        {"opt_val": "1,2,3", "opt_result": [1, 2, 3]},
        {"opt_val": "a,b,c", "opt_result": ["a", "b", "c"]},
        {"opt_val": "True,False,True", "opt_result": [True, False, True]},
        {"opt_val": "a,2,True", "opt_result": ["a", 2, True]},
        {"opt_val": "b,1 + 5j,True", "opt_result": ["b", 1 + 5j, True]},
        {"opt_val": "1", "opt_result": 1},
        {"opt_val": "1.5", "opt_result": 1.5},
        {"opt_val": "1+5j", "opt_result": 1 + 5j},
        {"opt_val": "False", "opt_result": False},
        {"opt_val": "Test", "opt_result": "Test"},
    ]
    test_parameters.extend(basic_tests)
    # multiline
    ml = [
        {
            "opt_val": f"{c1["opt_val"]}\n{c2["opt_val"]}",
            "opt_result": [c1["opt_result"], c2["opt_result"]],
        }
        for c1, c2 in combinations(basic_tests, 2)
    ]
    test_parameters.extend(ml)

    # -----
    # further read parameter tests
    # -----
    # option delimiters and comment prefixes
    for opt_delim, comment_prefix in product(
        get_args(VALID_MARKERS), get_args(VALID_MARKERS)
    ):
        if opt_delim == comment_prefix:
            continue
        with (
            pytest.raises(ValueError) if opt_delim == comment_prefix else nullcontext()
        ):
            test_parameters.append(
                {
                    "opt_val": "1",
                    "opt_result": 1,
                    "write_parameters": Parameters(
                        option_delimiters=opt_delim, comment_prefixes=comment_prefix
                    ),
                    "read_parameters": Parameters(
                        option_delimiters=opt_delim, comment_prefixes=comment_prefix
                    ),
                }
            )
    # multiline disabled
    test_parameters.extend(
        pars
        | {
            "opt_result": pars["opt_result"][0],
            "read_parameters": Parameters(multiline_allowed=False),
            "read_context": multiline_warning,
        }
        for pars in ml
    )
    # multiline prefix
    test_parameters.extend(
        [
            pars
            | {
                "opt_val": pars["opt_val"].replace("\n", f"\n{pref}"),
                "write_parameters": Parameters(multiline_prefix=pref),
                "read_parameters": Parameters(multiline_prefix=pref),
            }
            for pars in ml
            for pref in [*get_args(VALID_MARKERS), "\t"]
            if pref not in {"=", ";"}
        ]
    )
    # multiline ignore
    test_parameters.extend(
        [
            # section_name
            {
                "opt_val": "next line should not be\n[a section name]",
                "opt_result": "next line should not be",
                "read_context": undefined_section_warning,
            },
            {
                "opt_val": "next line should not be\n[a section name]\nopt=1",
                "opt_result": "next line should not be",
                "read_parameters": Parameters(read_undefined="section"),
                "further": lambda sch, sec, opt, com: getattr(
                    getattr(sch, _str_to_var("a section name")), "opt"
                )
                == 1,
            },
            {
                "opt_val": "next line should not be\n[a section name]",
                "opt_result": ["next line should not be", "[a section name]"],
                "read_parameters": Parameters(multiline_ignore=("section_name",)),
            },
            # option_delimiter
            {
                "opt_val": "1+1 should\n be = 2",
                "opt_result": "1+1 should",
                "read_context": undefined_option_warning,
            },
            {
                "opt_val": "1+1 should\n be = 2",
                "opt_result": "1+1 should",
                "read_parameters": Parameters(read_undefined="option"),
                "further": lambda sch, sec, opt, com: Base.option_is_result(
                    sch, sec, "be", 2
                ),
            },
            {
                "opt_val": "1+1 should\n be = 2",
                "opt_result": ["1+1 should", " be = 2"],
                "read_parameters": Parameters(multiline_ignore=("option_delimiter",)),
            },
            # comment prefix
            {
                "opt_val": "this is not\n;a comment",
                "opt_result": "this is not",
                "further": lambda sch, sec, opt, com: getattr(
                    getattr(sch, sec), "get_comments_by_content"
                )("a comment"),
            },
            {
                "opt_val": "this is not\n;a comment",
                "opt_result": ["this is not", ";a comment"],
                "read_parameters": Parameters(multiline_ignore=("comment_prefix",)),
            },
        ]
    )
    # read_undefined
    test_parameters.extend(
        [
            # ----------
            # False
            # ----------
            # defined option+section
            {
                "opt_val": "1",
                "opt_result": 1,
                "read_parameters": Parameters(read_undefined=False),
            },
            # undefined section+option
            {
                "opt_val": "1",
                "opt_result": 1,
                "section": "undef",
                "read_parameters": Parameters(read_undefined=False),
                "read_context": undefined_section_warning,
                "option_access_context": attribute_error,
                "comment_access_context": attribute_error,
            },
            # undefined option
            {
                "opt_val": "1",
                "opt_result": 1,
                "option": "undef",
                "read_parameters": Parameters(read_undefined=False),
                "read_context": undefined_option_warning,
                "option_access_context": attribute_error,
            },
            # ----------
            # "section"
            # ----------
            # defined option+section
            {
                "opt_val": "1",
                "opt_result": 1,
                "read_parameters": Parameters(read_undefined="section"),
            },
            # undefined section+option
            {
                "opt_val": "1",
                "opt_result": 1,
                "section": "undef",
                "read_parameters": Parameters(read_undefined="section"),
            },
            # undefined option
            {
                "opt_val": "1",
                "opt_result": 1,
                "option": "undef",
                "read_parameters": Parameters(read_undefined="section"),
                "read_context": undefined_option_warning,
                "option_access_context": attribute_error,
            },
            # ----------
            # "option"
            # ----------
            # defined option+section
            {
                "opt_val": "1",
                "opt_result": 1,
                "read_parameters": Parameters(read_undefined="option"),
            },
            # undefined section+option
            {
                "opt_val": "1",
                "opt_result": 1,
                "section": "undef",
                "read_parameters": Parameters(read_undefined="option"),
                "read_context": undefined_section_warning,
                "option_access_context": attribute_error,
                "comment_access_context": attribute_error,
            },
            # undefined option„
            {
                "opt_val": "1",
                "opt_result": 1,
                "option": "undef",
                "read_parameters": Parameters(read_undefined="option"),
            },
        ]
    )
    # ignore_whitespace_lines
    test_parameters.extend(
        [
            # True
            {
                "opt_val": "1\n          \nopt=2",
                "opt_result": 1,
                "read_parameters": Parameters(read_undefined=True),
                "further": lambda sch, sec, opt, com: getattr(getattr(sch, sec), "opt")
                == 2,
            },
            # False
            {
                "opt_val": "1\n          \nopt=2",
                "opt_result": [1, "          "],
                "read_parameters": Parameters(
                    read_undefined=True, ignore_whitespace_lines=False
                ),
                "further": lambda sch, sec, opt, com: getattr(getattr(sch, sec), "opt")
                == 2,
            },
            {
                "opt_val": "1\n          \nopt=2",
                "opt_result": [1, "          ", "opt=2"],
                "read_parameters": Parameters(
                    read_undefined=True,
                    ignore_whitespace_lines=False,
                    multiline_ignore=("option_delimiter",),
                ),
            },
        ]
    )

    # ----------
    # type converters
    # ----------
    # string type converter
    test_parameters.extend(
        pars
        | {
            "opt_result": (
                pars["opt_val"].split("\n")
                if "\n" in pars["opt_val"]
                else pars["opt_val"]
            ),
            "read_parameters": Parameters(default_type_converter=None),
        }
        for pars in (*basic_tests, *ml)
    )

    # ----------
    # Actual test
    # ----------

    @pytest.mark.parametrize(
        *Base.create_parametrization(
            Base.test_read_and_access, parameters=test_parameters
        )
    )
    def test_read_and_access(
        self,
        opt_val,
        opt_result,
        tmp_path_factory,
        section,
        option,
        read_context,
        option_access_context,
        comment_access_context,
        read_parameters,
        write_parameters,
        further,
    ):
        Base().test_read_and_access(
            opt_val,
            opt_result,
            tmp_path_factory.getbasetemp(),
            section,
            option,
            read_context,
            option_access_context,
            comment_access_context,
            read_parameters,
            write_parameters,
            further,
        )
