"""Unit tests for internal helper functions in the optional-dependencies plugin."""

from pytest_optional_dependencies.plugin import (
    _get_optional_missing_module,
    _extract_missing_module_name,
    _normalize_module_names,
    pytest_addoption,
)


def test_extract_missing_module_name_no_prefix():
    """Line 28: return None when 'No module named' is not in the text."""
    assert _extract_missing_module_name("SomeOtherError: something went wrong") is None


def test_extract_missing_module_name_empty_after_prefix():
    """Line 32: return None when nothing follows 'No module named '."""
    assert _extract_missing_module_name("No module named ") is None


def test_extract_missing_module_name_unquoted():
    """Line 41: return None when the module name is not quoted."""
    assert _extract_missing_module_name("No module named bad_module") is None


def test_extract_missing_module_name_empty_quoted():
    """Cover the branch where quotes exist but no module name is inside them."""
    assert _extract_missing_module_name("No module named ''") is None


def test_extract_missing_module_name_single_quoted():
    """Happy path: single-quoted module name is extracted correctly."""
    assert _extract_missing_module_name("No module named 'bad_module'") == "bad_module"


def test_extract_missing_module_name_double_quoted():
    """Happy path: double-quoted module name is extracted correctly."""
    assert _extract_missing_module_name('No module named "bad_module"') == "bad_module"


def test_normalize_module_names_empty_string():
    """Line 59: empty string values are skipped (continue branch)."""
    result = _normalize_module_names(["", "good_module"])
    assert result == {"good_module"}


def test_normalize_module_names_trailing_comma():
    """Line 62->60: parts that strip to empty string are skipped."""
    result = _normalize_module_names(["good_module,"])
    assert result == {"good_module"}


def test_normalize_module_names_comma_only():
    """Both empty-value and empty-part branches: comma-only value."""
    result = _normalize_module_names([","])
    assert result == set()


def test_get_optional_missing_module_returns_none_when_name_not_extracted():
    """Line 90: return None when ImportError text has no extractable module name."""

    class Report:
        failed = True
        longreprtext = "ImportError: cannot import name something"

    class Config:
        stash = {}

    assert _get_optional_missing_module(Report(), Config()) is None


def test_pytest_addoption_skips_shared_report_option_when_already_added():
    """Line 199->exit: guard prevents adding duplicate --report option."""

    class Group:
        def __init__(self):
            self.options = []

        def addoption(self, *args, **kwargs):
            self.options.append((args, kwargs))

    class Parser:
        def __init__(self):
            self._pytest_optional_dependencies_report_option_added = True
            self.ini = []
            self.group = Group()

        def getgroup(self, _name):
            return self.group

        def addini(self, *args, **kwargs):
            self.ini.append((args, kwargs))

    parser = Parser()
    pytest_addoption(parser)

    added_option_names = [opt_args[0] for (opt_args, _kwargs) in parser.group.options]
    assert "--report-optional-dependencies" not in added_option_names
