# from typing import Any

# from pydantic import BaseModel, PrivateAttr

# from .models import InteractaModel, Post, User, UserFull


# class ResponseInteracta(InteractaModel):
#     _response: Any = PrivateAttr(None)


# class ResponseItems(ResponseInteracta):
#     items: list | None = []
#     next_page_token: str | None = None
#     total_items_count: int | None = None


# class ResponsePosts(ResponseItems):
#     items: list[Post] | None = []


# class ResponseUsers(ResponseItems):
#     items: list[UserFull] | None


# class ResponsePost(ResponseInteracta, Post):
#     current_workflow_state: Any | None = None
#     current_workflow_screen_data: Any | None = None
#     mentions: Any | None = None
#     comment_mentions: Any | None = None
