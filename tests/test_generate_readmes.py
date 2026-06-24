"""Tests for the generate_readmes.py tools module."""

import sys
from pathlib import Path

import pytest

# Add tools directory to path so we can import generate_readmes
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from generate_readmes import (  # noqa: E402
    EvalInfo,
    TaskInfo,
    _clean_default_value,
    _format_parameter,
    _format_type_annotation,
    _parse_docstring_parameters,
    generate_basic_readme,
    readme_exists,
)


class TestParseDocstringParameters:
    def test_single_line(self) -> None:
        docstring = """
    Args:
        param1: This is a simple description
        param2: Another simple description
    """
        result = _parse_docstring_parameters(docstring)
        assert result == {
            "param1": "This is a simple description",
            "param2": "Another simple description",
        }

    def test_multiline_with_bullets(self) -> None:
        docstring = """
    Args:
        scenario: The action the model takes. Options are:
            - "blackmail": Tests if agent will use sensitive information
            - "leaking": Tests if agent will leak confidential information

        goal_type: The type of goal conflict
    """
        result = _parse_docstring_parameters(docstring)
        assert len(result) == 2
        assert result["scenario"] == (
            "The action the model takes. Options are: "
            '"blackmail": Tests if agent will use sensitive information, '
            '"leaking": Tests if agent will leak confidential information'
        )
        assert result["goal_type"] == "The type of goal conflict"

    def test_multiline_continuation(self) -> None:
        docstring = """
    Args:
        param1: This is a description that continues
            on multiple lines with consistent
            indentation throughout.
        param2: Another param
    """
        result = _parse_docstring_parameters(docstring)
        assert len(result) == 2
        assert (
            result["param1"]
            == "This is a description that continues on multiple lines with consistent indentation throughout."
        )

    def test_empty_args(self) -> None:
        docstring = """
    This is a function description.

    Returns:
        Something
    """
        assert _parse_docstring_parameters(docstring) == {}

    def test_with_type_annotations(self) -> None:
        docstring = """
    Args:
        param1 (str): Description one
        param2 (int): Description two with
            multiple lines
    """
        result = _parse_docstring_parameters(docstring)
        assert len(result) == 2
        assert result["param1"] == "Description one"
        assert result["param2"] == "Description two with multiple lines"

    def test_continuation_line_with_colon_not_treated_as_param(self) -> None:
        docstring = """
    Args:
        languages: Optional language filter.
                   Supported: python, cpp, java.
        count: Number of items
    """
        result = _parse_docstring_parameters(docstring)
        assert len(result) == 2
        assert "Supported" not in result
        assert "Supported:" in result["languages"]


class TestFormatParameter:
    def test_removes_default_colon(self) -> None:
        param = {
            "name": "max_attempts",
            "type_str": "int",
            "description": "Maximum attempts (default: 1)",
            "default": "1",
        }
        result = _format_parameter(param)
        assert result == "- `max_attempts` (int): Maximum attempts (default: `1`)"

    def test_removes_defaults_to(self) -> None:
        param = {
            "name": "max_attempts",
            "type_str": "int",
            "description": "Maximum attempts (defaults to 1)",
            "default": "1",
        }
        result = _format_parameter(param)
        assert "(defaults to 1)" not in result
        assert result.endswith("(default: `1`)")

    def test_removes_defaults_to_with_period(self) -> None:
        param = {
            "name": "max_attempts",
            "type_str": "int",
            "description": "Maximum attempts. Defaults to 1.",
            "default": "1",
        }
        result = _format_parameter(param)
        assert "Defaults to 1" not in result
        assert result.endswith("(default: `1`)")

    def test_no_default(self) -> None:
        param = {
            "name": "solver",
            "type_str": "Solver | None",
            "description": "Optional solver to use",
            "default": None,
        }
        result = _format_parameter(param)
        assert result == "- `solver` (Solver | None): Optional solver to use"

    def test_without_description(self) -> None:
        param = {
            "name": "kwargs",
            "type_str": "Any",
            "description": "",
            "default": None,
        }
        assert _format_parameter(param) == "- `kwargs` (Any):"

    def test_without_type(self) -> None:
        param = {
            "name": "solver",
            "type_str": None,
            "description": "Optional solver to use",
            "default": "None",
        }
        assert (
            _format_parameter(param)
            == "- `solver`: Optional solver to use (default: `None`)"
        )


class TestFormatTypeAnnotation:
    def test_simple_types(self) -> None:
        assert _format_type_annotation(int) == "int"
        assert _format_type_annotation(str) == "str"
        assert _format_type_annotation(bool) == "bool"

    def test_pipe_union_types(self) -> None:
        result = _format_type_annotation(int | None)
        assert result is not None
        assert "int" in result
        assert "None" in result

    def test_none_type_cleaned(self) -> None:
        result = _format_type_annotation(str | int | None)
        assert result is not None
        assert "None" in result
        assert "NoneType" not in result

    def test_complex_types(self) -> None:
        result = _format_type_annotation(list[str])
        assert result is not None
        assert "list[str]" in result

    def test_no_annotation(self) -> None:
        import inspect

        assert _format_type_annotation(inspect.Parameter.empty) is None


class TestCleanDefaultValue:
    def test_callable(self) -> None:
        def my_function() -> None:
            pass

        assert _clean_default_value(my_function) == "my_function"

    def test_simple_values(self) -> None:
        assert _clean_default_value(42) == "42"
        assert _clean_default_value("hello") == "'hello'"
        assert _clean_default_value(True) == "True"
        assert _clean_default_value(None) == "None"


class TestGenerateBasicReadme:
    def test_generates_skeleton(self) -> None:
        info = EvalInfo(
            title="My Eval",
            description="Test description",
            path="src/my_eval",
            group="Coding",
            contributors=["test"],
            tasks=[TaskInfo(name="my_task", dataset_samples=42)],
            version="1-A",
        )

        result = generate_basic_readme(info)
        text = "\n".join(result)

        assert "# My Eval" in text
        assert "<!-- Contributors: Automatically Generated -->" in text
        assert "<!-- Usage: Automatically Generated -->" in text
        assert "<!-- Options: Automatically Generated -->" in text
        assert "<!-- Parameters: Automatically Generated -->" in text
        assert "## Dataset" in text
        assert "## Scoring" in text
        assert "## Evaluation Report" in text
        assert "## Changelog" in text


class TestReadmeExists:
    def test_existing_example(self) -> None:
        info = EvalInfo(
            title="GPQA",
            description="",
            path="src/examples/gpqa",
            group="Knowledge",
            contributors=[],
            tasks=[],
            version="1-A",
        )
        assert readme_exists(info) is True

    def test_nonexistent(self) -> None:
        info = EvalInfo(
            title="Nonexistent",
            description="",
            path="src/nonexistent_eval_xyz",
            group="",
            contributors=[],
            tasks=[],
            version="1-A",
        )
        assert readme_exists(info) is False


class TestBuildParametersSection:
    @pytest.mark.dataset_download
    def test_gpqa_parameters(self) -> None:
        """Test parameter extraction from the GPQA example task."""
        from generate_readmes import build_parameters_section  # noqa: E402

        info = EvalInfo(
            title="GPQA",
            description="",
            path="src/examples/gpqa",
            group="Knowledge",
            contributors=["jjallaire"],
            tasks=[TaskInfo(name="gpqa_diamond", dataset_samples=198)],
            version="1-A",
        )

        result = build_parameters_section(info)
        text = "\n".join(result)

        assert "## Parameters" in text
        assert "`cot`" in text
        assert "`epochs`" in text
        assert "`high_level_domain`" in text
        assert "`subdomain`" in text
