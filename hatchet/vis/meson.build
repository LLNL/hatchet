# Specify the pure Python files for this directory
hatchet_vis_python_sources = [
    '__init__.py',
    'loader.py',
    'static_fixer.py'
]

# Install the specified pure Python files into 
# <INSTALL_PREFIX>/hatchet/vis
py.install_sources(
    hatchet_vis_python_sources,
    pure: false,
    subdir: 'hatchet' / 'vis'
)

# Install directory for this source directory
hatchet_vis_install_dir = py_top_install_dir / 'hatchet' / 'vis'

# Install all the subdirectories for visualization code as-is
# into hatchet_vis_install_dir
install_subdir(
    'external',
    install_dir: hatchet_vis_install_dir
)
install_subdir(
    'scripts',
    install_dir: hatchet_vis_install_dir
)
install_subdir(
    'static',
    install_dir: hatchet_vis_install_dir
)
install_subdir(
    'styles',
    install_dir: hatchet_vis_install_dir
)
install_subdir(
    'templates',
    install_dir: hatchet_vis_install_dir
)

# Install the following non-Python files as-is
# into hatchet_vis_install_dir
install_data(
    'package.json', 'README.md', 'requirements.txt', 'webpack.config.js',
    install_dir: hatchet_vis_install_dir
)