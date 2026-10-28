"""Application exceptions translated into HTTP responses by the API."""


class ConflictError(Exception):
    """A stale command or a reused event identifier cannot be applied."""


class VisitNotFoundError(Exception):
    """The requested visit does not exist."""


class WorkflowError(ValueError):
    """An operational transition would violate the workflow."""


class ReportFormatError(ValueError):
    """A report status event cannot be normalized safely."""
