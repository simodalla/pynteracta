from devtools import debug
from faker import Faker

from pynteracta.api import InteractaApi
from pynteracta.schemas import responses
from pynteracta.schemas.models import (
    GoogleUserCredentialsConfiguration,
    UserCredentialsConfiguration,
)
from pynteracta.schemas.requests import (
    CreateUserIn,
    EditUserIn,
    ListSystemUsersIn,
    UserInfoIn,
    UserSettingsIn,
)


def test_list_users(logged_api: InteractaApi) -> None:
    results = logged_api.list_users()
    assert isinstance(results, responses.ListSystemUsersOut)
    assert len(results.items) > 0


def test_list_users_filter_username(logged_api: InteractaApi) -> None:
    email = "sdalla@unionerenolavinosamoggia.bo.it"

    body = ListSystemUsersIn()
    body.full_text_filter = email

    results = logged_api.list_users(data=body)
    assert len(results.items) == 1
    user = results.items[0]
    assert user.deleted is False
    assert user.blocked is False

    debug(user)


def test_user_lifecycle(logged_api: InteractaApi) -> None:
    fake = Faker("it-IT")
    fake_id = fake.uuid4()
    domain = "unionerenolavinosamoggia.bo.it"
    username = f"zzz-pynta-{fake_id}"
    email = f"{username}@{domain}"
    google_credential = GoogleUserCredentialsConfiguration(google_account_id=email, enabled=True)
    user_credential_conf = UserCredentialsConfiguration(google=google_credential)
    user_info = UserInfoIn(
        area={"id": 1},
        business_unit={"id": 1},
        internal_phone=fake.phone_number(),
        manager={"id": 3872},
        mobile_phone=fake.phone_number(),
        phone=fake.phone_number(),
        place=fake.address(),
        role=fake.job(),
    )
    data = CreateUserIn(
        firstname=username,
        lastname=username,
        user_credentials_configuration=user_credential_conf,
        contact_email=email,
        private_email=fake.email(),
        user_info=user_info,
        user_settings=UserSettingsIn(
            people_section_enabled=False,
            visible_in_people_section=False,
            reduced_profile=True,
            view_user_profiles=False,
        ),
    )

    debug(email)

    # creazione utente
    create_result = logged_api.create_user(data=data)
    assert isinstance(create_result, responses.CreateUserOut)

    # modifica dati utente
    prepare_edit_result = logged_api.get_user_data_for_edit(user_id=create_result.user_id)
    assert isinstance(prepare_edit_result, responses.GetUserForEditOut)

    # cancellazione utente
    delete_result = logged_api.delete_user(create_result.user_id)
    assert delete_result.status_code == 200


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
