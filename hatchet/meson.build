# Specify the pure Python files for this directory
hatchet_python_sources = [
    '__init__.py',
    'frame.py',
    'graph.py',
    'graphframe.py',
    'node.py',
    'version.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet
py.install_sources(
    hatchet_python_sources,
    pure: false,
    subdir: 'hatchet'
)

# Go through all the subdirectories except for 'test'
subdir('cython_modules')
subdir('external')
subdir('query')
subdir('readers')
subdir('util')
subdir('vis')
subdir('writers')