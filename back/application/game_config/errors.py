class ApplicationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownCommandError(ApplicationError):
    pass


class CommandNotAllowedError(ApplicationError):
    pass


class InvalidCommandPayloadError(ApplicationError):
    pass
