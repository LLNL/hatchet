#!/bin/sh

case "$PYTHONPATH" in
    *"$PWD"*)
        ;;

    *)
        PYTHONPATH=$PWD:$PYTHONPATH
        ;;
esac

python setup.py build_ext --inplace
python hatchet/vis/static_fixer.py