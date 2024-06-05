# Specify the pure Python files for this directory
hatchet_query_python_sources = [
    '__init__.py',
    'compat.py',
    'compound.py',
    'engine.py',
    'errors.py',
    'object_dialect.py',
    'query.py',
    'string_dialect.py'
]

# Install the specified pure Python files into
# <INSTALL_PREFIX>/hatchet/query
py.install_sources(
    hatchet_query_python_sources,
    pure: false,
    subdir: 'hatchet' / 'query'
)