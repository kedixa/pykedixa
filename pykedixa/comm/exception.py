__all__ = [
    'CommException',
    'AdaptorException',
    'AdaptorEofError',
    'TransformerException',
    'TransformerEofError',
    'BadMessage',
]


class CommException(Exception):
    def __init__(self, what: str, **kwargs):
        self._what: str = what
        self._kwargs    = kwargs

    def __str__(self) -> str:
        return f'{self._what} kwargs:{self._kwargs}'

    def what(self) -> str:
        return self._what

    def get(self, key: str):
        return self._kwargs.get(key, None)


class AdaptorException(CommException):
    pass


class AdaptorEofError(AdaptorException):
    pass


class TransformerException(CommException):
    pass


class TransformerEofError(TransformerException):
    pass


class BadMessage(CommException):
    pass


