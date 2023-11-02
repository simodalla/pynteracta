import pytest
from devtools import debug  # noqa
from faker import Faker

from pynteracta import exceptions
from pynteracta.api import InteractaApi
from pynteracta.schemas import responses
from pynteracta.schemas.models import (
    GoogleUserCredentialsConfiguration,
    UserCredentialsConfiguration,
)
from pynteracta.schemas.requests import (
    CreateUserIn,
    ListSystemGroupsIn,
    ListSystemUsersIn,
    UserInfoIn,
    UserSettingsIn,
)

from .conftest import IntegrationTestData

pytestmark = pytest.mark.integration


def test_list_users(logged_api: InteractaApi) -> None:
    results = logged_api.list_users()
    assert isinstance(results, responses.ListSystemUsersOut)
    assert len(results.items) > 0


def test_list_users_filter_username(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
) -> None:
    email = integrations_data.sentinel.user.email

    data = ListSystemUsersIn()
    data.full_text_filter = email

    results = logged_api.list_users(data=data)
    assert len(results.items) == 1
    user = results.items[0]
    assert user.deleted is False
    assert user.blocked is False


def test_call_get_user_return_user(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
) -> None:
    user_id = integrations_data.sentinel.user.id
    email = integrations_data.sentinel.user.email
    result = logged_api.get_user(email_external_auth_service=email)

    assert result.id == user_id

    result = logged_api.list_users(data=ListSystemUsersIn(full_text_filter=email))
    assert len(result.items) == 1
    assert result.items[0].id == user_id


def test_call_get_user_raise_object_not_found(logged_api: InteractaApi, faker: Faker) -> None:
    email = faker.email()

    with pytest.raises(exceptions.ObjectDoesNotFound):
        logged_api.get_user(email_external_auth_service=email)


def test_call_get_user_raise_multiple_object(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
) -> None:
    text_filter = "s"
    data = ListSystemUsersIn(full_text_filter=text_filter)
    results = logged_api.list_users(data=data)
    if len(results.items) < 2:
        pytest.fail(
            f"Sembra che non siano presenti almeno 2 utenti che fanno match con il filtro full"
            f" text '{text_filter}'"
        )

    with pytest.raises(exceptions.MultipleObjectsReturned):
        logged_api.get_user(data=data)


def test_list_groups(logged_api: InteractaApi) -> None:
    results = logged_api.list_groups()
    assert isinstance(results, responses.ListSystemGroupsOut)
    assert len(results.items) > 0


def test_list_groups_filter_name(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
) -> None:
    filter_group_name = integrations_data.sentinel.filter_group_name
    data = ListSystemGroupsIn(full_text_filter=filter_group_name)
    results = logged_api.list_groups(data=data)
    assert isinstance(results, responses.ListSystemGroupsOut)
    if len(results.items) < 2:
        pytest.fail(
            f"Sembra che non siano presenti almeno 2 gruppi che fanno match con il filtro full"
            f" text '{filter_group_name}'"
        )


@pytest.mark.lifecycle
def test_user_con_accentate(
    logged_api: InteractaApi, integrations_data: IntegrationTestData, faker: Faker
) -> None:
    fake_id = faker.uuid4()
    username = f"{integrations_data.prefix_admin_object}{fake_id}"
    email = f"{username}@{integrations_data.sentinel.domain}"
    google_credential = GoogleUserCredentialsConfiguration(google_account_id=email, enabled=True)
    user_credential_conf = UserCredentialsConfiguration(google=google_credential)
    user_info = UserInfoIn(
        area={"id": integrations_data.sentinel.area_id},
        business_unit={"id": integrations_data.sentinel.business_unit_id},
        internal_phone=faker.phone_number(),
        manager={"id": integrations_data.sentinel.manager_id},
        mobile_phone=faker.phone_number(),
        phone=faker.phone_number(),
        place=faker.address(),
        role=faker.job(),
    )
    debug(email)
    create_data = CreateUserIn(
        firstname="provà",
        lastname="provà",
        user_credentials_configuration=user_credential_conf,
        contact_email=email,
        private_email=faker.email(),
        user_info=user_info,
        user_settings=UserSettingsIn(
            people_section_enabled=False,
            visible_in_people_section=False,
            reduced_profile=True,
            view_user_profiles=False,
        ),
    )
    debug(create_data)
    created_result = logged_api.create_user(data=create_data)
    assert isinstance(created_result, responses.CreateUserOut)
