from rich.table import Table

from pynteracta.api import InteractaApi, PlaygroundApi


class CliRichMixin:
    def table_list_posts(self, posts: list | None):
        table = Table("Id", "Titolo", "Descrizione")
        for post in posts:
            table.add_row(str(post["id"]), post["title"], post["descriptionPlainText"])
        return table


class CliPlaygroundApi(CliRichMixin, PlaygroundApi):
    pass


class CliInteractaApi(CliRichMixin, InteractaApi):
    pass
