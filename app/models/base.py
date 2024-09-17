from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


class WardrobeRecommendRequest(BaseModel):
    user_id: str
    product_id: str
    include_trendicles: bool = False

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        try:
            ObjectId(v)
            return v
        except Exception as e:
            raise ValueError("`user_id` must be exact 12 characters in length") from e

    def __str__(self):
        return f"<wardrobe_recommend:{self.user_id}:{self.include_trendicles}:{self.existing_wardrobe_id}>"


class Product(BaseModel):
    category: str = ""
    color: str = ""
    title: str = ""
    pattern: str = ""


class SizeRecommendRequest(BaseModel):
    user_id: str = "guest"
    product_id: str
    product_title: str
    user_measurements: List[Dict[str, Any]]

    @property
    def measurements(self) -> Dict[str, str]:
        return {
            um["name"]: f"{um['value'] * 0.0393701:.2f} inches"
            for um in self.user_measurements
        }

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        try:
            ObjectId(v)
            return v
        except Exception as e:
            raise ValueError("`user_id` must be exact 12 characters in length") from e

    def __str__(self):
        return f"<size_recommend:{self.user_id}:{self.product_id}>"


class AISearchRequest(BaseModel):
    user_id: str
    user_query: str
    include_trendicles: bool = False
    page: int = 1
    page_size: int = 2

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        try:
            ObjectId(v)
            return v
        except Exception as e:
            raise ValueError("`user_id` must be exact 12 characters in length") from e

    def __str__(self):
        return f"ai_search-{self.user_id}-{self.user_query.strip()}-{self.include_trendicles}"


class UserAttrs(BaseModel):
    _id: ObjectId
    skin_color: Optional[str] = Field(default="NA")
    height: Optional[int] = None  # Defaults to None if not provided
    weight: Optional[int] = None  # Defaults to None if not provided
    age: Optional[int] = None  # Defaults to None if not provided
    facial_attrs: Optional[List[str]] = Field(default_factory=list)
    physical_attrs: Optional[List[str]] = Field(default_factory=list)

    def to_str(self):
        return f"""
        ----------- User Attributes ----------
        Skin Color     : {self.skin_color}
        Height         : {self.height}
        Weight         : {self.weight}
        Age            : {self.age}
        Facial Attrs   : {''.join(self.facial_attrs) if self.facial_attrs else 'NA'}
        Phsycial Attrs : {''.join(self.physical_attrs) if self.physical_attrs else 'NA'}
        """
