# SPDX-License-Identifier: Apache-2.0
"""Facade models for the attachments endpoints."""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated

ListPostAttachmentsByPostIdRequestDTO = generated.ListPostAttachmentsByPostIdRequestDTO
CheckVisibilityRequestDTO = generated.CheckVisibilityRequestDTO


class PostAttachment:
    """Narrow facade over :class:`~generated.ListPostAttachmentsElementDTOModel`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListPostAttachmentsElementDTOModel) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def content_mime_type(self) -> str | None:
        return self.raw.contentMimeType

    @property
    def size(self) -> int | None:
        return self.raw.size

    @property
    def type(self) -> int | None:
        return self.raw.type

    @property
    def downloadable(self) -> bool | None:
        return self.raw.downloadable

    @property
    def version_number(self) -> int | None:
        return self.raw.versionNumber

    @property
    def creator_user(self) -> generated.UserDTO | None:
        return self.raw.creatorUser

    @property
    def creation_timestamp(self) -> int | None:
        return self.raw.creationTimestamp

    @property
    def hashtags(self) -> list[generated.HashtagDTOModel] | None:
        return self.raw.hashtags

    @property
    def temporary_content_view_link(self) -> str | None:
        return self.raw.temporaryContentViewLink

    @property
    def temporary_content_download_link(self) -> str | None:
        return self.raw.temporaryContentDownloadLink

    @property
    def temporary_content_preview_image_link(self) -> str | None:
        return self.raw.temporaryContentPreviewImageLink

    @property
    def temporary_content_preview_image_animated_link(self) -> str | None:
        return self.raw.temporaryContentPreviewImageAnimatedLink

    @property
    def temporary_content_preview_image_hi_res_link(self) -> str | None:
        return self.raw.temporaryContentPreviewImageHiResLink

    @property
    def temporary_content_preview_image_hi_res_animated_link(self) -> str | None:
        return self.raw.temporaryContentPreviewImageHiResAnimatedLink

    @classmethod
    def from_dict(cls, data: dict) -> PostAttachment:  # type: ignore[type-arg]
        """Parse from a raw API response dict element.

        Args:
            data: A single item dict from the ``items`` list.

        Returns:
            A new :class:`PostAttachment`.
        """
        raw = generated.ListPostAttachmentsElementDTOModel.model_validate(data)
        return cls(raw)


class PostAttachmentList:
    """Narrow facade over :class:`~generated.ListPostAttachmentsResponseDTO`.

    The ``items`` list holds :class:`~generated.ListPostAttachmentsElementDTO` objects, which are
    generated as ``RootModel[Any]`` stubs.  Call :meth:`items_typed` to re-validate each item
    against the fully-typed :class:`~generated.ListPostAttachmentsElementDTOModel`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListPostAttachmentsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        return self.raw.totalItemsCount

    @property
    def can_add_attachment(self) -> bool | None:
        return self.raw.canAddAttachment

    @property
    def image_attachments_count(self) -> int | None:
        return self.raw.imageAttachmentsCount

    @property
    def video_attachments_count(self) -> int | None:
        return self.raw.videoAttachmentsCount

    @property
    def audio_attachments_count(self) -> int | None:
        return self.raw.audioAttachmentsCount

    @property
    def documents_attachments_count(self) -> int | None:
        return self.raw.documentsAttachmentsCount

    @property
    def items_typed(self) -> list[PostAttachment]:
        """Re-validate each opaque list item into :class:`PostAttachment`.

        Returns:
            List of :class:`PostAttachment` instances.
        """
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(
                    PostAttachment(
                        generated.ListPostAttachmentsElementDTOModel.model_validate(root)
                    )
                )
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PostAttachmentList:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`PostAttachmentList`.
        """
        raw = generated.ListPostAttachmentsResponseDTO.model_validate(data)
        return cls(raw)


class AttachmentDetail:
    """Narrow facade over :class:`~generated.GetPostAttachmentDetailResponseDTO`.

    ``attachmentData`` is typed as ``PostAttachmentDataDTO`` (a ``RootModel[Any]`` stub) in the
    generated code; we re-validate it against the typed sibling
    :class:`~generated.PostAttachmentDataDTO1`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetPostAttachmentDetailResponseDTO) -> None:
        self.raw = raw
        self._attachment_data: generated.PostAttachmentDataDTO1 | None = None
        if raw.attachmentData is not None:
            ad = raw.attachmentData
            root = ad.root if hasattr(ad, "root") else ad
            if isinstance(root, dict):
                self._attachment_data = generated.PostAttachmentDataDTO1.model_validate(root)
        self._post: generated.PostBaseInfoDTO1 | None = None
        if raw.post is not None:
            pr = raw.post
            proot = pr.root if hasattr(pr, "root") else pr
            if isinstance(proot, dict):
                self._post = generated.PostBaseInfoDTO1.model_validate(proot)

    @property
    def attachment_data(self) -> generated.PostAttachmentDataDTO1 | None:
        """Typed attachment data DTO."""
        return self._attachment_data

    @property
    def post(self) -> generated.PostBaseInfoDTO1 | None:
        """Parent post base info (typed variant of the RootModel stub)."""
        return self._post

    @property
    def id(self) -> int | None:
        return self._attachment_data.id if self._attachment_data else None

    @property
    def name(self) -> str | None:
        return self._attachment_data.name if self._attachment_data else None

    @property
    def content_mime_type(self) -> str | None:
        return self._attachment_data.contentMimeType if self._attachment_data else None

    @property
    def size(self) -> int | None:
        return self._attachment_data.size if self._attachment_data else None

    @property
    def type(self) -> int | None:
        return self._attachment_data.type if self._attachment_data else None

    @property
    def downloadable(self) -> bool | None:
        return self._attachment_data.downloadable if self._attachment_data else None

    @property
    def temporary_content_view_link(self) -> str | None:
        return self._attachment_data.temporaryContentViewLink if self._attachment_data else None

    @property
    def temporary_content_download_link(self) -> str | None:
        return self._attachment_data.temporaryContentDownloadLink if self._attachment_data else None

    @classmethod
    def from_dict(cls, data: dict) -> AttachmentDetail:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`AttachmentDetail`.
        """
        raw = generated.GetPostAttachmentDetailResponseDTO.model_validate(data)
        return cls(raw)


class AttachmentVisibility:
    """Thin facade over :class:`~generated.CheckVisibilityResponseDTO`.

    Returns which attachment IDs are visible to the current user.
    Kept separate from the v0.2 :class:`~pynteracta.models.facade.posts.VisibilityResult`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.CheckVisibilityResponseDTO) -> None:
        self.raw = raw

    @property
    def ids(self) -> list[int]:
        """List of visible attachment IDs."""
        return self.raw.ids or []

    @classmethod
    def from_dict(cls, data: dict) -> AttachmentVisibility:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`AttachmentVisibility`.
        """
        raw = generated.CheckVisibilityResponseDTO.model_validate(data)
        return cls(raw)
