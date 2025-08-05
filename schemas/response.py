from fastapi import FastAPI
from pydantic import BaseModel
from typing import Generic, Optional, TypeVar
from pydantic.generics import GenericModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: int
    message: str

class APIResponse(GenericModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None