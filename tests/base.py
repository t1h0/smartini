from smartini import Schema, Section, Parameters
from smartini.utils import _str_to_var, OrderedDict
from typing import overload, Literal, Any, ContextManager, Callable
from contextlib import nullcontext
from uuid import uuid1
from pathlib import Path
import inspect
import re


class Base:
    """Base for tests. Provides functions for creating an ini content and a matching
    Schema definition."""

    def __init__(
        self, schema_id: str = "INI", write_parameters: Parameters = Parameters()
    ) -> None:
        """
        Args:
            schema_id (str, optional): The name for the Schema object. Defaults to "INI".
            parameters (Parameters, optional): Parameters for creating the ini content.
                Defaults to Parameters().
        """
        self.content: str = ""
        self.schema: type[Schema] = type(schema_id, (Schema,), {})
        self._write_parameters = self.markers_undo_escape(write_parameters)
        self.sections = OrderedDict()

    @property
    def write_parameters(self) -> Parameters:
        return self._write_parameters

    @write_parameters.setter
    def write_parameters(self, value: Parameters) -> None:
        self._write_parameters = self.markers_undo_escape(value)

    def markers_undo_escape(self, parameters: Parameters) -> Parameters:
        """Remove escape characters of escaped markers for writing.

        Args:
            parameters (Parameters): Write parameters.

        Returns:
            Parameters: The Parameters with escaped markers.
        """
        # undo re.escape
        for marker in ("option_delimiters", "comment_prefixes", "multiline_prefix"):
            attr = getattr(parameters, marker)
            if isinstance(attr, tuple | list):
                setattr(
                    parameters,
                    f"_{marker}",
                    tuple(re.sub(r"\\(.)", r"\1", a) for a in attr),
                )
            else:
                setattr(parameters, f"_{marker}", re.sub(r"\\(.)", r"\1", attr))
        return parameters

    def initialize(self) -> Schema:
        """Initialize the base Schema."""
        return self.schema(self.write_parameters)

    @classmethod
    def create_parametrization(
        cls, target: Callable, parameters: list[dict[str, Any]]
    ) -> tuple[str, list[tuple]]:
        """Create a pytest mark parametrization for a target function.

        Args:
            target (Callable): The target function to parametrize.
            parameters (list[dict[str, Any]]): Parameters to pass. One dict per
                parametrization with keys matching target arguments.

        Returns:
            tuple[str, list[tuple]]: Tuple of argnames and argvalues to pass to
                pytest.mark.parametrization.
        """

        args_to_pass = OrderedDict({"opt_val": "", "opt_result": ""})

        # get default args from target
        args_to_pass |= {
            k: v.default
            for k, v in inspect.signature(target).parameters.items()
            if v.default is not v.empty
        }

        parametrization: list[tuple] = []
        for pars in parameters:
            if {*pars.keys()}.difference(args_to_pass.keys()):
                # pytest.set_trace()
                raise ValueError(
                    "Parameters must be either read_parameters or function arguments."
                )
            parametrization.append(tuple((args_to_pass | pars).values()))

        # add parameters
        return ",".join(args_to_pass), parametrization

    @classmethod
    def option_is_result(
        cls, schema: Schema, sec_var: str, opt_var: str, opt_result: Any
    ) -> bool:
        """Check whether the value of Option 'opt_var' of Section 'sec_var' of
        Schema 'schema' equals 'opt_result'.

        Args:
            schema (Schema): The Schema to access.
            sec_var (str): The Section to access.
            opt_var (str): The Option to access.
            opt_result (Any): The result to compare.

        Returns:
            bool
        """
        return getattr(getattr(schema, sec_var), opt_var) == opt_result

    def test_read_and_access(
        self,
        opt_val: str,
        opt_result: Any,
        export_path: Path,
        section: Literal["def", "undef"] | None = None,
        option: Literal["def", "undef"] | None = None,
        read_context: ContextManager | None = None,
        option_access_context: ContextManager | None = None,
        comment_access_context: ContextManager | None = None,
        read_parameters: Parameters = Parameters(),
        write_parameters: Parameters = Parameters(),
        further: Callable[[Schema, str, str, str], bool] | None = None,
    ):
        """Create a test schema and test ini content and verify option value and comment
        content.

        Args:
            opt_val (str): The value the option should take inside the ini content.
            opt_result (Any): The value the option is expected to return.
            export_path (Path): The path to export the ini to.
            section (Literal["def", "undef"] | None, optional): Whether the Section
                should be defined or undefined. Defaults to "def".
            option (Literal["def", "undef"] | None, optional): Whether the Option
                should be defined or undefined. Defaults to "def".
            read_context (ContextManager | None, optional): The ContextManager for
                reading the ini. Defaults to nullcontext().
            option_access_context (ContextManager | None, optional): The ContextManager
                for accessing the option. Defaults to nullcontext().
            comment_access_context (ContextManager | None, optional): The ContextManager
                for accessing the comment. Defaults to nullcontext().
            read_parameters (Parameters, optional): Parameters for reading.
            write_parameters (Parameters, optional): Parameters for writing.
            further (Callable[[Schema, str, str, str], bool] | None, optional): A function
                that takes the schema, the section variable name, the option variable
                name and the comment content and returns a boolean. Will be asserted at
                the end if not None. Defaults to None.
        """
        self.write_parameters = write_parameters
        if section is None:
            section = "def"
        if option is None:
            option = "def"
        if read_context is None:
            read_context = nullcontext()
        if option_access_context is None:
            option_access_context = nullcontext()
        if comment_access_context is None:
            comment_access_context = nullcontext()

        if section == "def":
            sec_var, sec = self.add_defined_section()
            comment = self.add_comment()
            opt_var = (
                self.add_defined_option(sec, opt_val)
                if option == "def"
                else self.add_undefined_option(opt_val)
            )
        else:
            sec_var = self.add_undefined_section()
            comment = self.add_comment()
            opt_var = self.add_undefined_option(opt_val)

        read_path = self.export(export_path)

        schema = self.initialize()

        # pytest.set_trace()
        with read_context:
            schema.read_ini(read_path, parameters=read_parameters)
        with option_access_context:
            # if getattr(getattr(schema, sec_var), opt_var) != opt_result:
            #     breakpoint()
            assert self.option_is_result(schema, sec_var, opt_var, opt_result)
        with comment_access_context:
            # breakpoint()
            assert (
                tuple(
                    getattr(schema, sec_var).get_comments_by_content(comment).values()
                )[0].content
                == comment
            )
        if further:
            if not further(schema, sec_var, opt_var, comment):
                breakpoint()
            assert further(schema, sec_var, opt_var, comment)

    @classmethod
    def random_id(cls):
        """Create a random UUID1 with underscores instead of hyphens.

        Returns:
            _type_: The generated UUID1.
        """
        return str(uuid1()).replace("-", "_")

    def _add_option(self, value: str | None = None) -> tuple[str, str]:
        """Add an option to the content. Option will not be defined but registered in
        self.sections for the last section.

        Args:
            value (str | None, optional): The value the option should take.
                Defaults to None.

        Returns:
            tuple[str, str]: Variable name and ini option name.
        """
        if value is None:
            value = self.random_id()
        opt_id = self.random_id()
        access_id = _str_to_var(opt_id)
        self.sections.iloc[-1] = [*self.sections.iloc[-1], access_id]
        self.content += (
            f"\n{opt_id} {self.write_parameters.option_delimiters[0]} {value}"
        )
        return access_id, opt_id

    @overload
    def _add_section(self, define: Literal[False]) -> str: ...
    @overload
    def _add_section(self, define: Literal[True]) -> tuple[str, type[Section]]: ...
    def _add_section(self, define: bool) -> tuple[str, type[Section]] | str:
        """Add a section.

        Args:
            define (bool): Whether to define the section.

        Returns:
            tuple[str, type[Section]] | str: Section variable name and Section object if
                define else only section variable name.
        """
        sec_id = self.random_id()
        self.content += f"[{sec_id}]"
        access_id = _str_to_var(sec_id)
        self.sections[access_id] = []
        if define:
            sec = type(sec_id, (Section,), {})
            sec._name = sec_id
            setattr(self.schema, access_id, sec)
            return access_id, sec
        return access_id

    def add_defined_section(self) -> tuple[str, type[Section]]:
        """Add a defined section."""
        return self._add_section(True)

    def add_undefined_section(self) -> str:
        """Add an undefined section."""
        return self._add_section(False)

    def add_defined_option(
        self,
        section: type[Section] | None,
        value: str | None = None,
        annotation: type | None = None,
    ) -> str:
        """Add a defined option.

        Args:
            section (type[Section] | None): The section to add the option to.
            value (str | None, optional): The value the option should take. If None
                will generate an UUID4 as value. Defaults to None.
            annotation (type | None, optional): The type annotation the option
                should get. Defaults to None.

        Returns:
            str: The option's variable name.
        """
        access_id, opt_id = self._add_option(value)
        setattr(section, access_id, opt_id)
        if annotation is not None:
            section.__annotations__[access_id] = annotation
        return access_id

    def add_undefined_option(self, value: str | None = None) -> str:
        """Add an undefined option.

        Args:
            value (str | None, optional): The value the option should take. If None
                will generate an UUID4 as value. Defaults to None.

        Returns:
            str: The option's variable name.
        """
        return self._add_option(value)[0]

    def add_comment(self) -> str:
        """Add a comment."""
        comment = self.random_id()
        self.content += f"\n{f"{self.write_parameters.comment_prefixes[0]} " if self.write_parameters.comment_prefixes else ""}{comment}"
        return comment

    def add_invalid_entity(self) -> None:
        """Add an invalid entity."""
        self.content += f"\n{self.random_id}"

    def export(self, path: Path) -> Path:
        """Export the generated ini content.

        Args:
            path (Path): The path to export to.

        Returns:
            Path: The export path.
        """
        dest = path / f"{self.random_id()}.ini"
        with open(dest, "w") as f:
            f.write(self.content)
        return dest
