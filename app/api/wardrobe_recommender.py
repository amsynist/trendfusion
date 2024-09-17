import json
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from haystack import Pipeline
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis import Redis
from thirdai.neural_db import NeuralDB

from app.external import (
    FA_USER_COLLECTION,
    FA_WARDROBE_COLLECTION,
    LOCAL_TRENDICLES_DIR,
    BaseLLM,
)
from app.main import app
from app.models import Product, UserAttrs, WardrobeRecommendRequest

router = APIRouter()
# ndb = NeuralDB()

WARDROBE_RECOMMEND_PROMPT = """

here is my product in my cart ,
now suggest pr gemerate categories that suits and compleste this 

black shirt ->  lm -> jeans,shorts,tshirts -> open_search

jeans - white - grey -
shorts  - 
tshirts 
You are an expert men's only fashion recommender. 
You should recommend based on wardrobe items and likely going to buy the products we recommend by your search query you generate
Return the proper description of the cloths that likely going to buy based on his wardrobe items and categories in less than 20 words. 
The description must contain category, color, and pattern only. 
Please return answer in query to search in OpenSearch for listing products to user and ensure your response only contains the query and nothing else.
"""
messages = [
    {
        "role": "system",
        "content": "Just return list of core categories from the query \nOutput : JSON",
    },
    {"role": "user", "content": "black formal trousers with subtle texture pattern"},
    {
        "role": "assistant",
        "content": '{"core_categories": ["Fashion", "Clothing", "Trousers", "Formal Wear", "Textured Fabric"]}',
    },
    {"role": "user", "content": "black shirts  with subtle solid pattern"},
    {
        "role": "assistant",
        "content": '{"core_categories": ["Fashion", "Clothing", "Shirts", "Solid Pattern", "Formal Wear"]}',
    },
]


async def fetch_user_attrs(
    user_id: str, db: AsyncIOMotorDatabase, collection_name: str
) -> str:
    collection = db[collection_name]
    user_attrs = await collection.find_one({"_id": ObjectId(user_id)})
    if not user_attrs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserAttrs(**user_attrs).to_str()


def fetch_trend_knowledge(query: str) -> str:
    _ndb = ndb.from_checkpoint(LOCAL_TRENDICLES_DIR)
    results = _ndb.search(query, top_k=1)
    trends = "\n".join(result.text for result in results)
    return trends or "No Trend Knowledge"


async def fetch_wardrobe_items(
    wardrobe_id: str, db: AsyncIOMotorDatabase, collection_name: str
) -> List[Product]:
    collection = db[collection_name]
    wardrobe = await collection.find_one({"_id": ObjectId(wardrobe_id)})
    if not wardrobe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wardrobe not found"
        )
    return [Product(**item) for item in wardrobe.get("products", [])]


@router.post("/recommendations", status_code=status.HTTP_200_OK)
async def wardrobe_recommendations(
    wardrobe_request: WardrobeRecommendRequest,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
    llm_client: BaseLLM = Depends(lambda: app.state.llm_client),
    open_search_retriever: Pipeline = Depends(lambda: app.state.open_search_retriever),
    redis: Redis = Depends(lambda: app.state.redis),
):
    user_id = wardrobe_request.user_id
    wardrobe_id = wardrobe_request.existing_wardrobe_id

    # Check for cached response first
    cache_key = str(wardrobe_request)
    cached_result = redis.get(cache_key)

    # Fetch wardrobe items from MongoDB
    wardrobe_item = await fetch_wardrobe_items(
        wardrobe_id, fa_db, FA_WARDROBE_COLLECTION
    )
    # Generate query based on unique categories of wardrobe items
    wardrobe_categories = set(
        f"{item.title}-{item.category}" for item in wardrobe_items
    )
    wardrobe_query = " ".join(wardrobe_categories)
    if cached_result:
        print(f"Cached response found: {cache_key}")
        return json.loads(str(cached_result))

    # Fetch user attributes from MongoDB
    user_attrs = await fetch_user_attrs(user_id, fa_db, FA_USER_COLLECTION)

    # Fetch trend content (optional)
    trends = "No Trend Knowledge"
    if wardrobe_request.include_trendicles:
        trends = fetch_trend_knowledge(wardrobe_query + user_attrs)

    llm_client.system_prompt = WARDROBE_RECOMMEND_PROMPT
    llm_query = f"""
    {user_attrs}
    Trend Knowledge Base: {trends}
    Wardrobe Items: {wardrobe_query}
    """

    open_search_query = await llm_client.query(llm_query)
    print(open_search_query)
    core_categories = await llm_client.chat(
        messages + [{"role": "user", "content": open_search_query}]
    )
    print(core_categories)

    result = open_search_retriever.run(
        {
            "text_embedder": {"text": open_search_query},
            "bm25_retriever": {
                "query": open_search_query,
                "filters": {
                    "field": "meta.category",
                    "operator": "in",
                    "value": json.loads(core_categories)["core_categories"],
                },
            },
            "ranker": {"query": wardrobe_query},
        }
    )

    # Cache the response on first request
    results = [doc.to_dict() for doc in result["ranker"].get("documents", []) or []]
    redis.set(cache_key, json.dumps(results), ex=3600)  # Cache for 1 hour
    print(f"Cached response: {cache_key}")

    return results
