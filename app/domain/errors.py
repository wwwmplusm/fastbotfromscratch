class DomainError(Exception):
    pass


class InvalidWeight(DomainError):
    def __init__(self, value: object) -> None:
        super().__init__(f"weight out of range: {value}")
        self.value = value


class InvalidTransition(DomainError):
    pass


class EmptyEntry(DomainError):
    pass


class ItemNotFound(DomainError):
    pass
