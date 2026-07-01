import textwrap


def test_missing_is_error_with_no_flag(pytester):
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest("-v")
    result.stdout.fnmatch_lines(
        [
            "E   ModuleNotFoundError: No module named 'bad_dependency'*",
        ]
    )
    result.assert_outcomes(errors=1)
    assert result.ret == 2


def test_missing_is_not_collected_with_flag(pytester):
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest(
        "-v",
        "--optional-dependency",
        "bad_dependency",
    )
    result.stdout.fnmatch_lines(
        [
            "*collected 1 item / 1 skipped*",
            "test_simple.py::test_simple PASSED*",
        ]
    )
    result.assert_outcomes(passed=1, skipped=1)
    assert result.ret == 0


def test_only_optional_missing_module_is_skipped_by_default(pytester):
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest(
        "-v",
        "--optional-dependency",
        "bad_dependency",
    )
    result.assert_outcomes(skipped=1)
    assert result.ret == 5


def test_report(pytester):
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest(
        "-q",
        "--optional-dependency",
        "bad_dependency",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(
        [
            "optional dependency policy:",
            "  optional dependencies any: False",
            "  optional dependencies action: skip",
            "*optional dependencies:*bad_dependency*",
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (skip)",
        ]
    )


def test_report_any(pytester):
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest(
        "-q",
        "--optional-dependencies-any",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(
        [
            "optional dependency policy:",
            "  optional dependencies any: True",
            "  optional dependencies action: skip",
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (skip)",
        ]
    )


def test_ini_optional_dependencies_any(pytester):
    pytester.copy_example("test_bad_dependency.py")
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies_any = true
    """)
    )

    result = pytester.runpytest()
    result.assert_outcomes(skipped=1)
    assert result.ret == 5


def test_ini_optional_dependency(pytester):
    pytester.copy_example("test_bad_dependency.py")
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies = ["bad_dependency"]
    """)
    )

    result = pytester.runpytest(
        "-q",
        "--report-optional-dependencies",
    )
    result.assert_outcomes(skipped=1)
    assert result.ret == 5


def test_multiple_optional_dependencies_via_cli(pytester):
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")
    pytester.copy_example("test_optional_dependency.py")

    result = pytester.runpytest(
        "-v",
        "--optional-dependency",
        "bad_dependency",
        "--optional-dependency",
        "missing_dependency",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(
        [
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (skip)",
            "*test_optional_dependency.py: missing module 'missing_dependency' is optional (skip)",
        ]
    )
    assert result.ret == 0
    result.assert_outcomes(passed=1, skipped=2)


def test_multiple_optional_dependencies_via_ini(pytester):
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies = [
            "missing_dependency",
            "bad_dependency",
        ]
    """)
    )
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")
    pytester.copy_example("test_optional_dependency.py")

    result = pytester.runpytest(
        "-v",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(
        [
            "*collected 1 item / 2 skipped*",
            "*optional dependencies:*bad_dependency*missing_dependency*",
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (skip)",
            "*test_optional_dependency.py: missing module 'missing_dependency' is optional (skip)",
        ]
    )
    assert result.ret == 0
    result.assert_outcomes(passed=1, skipped=2)


def test_action_deselect_via_cli_reports_deselected(pytester):
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")

    result = pytester.runpytest(
        "-q",
        "--optional-dependency",
        "bad_dependency",
        "--optional-dependencies-action",
        "deselect",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(
        [
            "optional dependency policy:",
            "  optional dependencies action: deselect",
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (deselect)",
        ]
    )
    result.assert_outcomes(passed=1, deselected=1)


def test_report_with_no_skips(pytester):
    """Exercise the 'no optional imports were skipped' path in pytest_collection_finish."""
    pytester.copy_example("test_simple.py")

    result = pytester.runpytest(
        "-q",
        "--optional-dependency",
        "bad_dependency",
        "--report-optional-dependencies",
    )
    result.stdout.fnmatch_lines(["*no optional imports were skipped*"])
    result.assert_outcomes(passed=1)


def test_invalid_action_raises_usage_error(pytester):
    """Exercise the UsageError for invalid optional_dependencies_action value."""
    pytester.copy_example("test_simple.py")
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies_action = "invalid"
    """)
    )

    result = pytester.runpytest("-q")
    result.stderr.fnmatch_lines(
        ["*optional_dependencies_action must be either 'deselect' or 'skip'*"]
    )
    assert result.ret != 0


def test_non_import_error_is_not_skipped(pytester):
    """Exercise the path where the collection error is not an ImportError."""
    pytester.makepyfile(
        textwrap.dedent("""
        raise ValueError("not an import error")

        def test_something():
            pass
    """)
    )

    result = pytester.runpytest("-q", "--optional-dependencies-any")
    result.assert_outcomes(errors=1)


def test_normalize_empty_and_comma_values(pytester):
    """Exercise _normalize_module_names with empty/trailing-comma values."""
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies = ["bad_dependency,", ","]
    """)
    )

    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1, skipped=1)


def test_action_deselect_via_ini_reports_deselected(pytester):
    pytester.copy_example("test_simple.py")
    pytester.copy_example("test_bad_dependency.py")
    pytester.makepyprojecttoml(
        textwrap.dedent("""
        [tool.pytest.ini_options]
        optional_dependencies = ["bad_dependency"]
        optional_dependencies_action = "deselect"
    """)
    )

    result = pytester.runpytest("-q", "--report-optional-dependencies")
    result.stdout.fnmatch_lines(
        [
            "*optional dependencies action: deselect*",
            "*test_bad_dependency.py: missing module 'bad_dependency' is optional (deselect)",
        ]
    )
    result.assert_outcomes(passed=1, deselected=1)
