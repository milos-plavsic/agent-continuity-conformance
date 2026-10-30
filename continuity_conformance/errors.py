"""Typed failures exposed by the package."""

class ContinuityError(Exception):
    """Base class for expected continuity failures."""

class OperationNotFound(ContinuityError):
    """The requested operation does not exist."""

class InvalidTransition(ContinuityError):
    """A lifecycle transition is not valid from the current state."""

class StaleGeneration(ContinuityError):
    """The caller's ownership generation is no longer current."""

class ProviderUnavailable(ContinuityError):
    """The provider cannot currently establish the request status."""

class ResponseLost(ContinuityError):
    """The provider admitted a request but its response was lost."""
