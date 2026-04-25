from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Для создания ---
class PartCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Название запчасти")
    part_number: str = Field(..., description="Артикул запчасти")
    price: float = Field(..., gt=0, description="Цена должна быть больше 0")
    description: Optional[str] = None

# --- Для обновления (полное) ---
class PartUpdate(BaseModel):
    name: str
    part_number: str
    price: float
    description: Optional[str] = None

# --- Для обновления (частичное) ---
class PartPatch(BaseModel):
    name: Optional[str] = None
    part_number: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None

# --- Ответ (исключая чувствительные данные) ---
class PartResponse(BaseModel):
    id: int
    name: str
    part_number: str
    price: float
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Пагинация ---
class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PartsListResponse(BaseModel):
    data: List[PartResponse]
    meta: PaginationMeta