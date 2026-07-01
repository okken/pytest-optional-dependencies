## Example test files for pytest-optional-dependencies

Run from this folder so pytest picks this pyproject.toml:

```bash
cd examples
```

- pyproject.toml
  - sets optional_dependencies = ["missing_dependency", "vendor_only_package"]
  - sets optional_dependencies_any = false
  - defaults optional missing imports to skip reporting behavior.

- test_bad_dependency.py
  - imports bad_dependency.
  - default behavior is a collection error.
  - use --optional-dependency bad_dependency to skip collection for the file.

- test_optional_dependency.py
  - imports missing_dependency.
  - because missing_dependency is listed as optional in config, it is reported as skipped and no collection error is raised.

- test_simple.py
  - ordinary passing test for baseline behavior.

Use --report-optional-dependencies to print optional-dependency policy and per-file skip reasons.
Use --optional-dependencies-action deselect to override the default and hide optional missing imports from skip counts.
