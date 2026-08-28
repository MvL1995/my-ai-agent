import importlib
import importlib.util


module_spec = importlib.util.find_spec(
    "input_validation"
)

assert module_spec is not None, (
    "input_validation.py 尚未实现"
)

input_validation = importlib.import_module(
    "input_validation"
)

normalize_user_input = getattr(
    input_validation,
    "normalize_user_input",
    None
)

assert normalize_user_input is not None, (
    "normalize_user_input() 尚未实现"
)

cases = [
    ("", None),
    ("   ", None),
    ("\t\n", None),
    ("  新对话  ", "新对话"),
    (
        "  我今天学习 Python  ",
        "我今天学习 Python"
    ),
]

for raw_input, expected in cases:
    assert (
        normalize_user_input(raw_input)
        == expected
    )

print("Input-validation tests passed.")