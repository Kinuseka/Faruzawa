class FaruzawaGlobalExc(BaseException):
    """
    Dev notes: Use this class for arbitrary error raise, however I recommend creating a specific exception class
    that inherits this class for specific exception handling to prevent cluttering and ensure readabiltiy
    """
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message)
        self.message = message
        self.parent = parent

class ScrapingError(FaruzawaGlobalExc):
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message, parent)

class NotFound(FaruzawaGlobalExc):
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message, parent)

class NotFoundPagination(ScrapingError):
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message, parent)

class NotFoundEpisode(ScrapingError):
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message, parent)

class VideoNotFound(NotFound):
    def __init__(self, message="An Error has occured", parent=None) -> None:
        super().__init__(message, parent)