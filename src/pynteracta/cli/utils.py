from rich.table import Table

from ..schemas.models import BaseListPostsElement
from ..settings import InteractaSettings


def table_list_posts(posts: list[BaseListPostsElement], settings: InteractaSettings) -> Table:
    table = Table("Id", "Titolo", "Descrizione", show_lines=True)
    for post in posts:
        table.add_row(
            f"[link={post.get_absolute_url(base_url=settings.portal_url)}]{post.id}[/link]",
            post.title,
            post.description_plain_text,
        )
    return table
