# Setup the Meson Project
project('llnl-hatchet', 'cython',
    version: '2024.1.1'
)

# Get the Meson Python object, a dependency object to Python for extension modules,
# and the path to the top-level install directory
py = import('python').find_installation(required: true, pure: false)
py_dep = py.dependency(method: 'system')
py_top_install_dir = py.get_install_dir()

# Verify that the version from version.py matches the Meson project version
version_run = run_command(py.path(), meson.current_source_dir() / 'hatchet' / 'util' / 'print_version.py', check: true)
if version_run.returncode() != 0
    error('The __version__ variable in Hatchet cannot be determined')
endif
version_from_py = version_run.stdout().strip()
if not version_from_py.version_compare(meson.project_version())
    error('The __version__ variable in Hatchet does not match the Meson project version')
endif

# Enter the 'hatchet' subdirectory
subdir('hatchet')