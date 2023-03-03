# pyproject.toml

```
[project]
name = "my_project"

version = "0.1"

dependencies = [
    "my_package",
    "other_package>=1,<2",
    ...
]

client_dependencies = [
    "my_package",
    "other_package>=1,<2",
    ...
]

[tool.brickie]

entry = "<module>:<component class>"

client_directories = ["client"]

npm_packages = [
    'npm_module_a@version',
    'npm_module_b',
    '@org/npm_module_c@version',
    '@org/npm_module_d',
    ...
]

umd_packages = [
    "https://...",
    ...
]

styles = [
    "https://...",
    ...
]
```
