import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    def __init__(
        self,
        code: str,
        status_code: int,
        detail: str,
        field: str | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.detail = detail
        self.field = field
        super().__init__(detail)


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        body: dict = {"detail": exc.detail, "code": exc.code}
        if exc.field:
            body["field"] = exc.field
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
        return JSONResponse(
            status_code=422,
            content={
                "detail": first_error["msg"],
                "code": "VALIDATION_ERROR",
                "field": field or None,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado")
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor", "code": "INTERNAL_ERROR"},
        )
