class InteractaError(Exception):
    pass


class InteractaResponseError(InteractaError):
    pass


class InteractaLoginError(InteractaError):
    pass


class ObjectDoesNotFound(InteractaError):
    pass
    # def __init__(self, message, response=None):
    #     super().__init__(self, message, response)
    #     self.message = message
    #     self.response = response


class PostDoesNotFound(ObjectDoesNotFound):
    pass


class MultipleObjectsReturned(InteractaError):
    pass
