from hatchet.util.rcmanager import (
    RcManager,
    ConfigValidator,
    _resolve_conf_file,
    _read_config_from_file,
)


def test_creation():
    file = _resolve_conf_file()
    config = _read_config_from_file(file)
    RC = RcManager(config)

    assert RC is not None


def test_global_binding():
    import hatchet as ht

    assert hasattr(ht, "RcParams")


def test_change_value():
    import hatchet as ht
    from hatchet.util.rcmanager import RcParams

    assert "logging" in ht.RcParams

    ht.RcParams["logging"] = True
    assert ht.RcParams["logging"] is True
    assert RcParams["logging"] is True

    ht.RcParams["logging"] = False
    assert ht.RcParams["logging"] is False
    assert RcParams["logging"] is False


def test_validator():
    V = ConfigValidator()

    # Add validators for keys where we can input
    # bad values
    V._validations["bad_bool"] = V.bool_validator
    V._validations["bad_string"] = V.str_validator
    V._validations["bad_int"] = V.int_validator
    V._validations["bad_float"] = V.float_validator
    V._validations["bad_list"] = V.list_validator
    V._validations["bad_dict"] = V.dict_validator

    # Test passes if exception is thrown
    # Else: test fails
    try:
        V.validate("bad_bool", "True")
        assert False
    except TypeError:
        assert True

    try:
        V.validate("bad_string", True)
        assert False
    except TypeError:
        assert True

    try:
        V.validate("bad_int", "123")
        assert False
    except TypeError:
        assert True

    try:
        V.validate("bad_float", "1.2387")
        assert False
    except TypeError:
        assert True

    try:
        V.validate("bad_list", {})
        assert False
    except TypeError:
        assert True

    try:
        V.validate("bad_dict", [])
        assert False
    except TypeError:
        assert True

    # Testing valid inputs
    # Goes through to true assertion if
    # validation works
    try:
        V.validate("bad_bool", True)
        assert True
    except TypeError:
        assert False

    try:
        V.validate("bad_string", "string")
        assert True
    except TypeError:
        assert False

    try:
        V.validate("bad_int", 1)
        assert True
    except TypeError:
        assert False

    try:
        V.validate("bad_float", 1.2387)
        assert True
    except TypeError:
        assert False

    try:
        V.validate("bad_list", [])
        assert True
    except TypeError:
        assert False

    try:
        V.validate("bad_dict", {})
        assert True
    except TypeError:
        assert False
