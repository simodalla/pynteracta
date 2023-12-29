import pytest
from faker import Faker

from pydantic import BaseModel, ConfigDict, EmailStr

from pynteracta.api import InteractaApi
from pynteracta.settings import AppSettings, InteractaSettings


class UserData(BaseModel):
    id: int | None = None
    email: EmailStr | None = None


class GroupsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    filter_user_members: str | None = None


class GroupLifecycleData(BaseModel):
    create_filter_user_members: str | None = None
    edit_filter_user_members: str | None = None


class SentinelData(BaseModel):
    model_config = ConfigDict(extra="allow")

    domain: str | None = None
    user: UserData | None = None
    area_id: int | None = None
    manager_id: int | None = None
    business_unit_id: int | None = None
    filter_group_name: str = "demo"


class CatalogData(BaseModel):
    id: int | None = None
    labels: list[str] | None = None
    name: str | None = None
    community_id: int | None = None


class CatalogsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    catalog: CatalogData | None = None


class CommunityPostDefinitionData(BaseModel):
    model_config = ConfigDict(extra="allow")

    community_id: int | None = None


class CommentsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    community_id: int | None = None
    default_custom_data: dict | None = None


class IntegrationTestData(BaseModel):
    model_config = ConfigDict(extra="allow")

    faker_locale: str = "it-IT"
    prefix_admin_object: str = "zzz-pynta-"
    sentinel: SentinelData | None = None
    group_lifecycle: GroupLifecycleData | None = None
    catalogs: CatalogsData | None = None
    community_post_definition: CommunityPostDefinitionData | None = None
    comments: CommentsData | None = None


class IntegrationsAppSettings(AppSettings):
    integrations: IntegrationTestData | None = None


@pytest.fixture(scope="session")
def integration_app_settings() -> IntegrationsAppSettings:
    return IntegrationsAppSettings(_env_file=".envs/integrations/.pyinteracta.toml")


@pytest.fixture(scope="session")
def settings(integration_app_settings: IntegrationsAppSettings) -> InteractaSettings:
    return integration_app_settings.interacta


@pytest.fixture(scope="session")
def integrations_data(integration_app_settings: IntegrationsAppSettings) -> IntegrationTestData:
    return integration_app_settings.integrations


@pytest.fixture(scope="session")
def logged_api(settings: InteractaSettings) -> InteractaApi:
    api = InteractaApi(settings=settings)
    api.login()
    return api


@pytest.fixture
def faker(integrations_data: IntegrationTestData) -> Faker:
    return Faker(integrations_data.faker_locale)
