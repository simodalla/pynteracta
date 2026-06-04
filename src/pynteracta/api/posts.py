# SPDX-License-Identifier: Apache-2.0
"""Posts resource client."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_query_params
from pynteracta.models.facade.posts import (
    CheckVisibilityRequestDTO,
    GlobalPostStream,
    ListCommunityPostsFilteredRequestDTO,
    ListCommunityPostsRequestDTO,
    ListPostCommentsRequestDTO,
    ListPostHistoryEventsRequestDTO,
    Post,
    PostCapabilities,
    PostCommentList,
    PostHistoryEventList,
    PostList,
    VisibilityResult,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_GET_POST_PATH = "communication/posts/data/post-detail-by-id/{post_id}"
_GET_POST_BY_CLIENT_UID_PATH = "communication/posts/data/post-detail-by-client-uid/{client_uid}"
_POST_CAPABILITIES_PATH = "communication/posts/data/post-capabilities/{post_id}"
_LIST_COMMUNITY_PATH = "communication/posts/data/list/community/{community_id}"
_COMMUNITY_LIST_PATH = "communication/posts/data/community-list/{community_id}"
_HISTORY_LIST_PATH = "communication/posts/data/history-list/{post_id}"
_GLOBAL_STREAM_PATH = "communication/posts/data/global-stream"
_CHECK_VISIBILITY_PATH = "communication/posts/data/check-visibility"
_CHECK_VISIBILITY_WITH_COMMENTS_PATH = "communication/posts/data/check-visibility-with-comments"
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

    def get_by_client_uid(  # noqa: PLR0913
        self,
        client_uid: str,
        *,
        load_main_attachment: bool = False,
        load_main_attachment_view_link: bool = False,
        load_main_attachment_download_link: bool = False,
        load_main_attachment_preview_image_link: bool = False,
        load_main_attachment_preview_image_animated_link: bool = False,
        load_main_attachment_preview_image_hi_res_link: bool = False,
        load_main_attachment_preview_image_hi_res_animated_link: bool = False,
    ) -> Post:
        """GET ``/communication/posts/data/post-detail-by-client-uid/{clientUid}``."""
        path = _GET_POST_BY_CLIENT_UID_PATH.format(client_uid=client_uid)
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

    def capabilities(self, post_id: int) -> PostCapabilities:
        """GET ``/communication/posts/data/post-capabilities/{postId}``."""
        path = _POST_CAPABILITIES_PATH.format(post_id=post_id)
        return PostCapabilities.from_dict(self._get(path))

    def history(
        self,
        post_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        **filters: Any,
    ) -> PostHistoryEventList:
        """POST ``/communication/posts/data/history-list/{postId}``."""
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
        )
        req = ListPostHistoryEventsRequestDTO.model_validate(body)
        return self.history_raw(post_id, req)

    def history_raw(
        self, post_id: int, req: ListPostHistoryEventsRequestDTO
    ) -> PostHistoryEventList:
        """POST history with a pre-built request DTO (escape hatch)."""
        path = _HISTORY_LIST_PATH.format(post_id=post_id)
        return PostHistoryEventList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_history(
        self,
        post_id: int,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[generated.PostActivityHistoryEventDTO1]:
        """Lazy iterator over all pages of :meth:`history`."""

        def fetch(page_token: str | None) -> PostHistoryEventList:
            return self.history(post_id, page_token=page_token, page_size=page_size, **filters)

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def global_stream(  # noqa: PLR0913
        self,
        *,
        sync_token: str | None = None,
        page_token: str | None = None,
        load_main_attachment: bool | None = None,
        load_main_attachment_view_link: bool | None = None,
        load_main_attachment_download_link: bool | None = None,
        load_main_attachment_preview_image_link: bool | None = None,
        load_main_attachment_preview_image_animated_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_link: bool | None = None,
        load_main_attachment_preview_image_hi_res_animated_link: bool | None = None,
    ) -> GlobalPostStream:
        """POST ``/communication/posts/data/global-stream`` (filters via query params)."""
        params = build_query_params(
            sync_token=sync_token,
            page_token=page_token,
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
        return GlobalPostStream.from_dict(
            self._post(_GLOBAL_STREAM_PATH, json={}, params=params or None)
        )

    def iterate_global_stream(
        self,
        *,
        sync_token: str | None = None,
        load_main_attachment: bool | None = None,
    ) -> PageIterator[generated.BasePostsStreamChunkElementDTOModel]:
        """Lazy iterator over all pages of :meth:`global_stream`."""

        def fetch(page_token: str | None) -> GlobalPostStream:
            return self.global_stream(
                sync_token=sync_token,
                page_token=page_token,
                load_main_attachment=load_main_attachment,
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def community_list(
        self,
        community_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        **filters: Any,
    ) -> PostList:
        """POST ``/communication/posts/data/community-list/{communityId}``.

        Lighter listing endpoint using :class:`ListCommunityPostsRequestDTO` (basic filters only).
        Distinct from ``list/community`` which uses the more fully-featured
        :class:`ListCommunityPostsFilteredRequestDTO`.
        """
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
        )
        req = ListCommunityPostsRequestDTO.model_validate(body)
        return self.community_list_raw(community_id, req)

    def community_list_raw(self, community_id: int, req: ListCommunityPostsRequestDTO) -> PostList:
        """POST community-list with a pre-built request DTO (escape hatch)."""
        path = _COMMUNITY_LIST_PATH.format(community_id=community_id)
        return PostList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_community_list(
        self,
        community_id: int,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[generated.BaseListPostsElementDTOModel]:
        """Lazy iterator over all pages of :meth:`community_list`."""

        def fetch(page_token: str | None) -> PostList:
            return self.community_list(
                community_id, page_token=page_token, page_size=page_size, **filters
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def check_visibility(self, post_ids: list[int]) -> VisibilityResult:
        """POST ``/communication/posts/data/check-visibility``."""
        req = CheckVisibilityRequestDTO(ids=post_ids)
        return self.check_visibility_raw(req)

    def check_visibility_raw(self, req: CheckVisibilityRequestDTO) -> VisibilityResult:
        """POST check-visibility with a pre-built request DTO (escape hatch)."""
        return VisibilityResult.from_dict(
            self._post(_CHECK_VISIBILITY_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def check_visibility_with_comments(self, post_ids: list[int]) -> VisibilityResult:
        """POST ``/communication/posts/data/check-visibility-with-comments``."""
        req = CheckVisibilityRequestDTO(ids=post_ids)
        return self.check_visibility_with_comments_raw(req)

    def check_visibility_with_comments_raw(
        self, req: CheckVisibilityRequestDTO
    ) -> VisibilityResult:
        """POST check-visibility-with-comments with a pre-built request DTO (escape hatch)."""
        return VisibilityResult.from_dict(
            self._post(
                _CHECK_VISIBILITY_WITH_COMMENTS_PATH,
                json=req.model_dump(mode="json", exclude_none=True),
            )
        )

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
