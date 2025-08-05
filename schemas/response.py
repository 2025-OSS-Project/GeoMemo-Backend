from typing import Generic, TypeVar, Optional, Union, List
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class APIResponse(GenericModel, Generic[T]):
    success: bool
    data: Optional[Union[T, List[T]]] = None
    error: Optional[str] = None
