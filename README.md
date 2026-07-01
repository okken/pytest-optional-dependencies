# pytest-optional-dependencies

Don't test code that won't load due to missing imports. 
A pytest plugin to skip tests that require optional dependencies that are not installed.

Collection-time optional dependency handling for pytest.

This plugin allows specific missing imports to be treated as optional so collection can continue without errors.

## Features

* --optional-dependency MODULE (repeatable, also accepts comma-separated values).
    * specify which dependencies to skip/deselect based on their absence
* --optional-dependencies-any 
    * to treat any missing module import as optional.
* --optional-dependencies-action 
    * to control optional import handling: skip (default) or deselect.
* Configuration options
  * optional_dependencies 
  * optional_dependencies_any 
  * optional_dependencies_action 
* --report-optional-dependencies
    * Report what was filtered and why.

## Install

```bash
uv pip install pytest-optional-dependencies
```

Or with pip:

```bash
python -m pip install pytest-optional-dependencies
```

## Compatibility

- Python: 3.10+
- pytest: 8.0+

## CLI options

- --optional-dependency MODULE
- --optional-dependencies-any
- --optional-dependencies-action {deselect,skip}
- --report-optional-dependencies

## Configuration

pytest.ini:

```ini
[pytest]
optional_dependencies =
    optional_dependency
    some_namespace.submodule
optional_dependencies_any = false
optional_dependencies_action = skip
```

pyproject.toml:

```toml
[tool.pytest.ini_options]
optional_dependencies = [
  "optional_dependency",
  "some_namespace.submodule",
]
optional_dependencies_any = false
optional_dependencies_action = "skip"
```

## Example

```bash
pytest -q --optional-dependency optional_dependency --report-optional-dependencies
pytest -q --optional-dependency optional_dependency --optional-dependencies-action skip
```

## Development

```bash
python -m pytest -q
```

## License

MIT. See LICENSE.
