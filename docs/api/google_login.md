# Google login

Browser sign-in with a Google account, session kept in the system keychain, renewal without the
browser. Requires the `google` extra (`pip install "pynteracta[google]"`); see
[Authentication → Google OAuth2](../authentication.md#google-oauth2).

`InteractaClient(profile_name=...)` on a `google_oauth2` profile uses the saved session by
itself; these functions are for signing in, checking and removing it from Python. None of them
writes to standard output.

::: pynteracta.google_login
    options:
      members:
        - login
        - status
        - logout
        - GoogleLoginResult
        - GoogleSessionStatus
        - GoogleLogoutResult
        - GoogleSessionTokenProvider
        - session_token_provider

::: pynteracta.exceptions.ConfigurationError
