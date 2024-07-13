from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class AISearchRequest(BaseModel):
    user_id: str
    user_query: str


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
