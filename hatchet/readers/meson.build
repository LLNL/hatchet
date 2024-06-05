# Specify the pure Python files for this directory
hatchet_readers_python_sources = [
    '__init__.py',
    'caliper_native_reader.py',
    'caliper_reader.py',
    'cprofile_reader.py',
    'dataframe_reader.py',
    'gprof_dot_reader.py',
    'hdf5_reader.py',
    'hpctoolkit_reader.py',
    'json_reader.py',
    'literal_reader.py',
    'pyinstrument_reader.py',
    'spotdb_reader.py',
    'tau_reader.py',
    'timemory_reader.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet/readers
py.install_sources(
    hatchet_readers_python_sources,
    pure: false,
    subdir: 'hatchet' / 'readers'
)