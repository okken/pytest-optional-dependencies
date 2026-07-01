"""
pytest-optional-dependencies: Handle missing imports gracefully during test collection.

This plugin allows tests to be skipped or deselected if they fail collection due to
missing optional dependency imports. This is useful when a package has optional extras
that may not be installed in all test environments.
"""

import pytest


# Use pytest's StashKey for thread-safe storage of plugin state
FILTER_EVENTS_KEY = pytest.StashKey[list[str]]()
ACCEPTABLE_MISSING_MODULES_KEY = pytest.StashKey[set[str]]()
OPTIONAL_DEPENDENCIES_ANY_KEY = pytest.StashKey[bool]()
OPTIONAL_DEPENDENCIES_ACTION_KEY = pytest.StashKey[str]()


class _DeselectedCollectorNode:
    """Minimal object for pytest_deselected accounting."""

    def __init__(self, nodeid):
        self.nodeid = nodeid


def _extract_missing_module_name(longrepr_text):
    """Extract the module name from a ModuleNotFoundError/ImportError message.

    Why: pytest's longreprtext contains the full error traceback. We need to parse
    the specific error message to extract just the missing module name. The error
    message format is: "No module named 'module.name'" with either single or double
    quotes depending on Python version and context.
    """
    no_module_prefix = "No module named "
    if no_module_prefix not in longrepr_text:
        return None

    missing_part = longrepr_text.split(no_module_prefix, 1)[1].strip()
    if not missing_part:
        return None

    # Extract the quoted module name. The quote character (single or double) indicates
    # where the module name begins, and we find the closing quote.
    quote = missing_part[0]
    if quote in {'"', "'"}:
        end_idx = missing_part.find(quote, 1)
        if end_idx > 1:
            return missing_part[1:end_idx]
    return None


def _normalize_module_names(raw_values):
    """Convert raw config values into a normalized set of module names.

    Why: Config values can come from either CLI (--optional-dependency flag, can be
    repeated) or ini file (comma-separated lists). We need to handle both formats
    uniformly. CLI passes a list, ini passes strings. This function flattens them
    and handles comma-separated values so users can write either:
      optional_dependencies = numpy,scipy
      optional_dependencies = numpy
                              scipy
    in their ini file, or use --optional-dependency multiple times on the CLI.
    """
    modules = set()
    for value in raw_values:
        if not value:
            continue
        for part in str(value).split(","):
            module = part.strip()
            if module:
                modules.add(module)
    return modules


def _get_optional_missing_module(report, config):
    """Check if a collection failure is due to an optional missing import.

    Why this function exists: During collection, if a test module imports an optional
    dependency that's not installed, the entire test collection fails. We need to:
    1. Detect if the failure was actually due to a missing import (not another error)
    2. Extract which module was missing
    3. Check if that module is in our list of acceptable-to-skip missing modules

    Returns: The missing module name if it's an optional dependency we should skip,
    or None if this failure shouldn't be handled by this plugin.
    """
    if not report.failed:
        return None

    longrepr_text = getattr(report, "longreprtext", "")
    # Check for ModuleNotFoundError or ImportError - only then is a missing module
    # the root cause. Other import errors (syntax errors, etc.) shouldn't be skipped.
    if (
        "ImportError" not in longrepr_text
        and "ModuleNotFoundError" not in longrepr_text
    ):
        return None

    missing_module = _extract_missing_module_name(longrepr_text)
    if not missing_module:
        return None

    # If optional_dependencies_any is set, skip ANY missing module import error.
    # This is useful for test environments where many optional deps might be missing.
    if config.stash.get(OPTIONAL_DEPENDENCIES_ANY_KEY, False):
        return missing_module

    # Treat submodules as acceptable if top-level package is listed.
    # Why: If user specifies "sklearn" as optional, they likely mean sklearn and all
    # its submodules (sklearn.ensemble, sklearn.preprocessing, etc.). Without this,
    # a test importing sklearn.ensemble would fail even if sklearn is listed.
    optional_dependencies = config.stash.get(ACCEPTABLE_MISSING_MODULES_KEY, set())
    top_level = missing_module.split(".", 1)[0]
    if missing_module in optional_dependencies or top_level in optional_dependencies:
        return missing_module
    return None


def _record_filter_event(config, message):
    """Record a filtering decision for the debug report if --report-optional-dependencies is set.

    Why: Users can pass --report-optional-dependencies to see which tests were skipped and why.
    This helps them verify the plugin is working as intended and debug any issues.
    """
    if config.getoption("report_optional_dependencies"):
        config.stash[FILTER_EVENTS_KEY].append(message)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_make_collect_report(collector):
    """Intercept collection failures and convert optional-dependency failures to skips/passes.

    Why tryfirst=True: We need to run before other plugins that might fail on import errors.
    Why hookwrapper=True: We need to intercept the report AFTER collection happens but BEFORE
    pytest processes it further. This allows us to change the outcome from "failed" to "skipped".
    """
    outcome = yield
    report = outcome.get_result()

    missing_module = _get_optional_missing_module(report, collector.config)
    if missing_module:
        action = collector.config.stash.get(OPTIONAL_DEPENDENCIES_ACTION_KEY, "skip")
        _record_filter_event(
            collector.config,
            f"{report.nodeid}: missing module '{missing_module}' is optional ({action})",
        )

        if action == "skip":
            # Mark as skipped so the test still appears in output (good for visibility)
            report.outcome = "skipped"
            report.longrepr = (
                str(collector.path),
                0,
                f"missing module '{missing_module}' is configured as optional",
            )
        else:
            # Deselect collection node so it is reflected in pytest deselected counts.
            collector.config.hook.pytest_deselected(
                items=[_DeselectedCollectorNode(report.nodeid)]
            )
            report.outcome = "passed"
            report.longrepr = None
        outcome.force_result(report)


def pytest_addoption(parser):
    """Register command-line and ini-file options for this plugin."""
    group = parser.getgroup("Optional dependencies")

    # CLI options for specifying optional dependencies (can be used multiple times)
    group.addoption(
        "--optional-dependency",
        action="append",
        default=[],
        metavar="MODULE",
        help="Treat a missing module as an optional dependency during collection",
    )
    group.addoption(
        "--optional-dependencies-any",
        action="store_true",
        default=False,
        help="Treat any missing-module import as optional during collection",
    )
    group.addoption(
        "--optional-dependencies-action",
        action="store",
        default=None,
        choices=("deselect", "skip"),
        help="How to report optional missing imports: skip (default) or deselect",
    )

    # Ini file options (alternative to CLI for permanent project configuration)
    parser.addini(
        "optional_dependencies",
        "Optional dependencies that may be missing during collection import",
        type="linelist",
        default=[],
    )
    parser.addini(
        "optional_dependencies_any",
        "If true, treat any missing-module import as optional during collection",
        type="bool",
        default=False,
    )
    parser.addini(
        "optional_dependencies_action",
        "How optional missing imports are reported: skip (default) or deselect",
        default="skip",
    )

    # Reporting option
    if not getattr(parser, "_pytest_optional_dependencies_report_option_added", False):
        group.addoption(
            "--report-optional-dependencies",
            action="store_true",
            default=False,
            help="Report optional-dependency collection decisions and their reasons",
        )
        parser._pytest_optional_dependencies_report_option_added = True


def pytest_configure(config):
    """Initialize plugin state at the start of the test session.

    Why: We need to prepare the config.stash with initial values before collection starts,
    and also parse/merge CLI options with ini file settings. CLI options have priority.
    """
    config.stash[FILTER_EVENTS_KEY] = []

    # Merge optional dependencies from both ini file and CLI (CLI takes precedence)
    configured_missing_imports = _normalize_module_names(
        config.getini("optional_dependencies")
    )
    cli_missing_imports = _normalize_module_names(
        config.getoption("optional_dependency")
    )
    config.stash[ACCEPTABLE_MISSING_MODULES_KEY] = (
        configured_missing_imports | cli_missing_imports
    )

    # Set the "treat any missing import" flag if either CLI or ini is enabled
    config.stash[OPTIONAL_DEPENDENCIES_ANY_KEY] = bool(
        config.getini("optional_dependencies_any")
    ) or bool(config.getoption("optional_dependencies_any"))

    # Determine action (skip or deselect) - CLI takes precedence over ini file
    action = config.getoption("optional_dependencies_action") or config.getini(
        "optional_dependencies_action"
    )
    if action not in {"deselect", "skip"}:
        raise pytest.UsageError(
            "optional_dependencies_action must be either 'deselect' or 'skip'"
        )
    config.stash[OPTIONAL_DEPENDENCIES_ACTION_KEY] = action


def pytest_collection_finish(session):
    """Print debug report about optional dependencies if --report-optional-dependencies was set.

    Why: Users need visibility into what the plugin did. This report shows the configured
    policy and a log of every collection decision made, helping them debug issues.
    """
    config = session.config
    if not config.getoption("report_optional_dependencies"):
        return

    optional_dependencies_any = config.stash.get(OPTIONAL_DEPENDENCIES_ANY_KEY, False)
    optional_dependencies = sorted(
        config.stash.get(ACCEPTABLE_MISSING_MODULES_KEY, set())
    )
    action = config.stash.get(OPTIONAL_DEPENDENCIES_ACTION_KEY, "skip")

    print("optional dependency policy:")
    print(f"  optional dependencies any: {optional_dependencies_any}")
    print(f"  optional dependencies action: {action}")
    if optional_dependencies:
        print("  optional dependencies: " + ", ".join(optional_dependencies))
    else:
        print("  optional dependencies: (none)")

    events = config.stash.get(FILTER_EVENTS_KEY, [])
    print("optional dependency report:")
    if not events:
        print("  no optional imports were skipped")
        return

    for event in events:
        print(f"  - {event}")
