from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.exceptions import DomainException


async def domain_exception_handler(_: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(DomainException)(domain_exception_handler)
