from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """Structured application error returned as consistent JSON."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


def bad_request(message: str, code: str = "bad_request", details: Any = None) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, code, message, details)


def unauthorized(message: str = "Unauthorized", code: str = "unauthorized") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, code, message)


def forbidden(message: str = "Forbidden", code: str = "forbidden") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, code, message)


def not_found(message: str = "Not found", code: str = "not_found") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, code, message)


def conflict(message: str, code: str = "conflict") -> AppError:
    return AppError(status.HTTP_409_CONFLICT, code, message)


def too_many_requests(message: str = "Too many requests", code: str = "rate_limited") -> AppError:
    return AppError(status.HTTP_429_TOO_MANY_REQUESTS, code, message)


def service_unavailable(message: str, code: str = "service_unavailable", details: Any = None) -> AppError:
    return AppError(status.HTTP_503_SERVICE_UNAVAILABLE, code, message, details)


def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        code = getattr(exc, "code", None) or {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
        }.get(exc.status_code, "http_error")
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(status_code=exc.status_code, content=_error_body(code, detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            details.append({"field": loc, "message": err.get("msg", "Invalid value")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("validation_error", "Validation failed", details),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "Internal server error"),
        )
