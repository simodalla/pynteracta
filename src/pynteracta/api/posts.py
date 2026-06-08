# SPDX-License-Identifier: Apache-2.0
"""Posts resource client."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_query_params, to_epoch_millis
from pynteracta.exceptions import ValidationError
from pynteracta.models.facade.post_filters import PostFieldFilter, validate_field_filters
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

if TYPE_CHECKING:
    from pynteracta.models.facade.communities import PostDefinition


def _set_if(d: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        d[key] = value


# Allowed static values for the orderBy request field.
POST_ORDER_FIELDS: tuple[str, ...] = (
    "postCustomId",
    "postTitle",
    "postCreatorUser",
    "postCreationTimestamp",
    "postLastModifyUser",
    "postLastModifyTimestamp",
    "postLastModifyAndCommentTimestamp",
    "postViewedByMeTimestamp",
    "postModifiedByMeTimestamp",
    "postCommentedByMeTimestamp",
    "postScheduledPublication",
    "postRecency",
)

_CUSTOM_FIELD_ORDER_RE = re.compile(r"^postCustomField-\d+$")


def _validate_order_by(value: str) -> str:
    """Validate *value* against POST_ORDER_FIELDS plus the postCustomField-{id} form."""
    if value in POST_ORDER_FIELDS or _CUSTOM_FIELD_ORDER_RE.match(value):
        return value
    raise ValidationError(
        f"Invalid order_by value {value!r}. Allowed static values: {POST_ORDER_FIELDS}. "
        "Dynamic form: 'postCustomField-<id>'."
    )


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

    def list_in_community(  # noqa: PLR0913, PLR0915
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
        # --- ordering ---
        order_by: str | None = None,
        order_desc: bool | None = None,
        pinned_first: bool | None = None,
        # --- communityPostFilters (curated subset) ---
        title: str | None = None,
        description: str | None = None,
        contains_text: str | None = None,
        created_by_user_ids: list[int] | None = None,
        created_by_group_ids: list[int] | None = None,
        creation_timestamp_from: int | float | str | None = None,
        creation_timestamp_to: int | float | str | None = None,
        modified_timestamp_from: int | float | str | None = None,
        modified_timestamp_to: int | float | str | None = None,
        hashtag_ids: list[int] | None = None,
        hashtags_logical_and: bool | None = None,
        post_types: list[int] | None = None,
        current_workflow_status_ids: list[int] | None = None,
        visibility: int | None = None,
        followed_by_me: bool | None = None,
        mentioned: bool | None = None,
        to_manage: bool | None = None,
        only_pinned: bool | None = None,
        post_field_filters: list[PostFieldFilter | dict[str, Any]] | None = None,
        screen_field_filters: list[PostFieldFilter | dict[str, Any]] | None = None,
        # --- opt-in validation ---
        validate_with: PostDefinition | None = None,
        # --- escape hatch ---
        community_post_filters: dict[str, Any] | None = None,
        **filters: Any,
    ) -> PostList:
        """POST ``/communication/posts/data/list/community/{communityId}``.

        Args:
            community_id: Target community.
            order_by: Sort field — one of :data:`POST_ORDER_FIELDS` or ``'postCustomField-{id}'``.
            order_desc: Descending sort (``True``) or ascending (``False``).
            pinned_first: Show pinned posts first.
            title: Filter on post title.
            description: Filter on post description.
            contains_text: Full-text filter on post content.
            created_by_user_ids: Filter by creator user ids.
            created_by_group_ids: Filter by creator group ids.
            creation_timestamp_from: Lower bound on creation date (epoch-ms, datetime, or ISO str).
            creation_timestamp_to: Upper bound on creation date.
            modified_timestamp_from: Lower bound on modification date.
            modified_timestamp_to: Upper bound on modification date.
            hashtag_ids: Filter by hashtag ids.
            hashtags_logical_and: Combine hashtag filters with AND (default OR).
            post_types: Filter by post type ids (1=CUSTOM, 2=EVENTO, 3=QUESTIONARIO).
            current_workflow_status_ids: Filter by workflow status ids.
            visibility: Filter by visibility (public/private).
            followed_by_me: Only posts followed by the current user.
            mentioned: Only posts where the current user was mentioned.
            to_manage: Only posts the current user has actions to take on.
            only_pinned: Only pinned posts.
            post_field_filters: Custom-field filters — list of :class:`PostFieldFilter` or dicts
                with keys ``column_id``/``columnId``, ``type_id``/``typeId``, ``parameters``.
            screen_field_filters: Workflow screen-field filters (same structure).
            validate_with: When supplied, validates ``post_field_filters`` and
                ``screen_field_filters`` against this community's post-definition before sending
                (no extra network call; raises :class:`~pynteracta.exceptions.ValidationError`).
            community_post_filters: Pre-built ``communityPostFilters`` dict — escape hatch for
                the long-tail fields not promoted to explicit kwargs.
            **filters: Additional camelCase fields forwarded to the request body (escape hatch).
        """
        if order_by is not None:
            _validate_order_by(order_by)

        # Coerce date kwargs to epoch-millis
        cf_from = to_epoch_millis(creation_timestamp_from)
        cf_to = to_epoch_millis(creation_timestamp_to)
        mf_from = to_epoch_millis(modified_timestamp_from)
        mf_to = to_epoch_millis(modified_timestamp_to)

        # Opt-in validation of field filters
        coerced_pff: list[PostFieldFilter] | None = None
        coerced_sff: list[PostFieldFilter] | None = None
        if post_field_filters is not None and validate_with is not None:
            coerced_pff = validate_field_filters(post_field_filters, validate_with)
        elif post_field_filters is not None:
            coerced_pff = [
                f if isinstance(f, PostFieldFilter) else PostFieldFilter.from_dict(f)
                for f in post_field_filters
            ]
        if screen_field_filters is not None and validate_with is not None:
            coerced_sff = validate_field_filters(screen_field_filters, validate_with, screen=True)
        elif screen_field_filters is not None:
            coerced_sff = [
                f if isinstance(f, PostFieldFilter) else PostFieldFilter.from_dict(f)
                for f in screen_field_filters
            ]

        # Build communityPostFilters dict
        cpf: dict[str, Any] = {}
        if community_post_filters:
            cpf.update(community_post_filters)
        _set_if(cpf, "title", title)
        _set_if(cpf, "description", description)
        _set_if(cpf, "containsText", contains_text)
        _set_if(cpf, "createdByUserIds", created_by_user_ids)
        _set_if(cpf, "createdByGroupIds", created_by_group_ids)
        _set_if(cpf, "creationTimestampFrom", cf_from)
        _set_if(cpf, "creationTimestampTo", cf_to)
        _set_if(cpf, "modifiedTimestampFrom", mf_from)
        _set_if(cpf, "modifiedTimestampTo", mf_to)
        _set_if(cpf, "hashtagIds", hashtag_ids)
        _set_if(cpf, "hashtagsLogicalAnd", hashtags_logical_and)
        _set_if(cpf, "postTypes", post_types)
        _set_if(cpf, "currentWorkflowStatusIds", current_workflow_status_ids)
        _set_if(cpf, "visibility", visibility)
        _set_if(cpf, "followedByMe", followed_by_me)
        _set_if(cpf, "mentioned", mentioned)
        _set_if(cpf, "toManage", to_manage)
        _set_if(cpf, "onlyPinned", only_pinned)
        if coerced_pff is not None:
            cpf["postFieldFilters"] = [f.to_dict() for f in coerced_pff]
        if coerced_sff is not None:
            cpf["screenFieldFilters"] = [f.to_dict() for f in coerced_sff]

        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
        )
        if order_by is not None:
            body["orderBy"] = order_by
        if order_desc is not None:
            body["orderDesc"] = order_desc
        if pinned_first is not None:
            body["pinnedFirst"] = pinned_first
        if cpf:
            body["communityPostFilters"] = cpf

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

    def iterate_in_community(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        page_size: int | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
        pinned_first: bool | None = None,
        title: str | None = None,
        description: str | None = None,
        contains_text: str | None = None,
        created_by_user_ids: list[int] | None = None,
        created_by_group_ids: list[int] | None = None,
        creation_timestamp_from: int | float | str | None = None,
        creation_timestamp_to: int | float | str | None = None,
        modified_timestamp_from: int | float | str | None = None,
        modified_timestamp_to: int | float | str | None = None,
        hashtag_ids: list[int] | None = None,
        hashtags_logical_and: bool | None = None,
        post_types: list[int] | None = None,
        current_workflow_status_ids: list[int] | None = None,
        visibility: int | None = None,
        followed_by_me: bool | None = None,
        mentioned: bool | None = None,
        to_manage: bool | None = None,
        only_pinned: bool | None = None,
        post_field_filters: list[PostFieldFilter | dict[str, Any]] | None = None,
        screen_field_filters: list[PostFieldFilter | dict[str, Any]] | None = None,
        validate_with: PostDefinition | None = None,
        community_post_filters: dict[str, Any] | None = None,
        **filters: Any,
    ) -> PageIterator[generated.BaseListPostsElementDTOModel]:
        """Lazy iterator over all pages of :meth:`list_in_community`."""

        def fetch(page_token: str | None) -> PostList:
            return self.list_in_community(
                community_id,
                page_token=page_token,
                page_size=page_size,
                order_by=order_by,
                order_desc=order_desc,
                pinned_first=pinned_first,
                title=title,
                description=description,
                contains_text=contains_text,
                created_by_user_ids=created_by_user_ids,
                created_by_group_ids=created_by_group_ids,
                creation_timestamp_from=creation_timestamp_from,
                creation_timestamp_to=creation_timestamp_to,
                modified_timestamp_from=modified_timestamp_from,
                modified_timestamp_to=modified_timestamp_to,
                hashtag_ids=hashtag_ids,
                hashtags_logical_and=hashtags_logical_and,
                post_types=post_types,
                current_workflow_status_ids=current_workflow_status_ids,
                visibility=visibility,
                followed_by_me=followed_by_me,
                mentioned=mentioned,
                to_manage=to_manage,
                only_pinned=only_pinned,
                post_field_filters=post_field_filters,
                screen_field_filters=screen_field_filters,
                validate_with=validate_with,
                community_post_filters=community_post_filters,
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
