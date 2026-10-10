# Users API

The `UsersAPI` client exposes the user read endpoints (system user list, own profile, edit form)
and, since the admin write group opened by ADR 0001, the four admin write endpoints: create, edit,
delete and edit credentials.

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    page = client.users.list(page_size=50)
    for u in page.items_typed:
        print(u.id, u.firstName, u.lastName, u.contactEmail)

    me = client.users.profile()
    print(me.first_name, me.contact_email)

    # Edit form (admin): the current state plus the optimistic-concurrency token
    user = client.users.get_for_edit(1042)
    print(user.first_name, user.last_name, user.contact_email, user.blocked)
    print(user.occ_token)  # the token to pass to edit()
```

`UserForEdit.blocked` is read-only: the edit DTO has no `blocked` field, so blocking and
unblocking a user is not something this library can do.

## Writing users

`create()`, `edit()`, `delete()` and `edit_credentials()` mirror the other write groups: explicit
snake_case keyword arguments, a `*_raw()` variant for callers holding a pre-built DTO, and a
facade over the server response. **Only the fields you pass are sent**, in one request; nested
blocks (`user_preferences`, `user_info`, `user_settings`, `user_credentials_configuration`,
`reset_user_custom_credentials_command`) are passed as dicts in the shape of the DTO (camelCase
keys) or as generated DTOs.

```python
from pynteracta.client import InteractaClient
from pynteracta.exceptions import ConcurrencyError

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    created = client.users.create(
        firstname="Maria",
        lastname="Rossi",
        contact_email="m.rossi@tenant.example.com",
        user_credentials_configuration={
            "custom": {"username": "m.rossi@tenant.example.com", "active": True}
        },
        reset_user_custom_credentials_command={"generatePassword": True},
    )
    print(created.user_id, created.next_occ_token)
    print(created.generated_password)  # ["..."]: hand it over, it is shown only here

    # Edit: read first, pass the token, and send back every field that must survive
    user = client.users.get_for_edit(created.user_id)
    try:
        edited = client.users.edit(
            created.user_id,
            user.occ_token,
            firstname=user.first_name,
            lastname="Rossi-Bianchi",
            contact_email=user.contact_email,
        )
    except ConcurrencyError:
        raise  # the user changed after we read it: re-read and decide, the library never retries
    print(edited.next_occ_token)

    # Credentials: only the blocks you pass are touched
    creds = client.users.get_credentials_for_edit(created.user_id)
    client.users.edit_credentials(
        created.user_id,
        creds.occ_token,
        google={"googleAccountId": "m.rossi@tenant.example.com", "enabled": True},
    )

    client.users.delete(created.user_id)
```

### `UserWriteResult`

`create()`, `edit()` and `edit_credentials()` return a `UserWriteResult`: `user_id` (from the
create response, otherwise the id you passed), `next_occ_token` (the token for the next edit),
`generated_password`, `expired_credentials`, `sent_email_notify` (create only),
`account_photo_url`, and `.raw` (the generated response DTO). `delete()` returns nothing: the
response has no body.

### Concurrency: `occ_token`

`edit()` and `edit_credentials()` take the token read with `get_for_edit()` (`UserForEdit.occ_token`)
and `get_credentials_for_edit()` (`UserCredentialsForEdit.occ_token`). If the user changed in the
meantime the server answers `409`, mapped to `ConcurrencyError`. The library does **not** re-read
and retry (ADR 0001): one request per call, also on timeouts and network errors, whose outcome
stays unknown until you check.

### Generated password

Ask the server to generate the custom password with
`reset_user_custom_credentials_command={"generatePassword": True}`, or set one with
`{"password": ["..."]}`; `forceCredentialsExpiration` forces a change at first login and
`emailNotifyRecipients` sends it by email. The password can only be set at creation: the
credentials edit DTO has no password field. The swagger declares `generatedPassword` as a list of
strings while the tenant returns a single string: `generated_password` always gives you a list.
Request and response bodies are redacted before they reach logs, audit log and hooks
(`password`, `generatedPassword` → `***REDACTED***`), and a malformed create response raises a
`ValueError` that names the fields, never the values.

### Omitted fields in `edit()`: the server replaces the user

Verified against a tenant (spec 05): `edit()` **requires** `firstname` and `lastname` (`400`
`REQUIRED_FIELD` otherwise) and treats the request as a replacement of the scalar fields:
`contact_email`, `private_email` and `external_id` that are missing from the request are
**cleared**. The nested blocks are different: `user_preferences`, `user_info` and `user_settings`
you omit are **kept**.

!!! warning "Pass every scalar field you want to keep"
    Read the user first and send back first name, last name, contact email, private email and
    external id. The CLI `users edit` does this for you.

### Credential blocks in `edit_credentials()`: omitted blocks are kept

`edit_credentials()` takes up to three blocks, `google`, `microsoft` and `custom`. A block you do
not pass is **kept** as it is (a call without any block changes nothing). The server has no notion
of a disabled block: to **remove** one, send it with the flag false and **no account id**
(`custom={"active": False}`, `google={"enabled": False}`); an account id or username together
with the flag false is rejected (`400` `INVALID_VALUE`). `custom.active` is required whenever the
`custom` block is present (`400` `REQUIRED_FIELD`), and usernames and account ids must belong to
the tenant's domain (`400` `INVALID_DOMAIN`).

### Deleting a user

After `delete()` the user is gone: the credentials form answers `404` (`NotFoundError`) and the
edit form answers `204` with an empty body, which `get_for_edit()` maps to `NotFoundError` as well
(`status_code == 204`). The tenant gives that `204` for any unknown user id.

## API Reference

::: pynteracta.api.users.UsersAPI
    options:
      show_source: false

## Facade Reference

::: pynteracta.models.facade.users.UserForEdit

::: pynteracta.models.facade.users.UserWriteResult

See also the guide [Filtering and sorting users](../guides/filtering-users.md).
