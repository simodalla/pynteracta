# SPDX-License-Identifier: Apache-2.0
"""Posts resource client (endpoints 6-8)."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_query_params
from pynteracta.models.facade.posts import (
    ListCommunityPostsFilteredRequestDTO,
    ListPostCommentsRequestDTO,
    Post,
    PostCommentList,
    PostList,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_GET_POST_PATH = "communication/posts/data/post-detail-by-id/{post_id}"
_LIST_COMMUNITY_PATH = "communication/posts/data/list/community/{community_id}"
_COMMENTS_PATH = "communication/posts/data/comments-list/{post_id}"


class PostsAPI(ResourceClient):
    """Client for post detail, community listing, and comments endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def get(  # noqa: PLR0913
        self,
        post_id: int,
        *,
        load_main_attachment: bool = False,
        load_main_attachment_view_link: bool = False,
        load_main_attachment_download_link: bool = False,
        load_main_attachment_preview_image_link: bool = False,
        load_main_attachment_preview_image_animated_link: bool = False,
        load_main_attachment_preview_image_hi_res_link: bool = False,
        load_main_attachment_preview_image_hi_res_animated_link: bool = False,
    ) -> Post:
        """GET ``/communication/posts/data/post-detail-by-id/{postId}``."""
        path = _GET_POST_PATH.format(post_id=post_id)
        params = build_query_params(
            load_main_attachment=load_main_attachment,
            load_main_attachment_view_link=load_main_attachment_view_link,
            load_main_attachment_download_link=load_main_attachment_download_link,
            load_main_attachment_preview_image_link=load_main_attachment_preview_image_link,
            load_main_attachment_preview_image_animated_link=(
                load_main_attachment_preview_image_animated_link
            ),
            load_main_attachment_preview_image_hi_res_link=(
                load_main_attachment_preview_image_hi_res_link
            ),
            load_main_attachment_preview_image_hi_res_animated_link=(
                load_main_attachment_preview_image_hi_res_animated_link
            ),
        )
        return Post.from_dict(self._get(path, params=params or None))

    def list_in_community(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        load_post_details: bool = True,
        load_main_attachment: bool | None = None,
        load_main_attachment_view_link: bool | None = None,
        load_main_attachment_download_link: bool | None = None,
        load_main_attachment_preview_image_link: bool | None = None,
        load_main_attachment_preview_image_animated_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_animated_link: bool | None = None,
        load_capabilities: bool | None = None,
        **filters: Any,
    ) -> PostList:
        """POST ``/communication/posts/data/list/community/{communityId}``."""
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
        )
        req = ListCommunityPostsFilteredRequestDTO.model_validate(body)
        return self.list_in_community_raw(
            community_id,
            req,
            load_post_details=load_post_details,
            load_main_attachment=load_main_attachment,
            load_main_attachment_view_link=load_main_attachment_view_link,
            load_main_attachment_download_link=load_main_attachment_download_link,
            load_main_attachment_preview_image_link=load_main_attachment_preview_image_link,
            load_main_attachment_preview_image_animated_link=(
                load_main_attachment_preview_image_animated_link
            ),
            load_main_attachment_preview_image_hi_res_link=(
                load_main_attachment_preview_image_hi_res_link
            ),
            load_main_attachment_preview_image_hi_res_animated_link=(
                load_main_attachment_preview_image_hi_res_animated_link
            ),
            load_capabilities=load_capabilities,
        )

    def list_in_community_raw(  # noqa: PLR0913
        self,
        community_id: int,
        req: ListCommunityPostsFilteredRequestDTO,
        *,
        load_post_details: bool = True,
        load_main_attachment: bool | None = None,
        load_main_attachment_view_link: bool | None = None,
        load_main_attachment_download_link: bool | None = None,
        load_main_attachment_preview_image_link: bool | None = None,
        load_main_attachment_preview_image_animated_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_animated_link: bool | None = None,
        load_capabilities: bool | None = None,
    ) -> PostList:
        """POST community post list with a pre-built request DTO (escape hatch)."""
        path = _LIST_COMMUNITY_PATH.format(community_id=community_id)
        params = build_query_params(
            load_post_details=load_post_details,
            load_main_attachment=load_main_attachment,
            load_main_attachment_view_link=load_main_attachment_view_link,
            load_main_attachment_download_link=load_main_attachment_download_link,
            load_main_attachment_preview_image_link=load_main_attachment_preview_image_link,
            load_main_attachment_preview_image_animated_link=(
                load_main_attachment_preview_image_animated_link
            ),
            load_main_attachment_preview_image_hi_res_link=(
                load_main_attachment_preview_image_hi_res_link
            ),
            load_main_attachment_preview_image_hi_res_animated_link=(
                load_main_attachment_preview_image_hi_res_animated_link
            ),
            load_capabilities=load_capabilities,
        )
        return PostList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True), params=params)
        )

    def iterate_in_community(
        self,
        community_id: int,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[generated.BaseListPostsElementDTOModel]:
        """Lazy iterator over all pages of :meth:`list_in_community`."""

        def fetch(page_token: str | None) -> PostList:
            return self.list_in_community(
                community_id,
                page_token=page_token,
                page_size=page_size,
                **filters,
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def comments(
        self,
        post_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        **filters: Any,
    ) -> PostCommentList:
        """POST ``/communication/posts/data/comments-list/{postId}``."""
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
        )
        req = ListPostCommentsRequestDTO.model_validate(body)
        return self.comments_raw(post_id, req)

    def comments_raw(self, post_id: int, req: ListPostCommentsRequestDTO) -> PostCommentList:
        """POST post comments with a pre-built request DTO (escape hatch)."""
        path = _COMMENTS_PATH.format(post_id=post_id)
        return PostCommentList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_comments(
        self,
        post_id: int,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[generated.PostCommentDTO1]:
        """Lazy iterator over all pages of :meth:`comments`."""

        def fetch(page_token: str | None) -> PostCommentList:
            return self.comments(post_id, page_token=page_token, page_size=page_size, **filters)

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)
