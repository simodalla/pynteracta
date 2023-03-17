from pydantic import BaseModel


class Body(BaseModel):
    pageToken: str | None = None
    pageSize: int | None = None
    calculateTotalItemsCount: bool | None = True


class BodyOrdering(Body):
    orderDesc: bool | None = None


class BodyPost(BodyOrdering):
    title: str | None = None
    description: str | None = None
    createdByUserId: int | None = None
    creationTimestampFrom: int | None = None
    creationTimestampTo: int | None = None
    modifiedByUserId: int | None = None
    modifiedTimestampFrom: int | None = None
    modifiedTimestampTo: int | None = None
    containsText: str | None = None
    followedByMe: bool | None = None
    toManage: bool | None = None
    toManageProcesses: bool | None = None
    toManageStandardTasks: bool | None = None
    mentioned: bool | None = None
    currentWorkflowStatusIds: list[int] | None = None
    postType: int | None = None
    postTypes: list[int] | None = None
    draftType: int | None = None
    eventPostFilter: dict | None = None
    orderBy: str | None = None
    hashtagIds: list[int] | None = None
    hashtagsLogicalAnd: bool | None = None
    attachmentHashtagIds: list[int] | None = None
    attachmentHashtagsLogicalAnd: bool | None = None
    visibility: int | None = None
    customFieldFilters: dict | None = None
    postFieldFilters: dict | None = None
    screenFieldFilters: dict | None = None
    acknowledgeTaskFilter: dict | None = None
    draft: bool | None = None
    pinnedFirst: bool | None = None


class BodyUser(BodyOrdering):
    fullTextFilter: str | None
    firstNamePrefixFullTextFilter: str | None
    lastNamePrefixFullTextFilter: str | None
    emailPrefixFullTextFilter: str | None
    externalAuthServiceEmailFullTextFilter: str | None
    statusFilter: list[int] | None
    workspaceIds: list[int] | None
    businessUnitIds: list[int] | None
    areaIds: list[int] | None
    place: str | None
    orderTypeId: str | None
