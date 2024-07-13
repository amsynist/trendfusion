from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from haystack import Pipeline
from haystack_integrations.document_stores.opensearch import \
    OpenSearchDocumentStore
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.external import AI_SEARCH_CORE_PROMPT, FA_USER_COLLECTION, BaseLLM
from app.main import app
from app.models import AISearchRequest, UserAttrs  # Import the Pydantic schema

router = APIRouter()


async def fetch_user_attrs(
    user_id: str, db: AsyncIOMotorDatabase, collection_name: str
) -> str:
    collection = db[collection_name]
    user_attrs = await collection.find_one({"_id": ObjectId(user_id)})
    if not user_attrs:
        raise HTTPException(status_code=404, detail="User not found")
    return UserAttrs(**user_attrs).to_str()


@router.post("/ai-search")
async def ai_search(
    request: AISearchRequest,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
    llm_client: BaseLLM = Depends(lambda: app.state.llm_client),
    open_search_retriver: Pipeline = Depends(lambda: app.state.open_search_retriever),
):
    user_id = request.user_id
    user_query = request.user_query

    # fetch user_attrs from mongo db
    user_attrs = await fetch_user_attrs(user_id, fa_db, FA_USER_COLLECTION)
    llm_client.system_prompt = AI_SEARCH_CORE_PROMPT

    # fetch trend_content [Optional]

    llm_query = f"""
    {user_attrs}
    User Query : {user_query}
    """
    open_search_query = await llm_client.query(llm_query)
    result = open_search_retriver.run(
        {
            "text_embedder": {"text": open_search_query},
            "bm25_retriever": {
                "query": open_search_query,
            },
            "ranker": {"query": user_query},
        }
    )

    return result["ranker"]
