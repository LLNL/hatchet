# Specify the pure Python files for this directory
# Note: don't include 'print_version.py' because
#       that file is not needed in binary distributions
hatchet_util_python_sources = [
    '__init__.py',
    'colormaps.py',
    'config.py',
    'deprecated.py',
    'dot.py',
    'executable.py',
    'profiler.py',
    'timer.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet/util
py.install_sources(
    hatchet_util_python_sources,
    pure: false,
    subdir: 'hatchet' / 'util'
)