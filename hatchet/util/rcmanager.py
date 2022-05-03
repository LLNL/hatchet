# Copyright 2021 The University of Arizona and other Hatchet Project
# Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping
import os.path as path
import yaml


class ConfigValidator:
    def __init__(self):
        self._validations = {}
        self._set_validators_to_configs()

    def bool_validator(self, key, value):
        if not isinstance(value, bool):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type bool'.format(
                    key
                )
            )
        else:
            return value

    def str_validator(self, key, value):
        if not isinstance(value, str):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type string'.format(
                    key
                )
            )
        else:
            return value

    def int_validator(self, key, value):
        if not isinstance(value, int):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type int'.format(
                    key
                )
            )
        else:
            return value

    def float_validator(self, key, value):
        if not isinstance(value, float):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type float'.format(
                    key
                )
            )
        else:
            return value

    def list_validator(self, key, value):
        if not isinstance(value, list):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type list'.format(
                    key
                )
            )
        else:
            return value

    def dict_validator(self, key, value):
        if not isinstance(value, dict):
            raise TypeError(
                'Error loading configuration: Configuration "{}" must be of type dict'.format(
                    key
                )
            )
        else:
            return value

    def validate(self, key, value):
        return self._validations[key](key, value)

    def _set_validators_to_configs(self):
        self._validations["logging"] = self.bool_validator
        self._validations["log_directory"] = self.str_validator
        self._validations["highlight_name"] = self.bool_validator
        self._validations["invert_colormap"] = self.bool_validator


class RcManager(MutableMapping):
    """
    A runtime configurations class; modeled after the RcParams class in matplotlib.
    The benifit of this class over a dictonary is validation of set item and formatting
    of output.
    """

    def __init__(self, *args, **kwargs):
        self._data = {}
        self._validator = ConfigValidator()
        self._data.update(*args, **kwargs)

    def __setitem__(self, key, val):
        """
        Function loads valid configurations and prints errors for invalid configs.
        """
        try:
            self._validator.validate(key, val)
            return self._data.__setitem__(key, val)
        except TypeError as e:
            raise e

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        for kv in sorted(self._data.__iter__(self)):
            yield kv

    def __str__(self):
        return "\n".join(map("{0[0]}: {0[1]}".format, sorted(self.items())))

    def __len__(self):
        return len(self._data)

    def __delitem__(self, item):
        del self._data[item]


def _resolve_conf_file():
    """
    Determines which configuration file to load.
    Uses the precendence order:
        1. $HOME/.hatchet/hatchetrc.yaml
        2. $HATCHET_BASE_DIR/hatchetrc.yaml
    """
    home = path.expanduser("~")
    conf_dir = path.join(home, ".hatchet", "hatchetrc.yaml")
    if path.exists(conf_dir):
        return conf_dir
    else:
        hatchet_path = path.abspath(path.dirname(path.abspath(__file__)))
        rel_path = path.join(hatchet_path, "..", "..", "hatchetrc.yaml")
        return rel_path


def _read_config_from_file(filepath):
    configs = {}
    with open(filepath, "r") as f:
        configs = yaml.load(f, yaml.FullLoader)
    return configs


filepath = _resolve_conf_file()
configs = _read_config_from_file(filepath)

# Global instance of configurations
RcParams = RcManager(configs)
