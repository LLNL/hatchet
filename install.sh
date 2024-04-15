#!/bin/sh

case *"$PWD"* in
    "$PYTHONPATH")
        ;;

    *)
        PYTHONPATH=$PWD:$PYTHONPATH
        ;;
esac
~/wksp-brink2/python-virtualenv/anaconda3/bin/python setup.py clean --all
~/wksp-brink2/python-virtualenv/anaconda3/bin/python setup.py build_ext --inplace
~/wksp-brink2/python-virtualenv/anaconda3/bin/python hatchet/vis/static_fixer.py
