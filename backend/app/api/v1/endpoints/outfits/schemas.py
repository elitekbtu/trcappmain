from typing import List, Optional
from pydantic import BaseModel, root_validator, conint, Field
from datetime import datetime


class OutfitItemBase(BaseModel):
    id: int
    name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None

    class Config:
        orm_mode = True


class OutfitCreate(BaseModel):
    name: str
    style: str
    description: Optional[str] = None
    collection: Optional[str] = None
    top_ids: List[int] = []
    bottom_ids: List[int] = []
    footwear_ids: List[int] = []
    accessories_ids: List[int] = []
    fragrances_ids: List[int] = []

    @root_validator
    def _at_least_one_category(cls, values):
        if not any(values.get(field) for field in ["top_ids", "bottom_ids", "footwear_ids",
                                                 "accessories_ids", "fragrances_ids"]):
            raise ValueError("At least one outfit category must contain items")
        return values


class OutfitUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    description: Optional[str] = None
    collection: Optional[str] = None
    top_ids: Optional[List[int]] = None
    bottom_ids: Optional[List[int]] = None
    footwear_ids: Optional[List[int]] = None
    accessories_ids: Optional[List[int]] = None
    fragrances_ids: Optional[List[int]] = None


class OutfitOut(BaseModel):
    id: int
    name: str
    style: str
    description: Optional[str] = None
    collection: Optional[str] = None
    owner_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tops: List[OutfitItemBase] = []
    bottoms: List[OutfitItemBase] = []
    footwear: List[OutfitItemBase] = []
    accessories: List[OutfitItemBase] = []
    fragrances: List[OutfitItemBase] = []
    total_price: Optional[float] = None

    class Config:
        orm_mode = True


class OutfitCommentCreate(BaseModel):
    content: str
    rating: Optional[conint(ge=1, le=5)] = None


class OutfitCommentOut(OutfitCommentCreate):
    id: int
    user_id: int
    created_at: Optional[datetime]
    likes: Optional[int] = 0

    class Config:
        orm_mode = True


class OutfitGenerationRequest(BaseModel):
    style: str = Field(..., description="Style of outfit (casual, formal, sporty, etc.)")
    occasion: str = Field(..., description="Occasion for the outfit (work, party, date, etc.)")
    budget: Optional[float] = Field(None, description="Maximum budget for the outfit")
    preferred_colors: Optional[List[str]] = Field(None, description="List of preferred colors")
    required_categories: Optional[List[str]] = Field(None, description="Required item categories")
    collection: Optional[str] = Field(None, description="Specific collection to use")


class OutfitGenerationResponse(BaseModel):
    outfit_id: int
    outfit_name: str
    description: str
    total_price: float
    style_notes: str
    selected_items: List[int]


class OutfitEvaluationResponse(BaseModel):
    outfit_id: int
    overall_score: Optional[int] = None
    color_harmony_score: Optional[int] = None
    style_consistency_score: Optional[int] = None
    feedback: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    error: Optional[str] = None


class OutfitVariationRequest(BaseModel):
    num_variations: int = Field(3, description="Number of variations to generate")


class OutfitVariation(BaseModel):
    name: str
    description: str
    selected_items: List[int]
    changed_categories: List[str]


class OutfitVariationResponse(BaseModel):
    variations: List[OutfitVariation]


class SeasonalOutfitRequest(BaseModel):
    season: str = Field(..., description="Season (winter, summer, spring, autumn)")
    style: str = Field(..., description="Style preference")
    limit: int = Field(5, description="Number of outfits to generate")


class SeasonalOutfit(BaseModel):
    name: str
    description: str
    selected_items: List[int]
    weather_notes: str


class SeasonalOutfitResponse(BaseModel):
    seasonal_outfits: List[SeasonalOutfit]


class OutfitGenerationFromItemsRequest(BaseModel):
    selected_item_ids: List[int] = Field(..., description="List of selected item IDs")
    style: str = Field(..., description="Style for the outfit")
    occasion: str = Field(..., description="Occasion for the outfit")
    additional_categories: Optional[List[str]] = Field(None, description="Additional categories to include")


class RandomOutfitGenerationRequest(BaseModel):
    style: str = Field(..., description="Style for the outfit")
    occasion: str = Field(..., description="Occasion for the outfit")
    budget: Optional[float] = Field(None, description="Maximum budget")
    collection: Optional[str] = Field(None, description="Collection to use") 