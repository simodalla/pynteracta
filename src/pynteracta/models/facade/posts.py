# SPDX-License-Identifier: Apache-2.0
"""Facade models for the posts endpoints.

Endpoints covered:
  GET  /communication/posts/data/post-detail-by-id/{postId}          (endpoint 6)
  POST /communication/posts/data/list/community/{communityId}        (endpoint 7)
  POST /communication/posts/data/comments-list/{postId}              (endpoint 8)
"""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the posts API layer (M5).
ListCommunityPostsFilteredRequestDTO = generated.ListCommunityPostsFilteredRequestDTO
ListPostCommentsRequestDTO = generated.ListPostCommentsRequestDTO


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
