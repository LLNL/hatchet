RT = window.Roundtrip;

data_from_py = RT["data_from_py"]

data_to_py = data_from_py + 10

RT["to_py"] = data_to_py