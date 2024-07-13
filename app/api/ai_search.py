from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.external import FA_USER_COLLECTION, get_fa_connection
from app.models import AISearchRequest, UserAttrs  # Import the Pydantic schema

router = APIRouter()


def fetch_user_attrs(user_id: str, db: Database, collection_name: str) -> str:
    collection = db[collection_name]
    user_attrs = collection.find_one({"_id": ObjectId(user_id)})
    print(user_attrs)
    if not user_attrs:
        raise HTTPException(status_code=404, detail="User not found")
    return UserAttrs(**user_attrs).to_str()


@router.post("/ai-search")
def ai_search(request: AISearchRequest, fa_db: Database = Depends(get_fa_connection)):
    user_id = request.user_id
    user_query = request.user_query

    # fetch user_attrs from mongo db
    user_attrs = fetch_user_attrs(user_id, fa_db, FA_USER_COLLECTION)

    # fetch trend_content [Optional]

    # Example processing logic
    # Replace this with your actual search logic

    return user_attrs
