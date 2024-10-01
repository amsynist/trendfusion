import base64
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import File, UploadFile
from pydantic import BaseModel, Field, field_validator


def isBase64(sb):
    if isinstance(sb, str):
        # If there's any unicode here, an exception will be thrown and the function will return false
        sb_bytes = bytes(sb, "ascii")
    elif isinstance(sb, bytes):
        sb_bytes = sb
    else:
        raise ValueError("Argument must be string or bytes")
    is_base_64 = base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    if not is_base_64:
        raise ValueError("Argument must be valid base64 string")
    return True


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
        return f"<wardrobe_recommend:{self.user_id}:{self.include_trendicles}:{self.product_id}>"


class BodyGramRequest(BaseModel):
    user_id: str
    front_image: UploadFile = File(...)
    right_image: UploadFile = File(...)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        try:
            ObjectId(v)
            return v
        except Exception as e:
            raise ValueError("`user_id` must be exact 12 characters in length") from e


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
