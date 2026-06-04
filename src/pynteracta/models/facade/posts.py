# SPDX-License-Identifier: Apache-2.0
"""Facade models for the posts endpoints."""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the posts API layer.
ListCommunityPostsFilteredRequestDTO = generated.ListCommunityPostsFilteredRequestDTO
ListCommunityPostsRequestDTO = generated.ListCommunityPostsRequestDTO
ListPostCommentsRequestDTO = generated.ListPostCommentsRequestDTO
ListPostHistoryEventsRequestDTO = generated.ListPostHistoryEventsRequestDTO
CheckVisibilityRequestDTO = generated.CheckVisibilityRequestDTO


class Post:
    """Narrow facade over :class:`~generated.GetPostDetailResponseDTO`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetPostDetailResponseDTO) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Unique post identifier."""
        return self.raw.id

    @property
    def community_id(self) -> int | None:
        """Identifier of the community this post belongs to."""
        return self.raw.communityId

    @property
    def title(self) -> str | None:
        """Post title."""
        return self.raw.title

    @property
    def description_plain_text(self) -> str | None:
        """Post description as plain text."""
        return self.raw.descriptionPlainText

    @property
    def creation_timestamp(self) -> int | None:
        """Creation timestamp (epoch milliseconds)."""
        return self.raw.creationTimestamp

    @property
    def last_modify_timestamp(self) -> int | None:
        """Last modification timestamp (epoch milliseconds)."""
        return self.raw.lastModifyTimestamp

    @property
    def comments_count(self) -> int | None:
        """Number of comments on this post."""
        return self.raw.commentsCount

    @property
    def likes_count(self) -> int | None:
        """Number of likes on this post."""
        return self.raw.likesCount

    @classmethod
    def from_dict(cls, data: dict) -> Post:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`Post`.
        """
        raw = generated.GetPostDetailResponseDTO.model_validate(data)
        return cls(raw)


class PostList:
    """Narrow facade over :class:`~generated.PagedListPostsResponseDTO`.

    The ``items`` list holds :class:`~generated.BaseListPostsElementDTO` objects, which are
    generated as ``RootModel[Any]`` stubs.  Call :meth:`items_typed` to re-validate each item
    against the fully-typed :class:`~generated.BaseListPostsElementDTOModel`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.PagedListPostsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        """Token for the next page, or ``None`` if this is the last page."""
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        """Total number of matching posts (only populated when requested)."""
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[generated.BaseListPostsElementDTOModel]:
        """Re-validate each opaque list item into the typed element DTO.

        Returns:
            List of :class:`~generated.BaseListPostsElementDTOModel` instances.
        """
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(generated.BaseListPostsElementDTOModel.model_validate(root))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PostList:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`PostList`.
        """
        raw = generated.PagedListPostsResponseDTO.model_validate(data)
        return cls(raw)


class PostCommentList:
    """Narrow facade over :class:`~generated.ListPostCommentsResponseDTO`.

    The ``items`` list holds :class:`~generated.PostCommentDTO` objects, which are generated as
    ``RootModel[Any]`` stubs.  Call :meth:`items_typed` to re-validate each item against the
    fully-typed :class:`~generated.PostCommentDTO1`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListPostCommentsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        """Token for the next page, or ``None`` if this is the last page."""
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        """Total number of matching comments (only populated when requested)."""
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[generated.PostCommentDTO1]:
        """Re-validate each opaque list item into the typed comment DTO.

        Returns:
            List of :class:`~generated.PostCommentDTO1` instances.
        """
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(generated.PostCommentDTO1.model_validate(root))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PostCommentList:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`PostCommentList`.
        """
        raw = generated.ListPostCommentsResponseDTO.model_validate(data)
        return cls(raw)


class GlobalPostStream:
    """Narrow facade over :class:`~generated.GlobalPostsStreamResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.GlobalPostsStreamResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def next_sync_token(self) -> str | None:
        return self.raw.nextSyncToken

    @property
    def items_typed(self) -> list[generated.BasePostsStreamChunkElementDTOModel]:
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(generated.BasePostsStreamChunkElementDTOModel.model_validate(root))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> GlobalPostStream:  # type: ignore[type-arg]
        raw = generated.GlobalPostsStreamResponseDTO.model_validate(data)
        return cls(raw)


class PostCapabilities:
    """Narrow facade over :class:`~generated.GetPostCapabilitiesResponseDTO1`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.GetPostCapabilitiesResponseDTO1) -> None:
        self.raw = raw

    @property
    def can_view_detail(self) -> bool | None:
        return self.raw.canViewDetail

    @property
    def can_modify(self) -> bool | None:
        return self.raw.canModify

    @property
    def can_delete(self) -> bool | None:
        return self.raw.canDelete

    @property
    def can_view_comment(self) -> bool | None:
        return self.raw.canViewComment

    @property
    def can_add_comment(self) -> bool | None:
        return self.raw.canAddComment

    @property
    def can_edit_like(self) -> bool | None:
        return self.raw.canEditLike

    @property
    def can_edit_follow(self) -> bool | None:
        return self.raw.canEditFollow

    @classmethod
    def from_dict(cls, data: dict) -> PostCapabilities:  # type: ignore[type-arg]
        # GetPostCapabilitiesResponseDTO is a RootModel[Any] stub; bind to the typed variant.
        raw = generated.GetPostCapabilitiesResponseDTO1.model_validate(data)
        return cls(raw)


class PostHistoryEventList:
    """Narrow facade over :class:`~generated.ListPostHistoryEventsResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.ListPostHistoryEventsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[generated.PostActivityHistoryEventDTO1]:
        """Re-validate each opaque item into the typed event DTO."""
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(generated.PostActivityHistoryEventDTO1.model_validate(root))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PostHistoryEventList:  # type: ignore[type-arg]
        raw = generated.ListPostHistoryEventsResponseDTO.model_validate(data)
        return cls(raw)


class VisibilityResult:
    """Narrow facade over :class:`~generated.CheckVisibilityWithCommentsResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.CheckVisibilityWithCommentsResponseDTO) -> None:
        self.raw = raw

    @property
    def posts_typed(self) -> list[generated.CheckVisibilityWithCommentsResponseElementDTO1]:
        """Re-validate each opaque element into the typed DTO."""
        if not self.raw.posts:
            return []
        result = []
        for item in self.raw.posts:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(
                    generated.CheckVisibilityWithCommentsResponseElementDTO1.model_validate(root)
                )
        return result

    @classmethod
    def from_dict(cls, data: dict) -> VisibilityResult:  # type: ignore[type-arg]
        raw = generated.CheckVisibilityWithCommentsResponseDTO.model_validate(data)
        return cls(raw)
