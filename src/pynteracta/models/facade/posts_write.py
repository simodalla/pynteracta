# SPDX-License-Identifier: Apache-2.0
"""Façade per le scritture dei post, le letture propedeutiche, i commenti e il workflow (spec 03).

Molti DTO annidati sono generati come stub ``RootModel[Any]``: le façade li rivalidano nelle
varianti tipizzate (``PostDetailDTO1``, ``PostEditableContentDataDTO1``, ``PostCommentDTO1``,
``PostWorkflowDefinitionStateDTO1``, ``PostWorkflowDefinitionTransitionDTO1``,
``WorkflowDefinitionScreenDTO1``, ``PostAttachmentDataDTO1``, ``UserDTOModel``). Il DTO generato
resta sempre disponibile in ``.raw``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from pynteracta.models.generated import external_v2 as generated


def _typed[M: BaseModel](stub: object, model: type[M]) -> M | None:
    """Rivalida uno stub ``RootModel`` (o un dict) nel modello tipizzato; ``None`` se vuoto."""
    root = getattr(stub, "root", stub)
    if isinstance(root, dict):
        return model.model_validate(root)
    return None


def _typed_list[M: BaseModel](stubs: list[Any] | None, model: type[M]) -> list[M]:
    """Rivalida una lista di stub; gli elementi non oggetto si scartano."""
    items = (_typed(item, model) for item in stubs or [])
    return [item for item in items if item is not None]


class PostWriteResult:
    """Façade sulla risposta di ``create-post``, ``edit-post``, ``edit-post-custom-data`` e
    ``copy-post``.

    Attributes:
        raw: Il DTO generato (``CreatePostResponseDTO``, ``EditPostResponseDTO`` o
            ``CopyPostResponseDTO``).
    """

    def __init__(
        self,
        raw: (
            generated.CreatePostResponseDTO
            | generated.EditPostResponseDTO
            | generated.CopyPostResponseDTO
        ),
    ) -> None:
        self.raw = raw
        self._post = _typed(raw.postData, generated.PostDetailDTO1)

    @property
    def post_id(self) -> int | None:
        """Id del post scritto: dalla risposta (create, copy), altrimenti dai dati del post."""
        post_id = getattr(self.raw, "postId", None)
        if post_id is not None:
            return int(post_id)
        return self._post.id if self._post is not None else None

    @property
    def next_occ_token(self) -> int | None:
        """Token di concorrenza da usare per la modifica successiva."""
        return self.raw.nextOccToken

    @property
    def post(self) -> generated.PostDetailDTO1 | None:
        """Dati del post dopo la scrittura, tipizzati."""
        return self._post

    @classmethod
    def from_create(cls, data: dict[str, Any]) -> PostWriteResult:
        """Legge la risposta di ``create-post``."""
        return cls(generated.CreatePostResponseDTO.model_validate(data))

    @classmethod
    def from_edit(cls, data: dict[str, Any]) -> PostWriteResult:
        """Legge la risposta di ``edit-post`` ed ``edit-post-custom-data``."""
        return cls(generated.EditPostResponseDTO.model_validate(data))

    @classmethod
    def from_copy(cls, data: dict[str, Any]) -> PostWriteResult:
        """Legge la risposta di ``copy-post``."""
        return cls(generated.CopyPostResponseDTO.model_validate(data))


class PostForCreate:
    """Façade su ``post-data-for-create``: i dati iniziali della form di creazione.

    Attributes:
        raw: Il ``GetCustomPostForCreateResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetCustomPostForCreateResponseDTO) -> None:
        self.raw = raw
        self._content = _typed(raw.contentData, generated.PostEditableContentDataDTO1)

    @property
    def content_data(self) -> generated.PostEditableContentDataDTO1 | None:
        """Dati editabili proposti dal server per un post nuovo."""
        return self._content

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostForCreate:
        """Legge la risposta di ``post-data-for-create``."""
        return cls(generated.GetCustomPostForCreateResponseDTO.model_validate(data))


class PostForEdit:
    """Façade su ``post-data-for-edit``: dati editabili e ``occ_token`` per ``edit``.

    Attributes:
        raw: Il ``GetCustomPostForEditResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetCustomPostForEditResponseDTO) -> None:
        self.raw = raw
        self._content = _typed(raw.contentData, generated.PostEditableContentDataDTO1)
        self._state = _typed(raw.currentWorkflowState, generated.PostWorkflowDefinitionStateDTO1)

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``edit`` ed ``edit_custom_data``."""
        return self.raw.occToken

    @property
    def community_id(self) -> int | None:
        """Community del post."""
        return self.raw.communityId

    @property
    def custom_id(self) -> str | None:
        """Identificativo leggibile del post (per esempio ``POST-21269``)."""
        return self.raw.customId

    @property
    def current_workflow_state(self) -> generated.PostWorkflowDefinitionStateDTO1 | None:
        """Stato corrente del workflow, se la community ne ha uno."""
        return self._state

    @property
    def content_data(self) -> generated.PostEditableContentDataDTO1 | None:
        """Dati editabili del post: titolo, descrizione, campi custom, allegati, watcher…"""
        return self._content

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostForEdit:
        """Legge la risposta di ``post-data-for-edit``."""
        return cls(generated.GetCustomPostForEditResponseDTO.model_validate(data))


class PostForCopy:
    """Façade su ``post-data-for-copy``: dati da copiare e ``occ_token`` per ``copy``.

    Attributes:
        raw: Il ``GetCustomPostForCopyResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetCustomPostForCopyResponseDTO) -> None:
        self.raw = raw
        self._content = _typed(raw.contentData, generated.PostEditableContentDataDTO1)

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``copy``."""
        return self.raw.occToken

    @property
    def content_data(self) -> generated.PostEditableContentDataDTO1 | None:
        """Dati editabili del post da copiare."""
        return self._content

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostForCopy:
        """Legge la risposta di ``post-data-for-copy``."""
        return cls(generated.GetCustomPostForCopyResponseDTO.model_validate(data))


class PostComment:
    """Façade sulla risposta di ``create-comment``: il commento appena creato.

    Attributes:
        raw: Il ``CreatePostCommentResponseDTO`` generato.
    """

    def __init__(self, raw: generated.CreatePostCommentResponseDTO) -> None:
        self.raw = raw
        self._comment = _typed(raw.comment, generated.PostCommentDTO1)
        self._creator = (
            _typed(self._comment.creatorUser, generated.UserDTOModel)
            if self._comment is not None
            else None
        )
        parent = self._comment.parentComment if self._comment is not None else None
        parent_root = getattr(parent, "root", parent)
        self._parent_id = parent_root.get("id") if isinstance(parent_root, dict) else None

    @property
    def comment(self) -> generated.PostCommentDTO1 | None:
        """Il commento tipizzato."""
        return self._comment

    @property
    def id(self) -> int | None:
        """Id del commento."""
        return self._comment.id if self._comment is not None else None

    @property
    def comment_plain_text(self) -> str | None:
        """Testo del commento."""
        return self._comment.commentPlainText if self._comment is not None else None

    @property
    def comment_delta(self) -> str | None:
        """Testo del commento in formato Quill delta (JSON)."""
        return self._comment.commentDelta if self._comment is not None else None

    @property
    def creator_user(self) -> generated.UserDTOModel | None:
        """Autore del commento."""
        return self._creator

    @property
    def creation_timestamp(self) -> int | None:
        """Data di creazione (epoch in millisecondi)."""
        return self._comment.creationTimestamp if self._comment is not None else None

    @property
    def parent_comment_id(self) -> int | None:
        """Id del commento a cui questo risponde, se c'è."""
        return self._parent_id

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostComment:
        """Legge la risposta di ``create-comment``."""
        return cls(generated.CreatePostCommentResponseDTO.model_validate(data))


class PostAttachmentsWriteResult:
    """Façade sulla risposta di ``edit-post-attachments``.

    Attributes:
        raw: L'``EditPostAttachmentsResponseDTO`` generato.
    """

    def __init__(self, raw: generated.EditPostAttachmentsResponseDTO) -> None:
        self.raw = raw

    @property
    def post_id(self) -> int | None:
        """Id del post."""
        return self.raw.postId

    @property
    def added(self) -> list[generated.PostAttachmentDataDTO1]:
        """Allegati aggiunti."""
        return _typed_list(self.raw.addedAttachments, generated.PostAttachmentDataDTO1)

    @property
    def updated(self) -> list[generated.PostAttachmentDataDTO1]:
        """Allegati aggiornati."""
        return _typed_list(self.raw.updatedAttachments, generated.PostAttachmentDataDTO1)

    @property
    def removed_ids(self) -> list[int]:
        """Id degli allegati tolti."""
        return list(self.raw.removedAttachmentIds or [])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostAttachmentsWriteResult:
        """Legge la risposta di ``edit-post-attachments``."""
        return cls(generated.EditPostAttachmentsResponseDTO.model_validate(data))


class WorkflowScreen:
    """Façade su ``post-workflow-screen-data-for-edit``: dati e token dello screen.

    Attributes:
        raw: Il ``GetPostWorkflowScreenDataForEditResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetPostWorkflowScreenDataForEditResponseDTO) -> None:
        self.raw = raw
        self._screen = _typed(raw.screen, generated.WorkflowDefinitionScreenDTO1)
        self._state = _typed(raw.currentWorkflowState, generated.PostWorkflowDefinitionStateDTO1)

    @property
    def screen_data(self) -> dict[str, Any]:
        """Valori correnti dei campi dello screen, per id del campo."""
        return dict(self.raw.screenData or {})

    @property
    def screen_occ_token(self) -> int | None:
        """Token di concorrenza dello screen."""
        return self.raw.screenOccToken

    @property
    def screen(self) -> generated.WorkflowDefinitionScreenDTO1 | None:
        """Metadati dello screen (nome, messaggio, campi)."""
        return self._screen

    @property
    def current_workflow_state(self) -> generated.PostWorkflowDefinitionStateDTO1 | None:
        """Stato corrente del workflow del post."""
        return self._state

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowScreen:
        """Legge la risposta di ``post-workflow-screen-data-for-edit``."""
        return cls(generated.GetPostWorkflowScreenDataForEditResponseDTO.model_validate(data))


class WorkflowOperationResult:
    """Façade sulla risposta di ``execute-post-workflow-operation``.

    Attributes:
        raw: L'``ExecutePostWorkflowOperationResponseDTO`` generato.
    """

    def __init__(self, raw: generated.ExecutePostWorkflowOperationResponseDTO) -> None:
        self.raw = raw
        self._state = _typed(raw.newCurrentState, generated.PostWorkflowDefinitionStateDTO1)

    @property
    def new_current_state(self) -> generated.PostWorkflowDefinitionStateDTO1 | None:
        """Stato del workflow dopo la transizione."""
        return self._state

    @property
    def new_screen_data(self) -> dict[str, Any]:
        """Valori dei campi dello screen dopo la transizione."""
        return dict(self.raw.newScreenData or {})

    @property
    def new_permitted_operations(self) -> list[generated.PostWorkflowDefinitionTransitionDTO1]:
        """Transizioni permesse dal nuovo stato."""
        return _typed_list(
            self.raw.newCurrentWorkflowPermittedOperations,
            generated.PostWorkflowDefinitionTransitionDTO1,
        )

    @property
    def new_can_edit_workflow_screen_data(self) -> bool | None:
        """Se i dati di screen del nuovo stato sono modificabili."""
        return self.raw.newCanEditWorkflowScreenData

    @property
    def post_data_has_changed(self) -> bool | None:
        """Se la transizione ha cambiato anche i dati del post."""
        return self.raw.postDataHasChanged

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowOperationResult:
        """Legge la risposta di ``execute-post-workflow-operation``."""
        return cls(generated.ExecutePostWorkflowOperationResponseDTO.model_validate(data))


class WorkflowScreenWriteResult:
    """Façade sulla risposta di ``edit-post-workflow-screen-data``.

    Attributes:
        raw: L'``EditPostWorkflowScreenDataResponseDTO`` generato.
    """

    def __init__(self, raw: generated.EditPostWorkflowScreenDataResponseDTO) -> None:
        self.raw = raw

    @property
    def next_screen_occ_token(self) -> int | None:
        """Token di concorrenza dello screen per la modifica successiva."""
        return self.raw.nextScreenOccToken

    @property
    def new_screen_data(self) -> dict[str, Any]:
        """Valori dei campi dello screen dopo la modifica."""
        return dict(self.raw.newScreenData or {})

    @property
    def post_data_has_changed(self) -> bool | None:
        """Se la modifica ha cambiato anche i dati del post."""
        return self.raw.postDataHasChanged

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowScreenWriteResult:
        """Legge la risposta di ``edit-post-workflow-screen-data``."""
        return cls(generated.EditPostWorkflowScreenDataResponseDTO.model_validate(data))
