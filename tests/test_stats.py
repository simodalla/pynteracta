from devtools import debug

from pynteracta.schemas.models import ListSystemUsersElement
from pynteracta.utils.models import UsersStats
from pynteracta.utils.stats import calculate_stats_users


def test_stats():
    users = [
        ListSystemUsersElement(id=1, login_providers=["google"]),
        ListSystemUsersElement(id=2, login_providers=["google"]),
        ListSystemUsersElement(id=3, login_providers=["microsoft"]),
        ListSystemUsersElement(id=4, login_providers=["custom"]),
    ]
    stats = calculate_stats_users(users=users)
    assert isinstance(stats, UsersStats)
    assert len(stats.provider_google) == 2
    assert len(stats.provider_microsoft) == 1
    assert len(stats.provider_custom) == 1

    debug(stats.model_dump())
