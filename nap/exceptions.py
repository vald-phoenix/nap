from __future__ import unicode_literals

class InvalidStatusError(ValueError):

    ERROR_MSG = "Expected status code in %s, got %s at %s"

    def __init__(self, valid_statuses, response):
        self.valid_statuses = valid_statuses
        self.response = response
        msg = self.ERROR_MSG % (valid_statuses, response.status_code, response.url)
        super(InvalidStatusError, self).__init__(msg)


class EmptyResponseError(Exception):
    pass


class DoesNotExist(Exception):
    pass


class BadRequestError(InvalidStatusError):

    def __init__(self, response, errors):
        self.response = response
        self.errors = errors
        super(InvalidStatusError, self).__init__(errors)
