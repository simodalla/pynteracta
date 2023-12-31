import pytest

from pynteracta.api import InteractaApi
from pynteracta.schemas.responses import (
    GetPostDefinitionCatalogsOut,
    ListPostDefinitionCatalogEntriesOut,
)

from .conftest import IntegrationTestData

pytestmark = pytest.mark.integration


def test_list_catalogs(logged_api: InteractaApi, integrations_data: IntegrationTestData):
    result = logged_api.list_catalogs(
        catalog_ids={integrations_data.catalogs.catalog.id}, load_entries=False
    )
    assert isinstance(result, GetPostDefinitionCatalogsOut)
    assert len(result.catalogs) == 1
    assert result.catalogs[0].name.lower() == integrations_data.catalogs.catalog.name
    assert result.catalogs[0].entries is None

    result = logged_api.list_catalogs(
        catalog_ids={integrations_data.catalogs.catalog.id}, load_entries=True
    )
    assert isinstance(result.catalogs[0].entries, list)
    assert len(result.catalogs[0].entries) >= len(integrations_data.catalogs.catalog.labels)
    result_labels = [entry.label.lower() for entry in result.catalogs[0].entries]
    for label in integrations_data.catalogs.catalog.labels:
        assert label in result_labels


def test_list_catolog_entries(logged_api: InteractaApi, integrations_data: IntegrationTestData):
    result = logged_api.list_catalog_entries(integrations_data.catalogs.catalog.id)

    assert isinstance(result, ListPostDefinitionCatalogEntriesOut)
    assert len(result.items) >= len(integrations_data.catalogs.catalog.labels)
    result_labels = [entry.label.lower() for entry in result.items]
    for label in integrations_data.catalogs.catalog.labels:
        assert label in result_labels


def test_list_catolog_entries_from_community_definition(
    logged_api: InteractaApi, integrations_data: IntegrationTestData
):
    community_id = integrations_data.catalogs.catalog.community_id
    post_definition = logged_api.get_post_definition_detail(community_id=community_id)
    community_catalog_ids = post_definition.catalog_ids
    assert integrations_data.catalogs.catalog.id in community_catalog_ids

    result = logged_api.list_catalogs(catalog_ids=set(community_catalog_ids), load_entries=True)
    for catalog in result.catalogs:
        if catalog.id == integrations_data.catalogs.catalog.id:
            catalog_labels = [entry.label.lower() for entry in catalog.entries]
            for label in integrations_data.catalogs.catalog.labels:
                assert label in catalog_labels
