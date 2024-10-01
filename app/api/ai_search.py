import json

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from haystack import Pipeline
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis import Redis

from app.external import FA_USER_COLLECTION, LOCAL_TRENDICLES_DIR, GroqLLM
from app.main import app
from app.models import AISearchRequest, UserAttrs

router = APIRouter()
# ndb = NeuralDB()

AI_SEARCH_CORE_PROMPT = """
You are an expert men's only fashion recommender. 
You have to recommend clothes for the user based on their profile and user data given, and you get optional trend-related information which you could use for generating query.
Return the proper description of the cloth in less than 20 words. 
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


def paginate_documents(redis, cache_key, results=[], page=1, page_size=10):
    """
    Paginate through the retrieved documents.

    """
    start = (page - 1) * page_size
    end = start + page_size
    if not results:
        cached_results = redis.get(cache_key)
        if cached_results:
            results = json.loads(str(cached_results))
            if not results:
                return []
            return results[start:end] if len(results) > end else results[start:]
    return results[start:end] if len(results) > end else results[start:]


@router.post("/search", status_code=status.HTTP_200_OK)
async def ai_search(
    user_request: AISearchRequest,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
    llm_client: GroqLLM = Depends(lambda: app.state.llm_client),
    open_search_retriever: Pipeline = Depends(lambda: app.state.open_search_retriever),
    redis: Redis = Depends(lambda: app.state.redis),
):
    user_id = user_request.user_id
    user_query = user_request.user_query

    # Check for cached response first
    cache_key = str(user_request)
    # check for cache if results are already loaded else do a fresh query
    if results := paginate_documents(
        redis, cache_key, [], user_request.page, user_request.page_size
    ):
        print(f"Cached response found: {cache_key}")
        return {
            "products": results,
            "info": {
                "page": user_request.page,
                "page_size": user_request.page_size,
                "count": len(results),
            },
        }

    # Fetch user attributes from MongoDB
    user_attrs = await fetch_user_attrs(user_id, fa_db, FA_USER_COLLECTION)

    # Fetch trend content (optional)
    trends = "No Trend Knowledge"
    if user_request.include_trendicles:
        trends = fetch_trend_knowledge(user_query + user_attrs)

    llm_client.system_prompt = AI_SEARCH_CORE_PROMPT
    llm_query = f"""
    {user_attrs}
    Trend Knowledge Base: {trends}
    User Query: {user_query}
    """
    core_categories = await llm_client.chat(
        messages + [{"role": "user", "content": user_query}]
    )

    open_search_query = await llm_client.query(llm_query)

    result = open_search_retriever.run(
        {
            "text_embedder": {"text": open_search_query},
            "bm25_retriever": {
                "query": open_search_query,
                "scale_score": 0 - 1,
                "top_k": 200,
                "filters": {
                    "field": "meta.category",
                    "operator": "in",
                    "value": json.loads(core_categories)["core_categories"],
                },
            },
            "ranker": {
                "query": user_query,
                "top_k": 500,
            },
        }
    )

    # Cache the response on first request
    _results = [doc.to_dict() for doc in result["ranker"].get("documents", []) or []]
    redis.set(cache_key, json.dumps(_results), ex=300)  # Cache for 1 hour
    results = paginate_documents(
        redis, cache_key, _results, user_request.page, user_request.page_size
    )
    print(f"Cached response for {len(_results)} products : {cache_key}")
    if not results:
        return {"products": []}
    return {
        "products": results,
        "info": {
            "page": user_request.page,
            "page_size": user_request.page_size,
            "count": len(results),
        },
    }
