# SPDX-License-Identifier: Apache-2.0
"""Communities settings resource client (endpoints 1-5)."""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.models.facade.communities import (
    CommunityDetail,
    CommunityList,
    ListCommunitiesRequestDTO,
    PostDefinition,
    PostDefinitionMap,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.transport import HttpTransport

_LIST_PATH = "communication/settings/communities"
_DETAILS_SINGLE_PATH = "communication/settings/communities/{community_id}/details"
_DETAILS_BULK_PATH = "communication/settings/communities/details"
_POST_DEFINITION_PATH = "communication/settings/communities/{community_id}/post-definition"
_POST_DEFINITIONS_PATH = "communication/settings/communities/post-definitions"


class CommunitiesAPI(ResourceClient):
    """Client for community settings endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list(self) -> CommunityList:
        """GET ``/communication/settings/communities``.

        Returns all communities the caller is allowed to post in.
        """
        return CommunityList.from_dict(self._get(_LIST_PATH))

    def details(self, community_id: int) -> CommunityDetail:
        """GET ``/communication/settings/communities/{communityId}/details``.

        Args:
            community_id: Unique community identifier.
        """
        path = _DETAILS_SINGLE_PATH.format(community_id=community_id)
        return CommunityDetail.from_dict(self._get(path))

    def details_bulk(self, community_ids: list[int]) -> CommunityList:  # type: ignore[valid-type]
        """POST ``/communication/settings/communities/details``.

        Retrieve details for multiple communities in a single call.

        Args:
            community_ids: List of community identifiers.
        """
        req = ListCommunitiesRequestDTO(communityIds=community_ids)
        return self.details_bulk_raw(req)

    def details_bulk_raw(self, req: ListCommunitiesRequestDTO) -> CommunityList:
        """POST community details with a pre-built request DTO (escape hatch)."""
        return CommunityList.from_dict(
            self._post(_DETAILS_BULK_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def post_definition(self, community_id: int) -> PostDefinition:
        """GET ``/communication/settings/communities/{communityId}/post-definition``.

        Returns the post structure (field definitions, hashtags, workflow) for a community.

        Args:
            community_id: Unique community identifier.
        """
        path = _POST_DEFINITION_PATH.format(community_id=community_id)
        raw = self._get(path)
        typed = generated.GetPostDefinitionResponseDTOModel.model_validate(raw)
        return PostDefinition(typed)

    def post_definitions(self, community_ids: list[int]) -> PostDefinitionMap:  # type: ignore[valid-type]
        """POST ``/communication/settings/communities/post-definitions``.

        Retrieve post definitions for multiple communities in a single call.

        Args:
            community_ids: List of community identifiers.
        """
        req = ListCommunitiesRequestDTO(communityIds=community_ids)
        return self.post_definitions_raw(req)

    def post_definitions_raw(self, req: ListCommunitiesRequestDTO) -> PostDefinitionMap:
        """POST community post definitions with a pre-built request DTO (escape hatch)."""
        return PostDefinitionMap.from_dict(
            self._post(_POST_DEFINITIONS_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )
