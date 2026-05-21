class ApplicationError(Exception):
    pass


class BookAlreadyExists(ApplicationError):
    pass


class MemberAlreadyExists(ApplicationError):
    pass
