#!/bin/sh

case *"$PWD"* in
    "$PYTHONPATH")
        ;;

    *)
        PYTHONPATH=$PWD:$PYTHONPATH
        ;;
esac
python setup.py clean --all
python setup.py build_ext --inplace
python hatchet/vis/static_fixer.py
