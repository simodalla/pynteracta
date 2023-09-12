from rich.table import Table

from pynteracta.api import InteractaApi, PlaygroundApi
from pynteracta.schemas.models import BaseListPostsElement


class CliRichMixin:
    def table_list_posts(self, posts: list[BaseListPostsElement]):
        table = Table("Id", "Titolo", "Descrizione")
        for post in posts:
            table.add_row(str(post.id), post.title, post.description_plain_text)
        return table


class CliPlaygroundApi(CliRichMixin, PlaygroundApi):
    pass


class CliInteractaApi(CliRichMixin, InteractaApi):
    pass
