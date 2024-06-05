# Specify the names of the Cython extension modules, excluding file extensions
cython_module_names = [
    'graphframe_modules',
    'reader_modules'
]

# Loop over the Cython modules and build/install them to
# <INSTALL_PREFIX>/hatchet/cython_modules/libs
foreach mod_name : cython_module_names
    py.extension_module(
        mod_name,
        mod_name + '.pyx',
        subdir: 'hatchet' / 'cython_modules' / 'libs',
        install: true
    )
endforeach