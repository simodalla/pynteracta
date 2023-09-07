from rich.table import Table

from .api import InteractaApi
from .utils import PLAYGROUND_SETTINGS


class PlaygroundApi(InteractaApi):
    def __init__(
        self,
        log_calls: bool = False,
        log_call_responses: bool = False,
    ):
        super().__init__(
            base_url=PLAYGROUND_SETTINGS["base_url"],
            log_calls=log_calls,
            log_call_responses=log_call_responses,
        )

    def bootstrap_token(self):
        url, data = self.prepare_credentials_login(
            username=PLAYGROUND_SETTINGS["username"],
            password=PLAYGROUND_SETTINGS["password"],
        )
        token = self.login(url, data)
        return token

    def list_posts(self):
        response = self.get_posts(PLAYGROUND_SETTINGS["community"]["id"])
        if response.status_code != 200:
            pass
        result = response.json()
        if "items" not in result:
            pass
        return result["items"]

    def table_list_posts(self):
        posts = self.list_posts()
        table = Table("Id", "Titolo", "Descrizione")
        for post in posts:
            table.add_row(str(post["id"]), post["title"], post["descriptionPlainText"])
        return table
