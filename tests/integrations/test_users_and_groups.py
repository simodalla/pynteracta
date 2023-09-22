import pytest
from devtools import debug
from faker import Faker

from pynteracta import exceptions
from pynteracta.api import InteractaApi
from pynteracta.schemas import responses
from pynteracta.schemas.models import (
    GoogleUserCredentialsConfiguration,
    ListSystemUsersElement,
    UserCredentialsConfiguration,
)
from pynteracta.schemas.requests import (
    CreateUserIn,
    EditUserIn,
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

    debug(user)


@pytest.mark.lifecycle
def test_user_lifecycle(
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
    create_data = CreateUserIn(
        firstname=username,
        lastname=username,
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

    debug(email)

    # verifica utente non esistente
    with pytest.raises(exceptions.ObjectDoesNotFound):
        result = logged_api.get_user(email_external_auth_service=email)

    # creazione utente
    created_result = logged_api.create_user(data=create_data)
    assert isinstance(created_result, responses.CreateUserOut)

    # verifica utente esistente e recupera i dati
    result = logged_api.get_user(email_external_auth_service=email)
    assert isinstance(result, ListSystemUsersElement)
    assert created_result.user_id == result.id

    # modifica dati utente
    prepare_edit_result = logged_api.get_user_data_for_edit(user_id=created_result.user_id)
    assert isinstance(prepare_edit_result, responses.GetUserForEditOut)
    new_private_email = faker.email()
    new_mobile_phone = faker.phone_number()
    assert new_mobile_phone != prepare_edit_result.user_info.mobile_phone
    assert new_private_email != prepare_edit_result.private_email
    prepare_edit_result.private_email = new_private_email
    prepare_edit_result.user_info.mobile_phone = new_mobile_phone

    edit_data = EditUserIn(**prepare_edit_result.model_dump(by_alias=True))
    edit_result = logged_api.edit_user(user_id=created_result.user_id, data=edit_data)
    assert isinstance(edit_result, responses.EditUserOut)

    prepare_edit_result = logged_api.get_user_data_for_edit(user_id=created_result.user_id)
    assert prepare_edit_result.private_email == new_private_email
    assert prepare_edit_result.user_info.mobile_phone == new_mobile_phone

    # cancellazione utente
    deleted_result = logged_api.delete_user(created_result.user_id)
    assert deleted_result.status_code == 200


@pytest.mark.temp
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

    data = EditUserIn(**prepare_edit_result.model_dump(by_alias=True))
    debug(data)

    edit_result = logged_api.edit_user(user_id=user_id, data=data)
    assert isinstance(edit_result, responses.EditUserOut)

    edited_result = logged_api.get_user_data_for_edit(user_id=user_id)
    assert edited_result.private_email == new_private_email
    assert edited_result.user_info.mobile_phone == new_mobile_phone

    debug(edit_result)


def test_call_get_user_return_user(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
):
    user_id = integrations_data.sentinel.user.id
    email = integrations_data.sentinel.user.email
    result = logged_api.get_user(email_external_auth_service=email)

    assert result.id == user_id

    result = logged_api.list_users(data=ListSystemUsersIn(full_text_filter=email))
    assert len(result.items) == 1
    assert result.items[0].id == user_id


def test_call_get_user_raise_object_not_found(
    logged_api: InteractaApi, integrations_data: IntegrationTestData, faker: Faker
) -> None:
    email = faker.email()

    with pytest.raises(IndexError):
        logged_api.get_user(email_external_auth_service=email)
