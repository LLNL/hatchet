# Specify the pure Python files for this directory
hatchet_writers_python_sources = [
    '__init__.py',
    'dataframe_writer.py',
    'hdf5_writer.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet/writers
py.install_sources(
    hatchet_writers_python_sources,
    pure: false,
    subdir: 'hatchet' / 'writers'
)