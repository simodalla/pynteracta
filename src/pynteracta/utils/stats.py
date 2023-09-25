from ..enums import InteractaLoginProviderEnum
from ..schemas.models import ListSystemUsersElement
from .models import UsersStats


def calculate_stats_users(users: list[ListSystemUsersElement]):
    providers = [provider.value for provider in InteractaLoginProviderEnum]
    data = {f"provider_{provider}": [] for provider in providers}
    data.update({"ids": []})
    for user in users:
        data["ids"].append(user.id)
        for provider in user.login_providers:
            data[f"provider_{provider}"].append(user.id)
    assert len(data["ids"]) == len(users)
    return UsersStats(**data)
