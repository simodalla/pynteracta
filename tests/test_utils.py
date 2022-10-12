import pytest

from pynteracta import exceptions
from pynteracta.utils import check_service_account_json_data, parse_service_account_file


def test_check_scheck_service_account_file_raise_error_if_path_not_exists(faker):
    with pytest.raises(exceptions.InteractaError):
        parse_service_account_file(faker.file_path(depth=3))


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"private_key": "aaa"},
        {"client_id": "aaa"},
        {"private_key_id": "aaa"},
        {"private_key_id": "aaa", "client_id": "aaa"},
    ],
)
def test_check_service_account_json_data_raise_error_without_ok_keys(data):
    with pytest.raises(exceptions.InteractaError) as excinfo:
        check_service_account_json_data(data)
    assert (
        str(excinfo.value)
        == "Il service account non risulta valido. Non sono presenti tutti parametri necessari."
    )


@pytest.mark.parametrize(
    "data",
    [
        {"private_key_id": "aaa", "client_id": "aaa", "private_key": None},
        {"private_key_id": "", "client_id": "aaa", "private_key": "aaa"},
        {"private_key_id": "", "client_id": None, "private_key": "aaa"},
    ],
)
def test_check_service_account_json_data_raise_error_without_values(data):
    with pytest.raises(exceptions.InteractaError) as excinfo:
        check_service_account_json_data(data)
    assert (
        str(excinfo.value)
        == "Il service account non risulta valido. Non sono valorizzati tutti parametri necessari."
    )


def test_check_service_account_json_data_return_true():
    result = check_service_account_json_data(
        {"private_key_id": "aaa", "client_id": "aaa", "private_key": "aaa"}
    )
    assert result is True
