"""Common error handling for HTTP routes."""

from fastapi import HTTPException


def raise_not_found(detail: str) -> None:
    """
    Raise 404 Not Found exception.

    Args:
        detail: Error message

    Raises:
        HTTPException: 404 error

    """
    raise HTTPException(status_code=404, detail=detail)


def raise_bad_request(detail: str) -> None:
    """
    Raise 400 Bad Request exception.

    Args:
        detail: Error message

    Raises:
        HTTPException: 400 error

    """
    raise HTTPException(status_code=400, detail=detail)


def raise_internal_error(detail: str) -> None:
    """
    Raise 500 Internal Server Error exception.

    Args:
        detail: Error message

    Raises:
        HTTPException: 500 error

    """
    raise HTTPException(status_code=500, detail=detail)


def raise_unauthorized(detail: str = "Unauthorized") -> None:
    """
    Raise 401 Unauthorized exception.

    Args:
        detail: Error message

    Raises:
        HTTPException: 401 error

    """
    raise HTTPException(status_code=401, detail=detail)


def raise_forbidden(detail: str = "Forbidden") -> None:
    """
    Raise 403 Forbidden exception.

    Args:
        detail: Error message

    Raises:
        HTTPException: 403 error

    """
    raise HTTPException(status_code=403, detail=detail)
