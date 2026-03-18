from pydantic import BaseModel, Field


class BaseResponseSchema(BaseModel):
    """Base class for all API response schemas."""

    success: bool = Field(default=True, example=True)


class ErrorResponse(BaseResponseSchema):
    """Standard error response body."""

    success: bool = Field(default=False, example=False)
    error: str = Field(example="Resource not found")
    code: str = Field(example="NOT_FOUND")
