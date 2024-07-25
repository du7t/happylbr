import pytest

from libs.model_base import Base

base = Base()


@pytest.mark.parametrize(
    ("input_dict", "expected_bool"),
    [
        ({'Entrypoint': {'patched': True, 'siblings': {}}}, True),
        ({'ServerA10': {'siblings': {}, 'patched': False}}, False),
        ({'ServerA10': {'siblings': {}, 'patched': True}}, True),
        ({'Entry': {'patched': True, 'siblings': {'scp': {'F5': {'patched': True, 'siblings': {}}}, 'patched': True}}}, True),
        ({'Entry': {'patched': True, 'siblings': {'scp': {'F5': {'patched': False, 'siblings': {}}}, 'patched': True}}}, False)
    ]
)
def test_is_siblings_data_success(input_dict, expected_bool):
    assert base._is_siblings_data_success(data=input_dict, method='patched') == expected_bool
