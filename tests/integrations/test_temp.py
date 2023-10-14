import pytest
from devtools import debug
from faker import Faker

from pynteracta.api import InteractaApi
from pynteracta.schemas import requests, responses

from .conftest import IntegrationTestData

pytestmark = pytest.mark.temp


def test_call_spot(logged_api: InteractaApi) -> None:
    fake = Faker("it-IT")
    user_id = 4759
    prepare_edit_result = logged_api.get_user_data_for_edit(user_id=user_id)
    assert isinstance(prepare_edit_result, responses.GetUserForEditOut)
    debug(prepare_edit_result)
    new_private_email = fake.email()
    new_mobile_phone = fake.phone_number()
    assert new_mobile_phone != prepare_edit_result.user_info.mobile_phone
    assert new_private_email != prepare_edit_result.private_email
    prepare_edit_result.private_email = new_private_email
    prepare_edit_result.user_info.mobile_phone = new_mobile_phone

    data = requests.EditUserIn(**prepare_edit_result.model_dump(by_alias=True))
    debug(data)

    edit_result = logged_api.edit_user(user_id=user_id, data=data)
    assert isinstance(edit_result, responses.EditUserOut)

    edited_result = logged_api.get_user_data_for_edit(user_id=user_id)
    assert edited_result.private_email == new_private_email
    assert edited_result.user_info.mobile_phone == new_mobile_phone

    debug(edit_result)


def test_modify_group_members(
    logged_api: InteractaApi,
    integrations_data: IntegrationTestData,
):
    group_name = "zzz-pynta-32495f29-3552-472a-b600-d11654c82163"
    data = requests.ListSystemGroupsIn(full_text_filter=group_name)
    results = logged_api.list_groups(data=data)
    assert len(results.items) == 1
    group = results.items[0]
    debug(results)

    prepare_edit_results = logged_api.get_group_data_for_edit(group_id=group.id)
    debug(prepare_edit_results)
    member_ids = [user.id for user in prepare_edit_results.members] + [
        integrations_data.sentinel.user.id
    ]
    debug(member_ids)

    data = requests.EditGroupIn(
        member_ids=member_ids,
        **prepare_edit_results.model_dump(by_alias=True, exclude=["members", "tags"]),
    )
    debug(data)

    edit_results = logged_api.edit_group(group_id=group.id, data=data)
    debug(edit_results)


def test_list_business_unit(logged_api: InteractaApi):
    debug(logged_api.list_business_units())
