import pytest

from pynteracta.api import InteractaApi
from pynteracta.schemas.models import PostWorkflowDefinitionScreenField

from .conftest import IntegrationTestData

pytestmark = pytest.mark.integration


def test_screen_field_metadatas_of_postworkflowdefinition(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
):
    result = logged_api.get_post_definition_detail(
        community_id=integrations_data.community_post_definition.community_id
    )
    assert isinstance(result.workflow_definition.screen_field_metadatas, list) is True

    for screen_field in result.workflow_definition.screen_field_metadatas:
        assert isinstance(screen_field, PostWorkflowDefinitionScreenField)

    for label in integrations_data.community_post_definition.screen_metadata_labels:
        screen_field = result.workflow_definition.get_screen_field(label=label)
        assert isinstance(screen_field, PostWorkflowDefinitionScreenField)
        assert screen_field.label == label
