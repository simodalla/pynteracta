# SPDX-License-Identifier: Apache-2.0
"""Test delle façade dei post evento (spec 08, T04)."""

from __future__ import annotations

import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from api_helpers import load_payload

from pynteracta.models.facade import (
    EventData,
    EventInvitee,
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
    ParticipationAnswer,
)
from pynteracta.models.generated import external_v2 as generated

_ROME = ZoneInfo("Europe/Rome")
_START = datetime(2026, 11, 5, 10, 0, tzinfo=_ROME)
_END = datetime(2026, 11, 5, 12, 0, tzinfo=_ROME)
_COMMUNITY_ID = 79
_OCC_TOKEN = 5
_USER_ID = 7
_GROUP_ID = 3
_COLLABORATOR = 2
_PARTICIPANTS = 3


def _event_dict() -> dict:  # type: ignore[type-arg]
    data = load_payload("event_post_for_edit_response.json")
    return copy.deepcopy(data["contentData"]["event"])


def _event(data: dict) -> EventData:  # type: ignore[type-arg]
    return EventData(generated.EventPostDataDTOModel.model_validate(data))


# criterio: 08-C07
def test_participation_answer_values() -> None:
    assert ParticipationAnswer(1) is ParticipationAnswer.YES
    assert ParticipationAnswer(2) is ParticipationAnswer.MAYBE
    assert ParticipationAnswer(3) is ParticipationAnswer.NO
    with pytest.raises(ValueError, match="4"):
        ParticipationAnswer(4)


class TestEventData:
    # criterio: 08-C11
    def test_fields_from_fixture(self) -> None:
        event = _event(_event_dict())
        assert isinstance(event.raw, generated.EventPostDataDTOModel)
        assert event.start_at == _START
        assert event.end_at == _END
        assert event.start_at is not None
        assert event.start_at.utcoffset() == _START.utcoffset()
        assert event.timezone == "Europe/Rome"
        assert event.all_day is False
        assert event.location == "Sala A"
        assert event.participants_count == _PARTICIPANTS
        assert event.my_answer is ParticipationAnswer.YES
        assert event.send_edit_post_notifications is False

    # criterio: 08-C11
    def test_invitees(self) -> None:
        event = _event(_event_dict())
        assert len(event.invited_users) == 1
        user = event.invited_users[0]
        assert isinstance(user, EventInvitee)
        assert user.id == _USER_ID
        assert user.type_id == _COLLABORATOR
        assert user.name == "Alice Rossi"
        assert isinstance(user.raw, generated.InvitationUserDTO1)
        group = event.invited_groups[0]
        assert group.id == _GROUP_ID
        assert group.type_id == 0
        assert group.name == "G"
        assert isinstance(group.raw, generated.InvitationGroupDTO1)

    # criterio: 08-C11
    def test_local_datetime_and_timezone_fallback(self) -> None:
        data = _event_dict()
        del data["startAt"]["zonedDatetime"]
        data["endAt"] = {"localDatetime": "2026-11-05T12:00:00"}
        event = _event(data)
        assert event.start_at == _START
        assert event.start_at is not None
        assert event.start_at.tzinfo == _ROME
        assert event.end_at == _END

    # criterio: 08-C11
    def test_dates_none_without_zone_or_value(self) -> None:
        data = _event_dict()
        del data["startAt"]["zonedDatetime"]
        del data["timezone"]
        del data["endAt"]
        event = _event(data)
        assert event.start_at is None
        assert event.end_at is None
        assert event.timezone is None

    # criterio: 08-C11
    def test_unparsable_zoned_datetime_falls_back_to_local(self) -> None:
        data = _event_dict()
        data["startAt"]["zonedDatetime"] = "2026-11-05T10:00:00+01:00[Europe/Rome]"
        assert _event(data).start_at == _START

    # criterio: 08-C11
    def test_unknown_timezone_gives_none(self) -> None:
        data = _event_dict()
        del data["startAt"]["zonedDatetime"]
        data["timezone"] = "Nowhere/Town"
        assert _event(data).start_at is None

    # criterio: 08-C11
    def test_unanswered_and_without_invitations(self) -> None:
        data = _event_dict()
        data["participateTypeId"] = None
        del data["invitations"]
        event = _event(data)
        assert event.my_answer is None
        assert event.invited_users == []
        assert event.invited_groups == []
        assert event.send_edit_post_notifications is None

    def test_user_name_falls_back_to_caption_parts(self) -> None:
        invitee = EventInvitee(generated.InvitationUserDTO1(id=9, firstName="Bea"))
        assert invitee.name == "Bea"
        assert EventInvitee(generated.InvitationUserDTO1(id=10)).name is None


class TestEventForms:
    # criterio: 08-C11
    def test_for_create(self) -> None:
        form = EventPostForCreate.from_dict(load_payload("event_post_for_create_response.json"))
        assert isinstance(form.raw, generated.GetEventPostForCreateResponseDTO)
        assert isinstance(form.content_data, generated.EventPostEditableContentDataDTOModel)
        assert form.content_data.visibility == 1
        assert form.event is None
        assert form.cover_image is None

    # criterio: 08-C11
    def test_for_edit(self) -> None:
        form = EventPostForEdit.from_dict(load_payload("event_post_for_edit_response.json"))
        assert isinstance(form.raw, generated.GetEventPostForEditResponseDTO)
        assert form.occ_token == _OCC_TOKEN
        assert form.community_id == _COMMUNITY_ID
        assert form.custom_id == "POST-21269"
        assert form.content_data is not None
        assert form.content_data.title == "Riunione di prova"
        assert form.content_data.coverImageContentRef == "ref-1"
        assert form.event is not None
        assert form.event.start_at == _START
        assert form.cover_image is not None
        assert form.cover_image.contentRef == "ref-1"

    # criterio: 08-C11
    def test_for_copy(self) -> None:
        form = EventPostForCopy.from_dict(load_payload("event_post_for_copy_response.json"))
        assert isinstance(form.raw, generated.GetEventPostForCopyResponseDTO)
        assert form.occ_token == _OCC_TOKEN
        assert form.content_data is not None
        assert form.content_data.announcement is True
        assert form.event is not None
        assert form.event.location == "Sala A"

    # criterio: 08-C11
    def test_event_none_when_missing(self) -> None:
        data = load_payload("event_post_for_edit_response.json")
        del data["contentData"]["event"]
        form = EventPostForEdit.from_dict(data)
        assert form.event is None
        assert EventPostForEdit.from_dict({"occToken": 1}).content_data is None
