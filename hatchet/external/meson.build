# Specify the pure Python files for this directory
hatchet_external_python_sources = [
    '__init__.py',
    'console.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet/external
py.install_sources(
    hatchet_external_python_sources,
    pure: false,
    subdir: 'hatchet' / 'external'
)

# Install roundtrip as-is into
# <INSTALL_PREFIX>/hatchet/external
install_subdir(
    'roundtrip',
    install_dir: py_top_install_dir / 'hatchet' / 'external'
)