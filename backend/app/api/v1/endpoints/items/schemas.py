from typing import List, Optional
from pydantic import BaseModel, conint, confloat
from datetime import datetime


class ItemCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    price: Optional[confloat(gt=0)] = None
    category: Optional[str] = None
    clothing_type: Optional[str] = None
    article: Optional[str] = None
    size: Optional[str] = None
    style: Optional[str] = None
    collection: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    price: Optional[confloat(gt=0)] = None
    category: Optional[str] = None
    clothing_type: Optional[str] = None
    article: Optional[str] = None
    size: Optional[str] = None
    style: Optional[str] = None
    collection: Optional[str] = None


class VariantBase(BaseModel):
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str] = None
    stock: conint(ge=0) = 0
    price: Optional[confloat(gt=0)] = None


class VariantCreate(VariantBase):
    pass


class VariantUpdate(BaseModel):
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str] = None
    stock: Optional[conint(ge=0)] = None
    price: Optional[confloat(gt=0)] = None


class VariantOut(VariantBase):
    id: int

    class Config:
        orm_mode = True


class ItemOut(ItemCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    style: Optional[str] = None
    collection: Optional[str] = None
    image_urls: Optional[List[str]] = None
    variants: Optional[List[VariantOut]] = None
    is_favorite: Optional[bool] = None
    
    # Новые поля для Lamoda
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_sku: Optional[str] = None
    old_price: Optional[float] = None

    class Config:
        orm_mode = True


class CommentCreate(BaseModel):
    content: str
    rating: Optional[conint(ge=1, le=5)] = None  # 1-5


class CommentOut(CommentCreate):
    id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: Optional[datetime]
    likes: Optional[int] = 0

    class Config:
        orm_mode = True


# Images


class ItemImageOut(BaseModel):
    id: int
    image_url: str
    position: Optional[int] = None

    class Config:
        orm_mode = True


# Lamoda Import


class LamodaImportRequest(BaseModel):
    query: str
    limit: Optional[int] = 20
    domain: Optional[str] = "kz"
    
    class Config:
        schema_extra = {
            "example": {
                "query": "nike кроссовки",
                "limit": 10,
                "domain": "kz"
            }
        }


class LamodaImportResponse(BaseModel):
    success: bool
    message: str
    imported_count: int
    items: List[ItemOut]
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully imported 5 items from Lamoda",
                "imported_count": 5,
                "items": []
            }
        } 