from typing import Any


class InteractaError(Exception):
    pass


class InteractaResponseError(InteractaError):
    def __init__(self, message: str, response: Any = None):
        super().__init__(message, response)
        self.message = message
        self.response = response


class InteractaLoginError(InteractaError):
    pass


class ObjectDoesNotFound(InteractaError):
    pass


class PostDoesNotFound(ObjectDoesNotFound):
    pass


class MultipleObjectsReturned(InteractaError):
    pass
