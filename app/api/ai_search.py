import json

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from haystack import Pipeline
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis import Redis

from app.external import FA_USER_COLLECTION, FA_PRODUCT_COLLECTION ,LOCAL_TRENDICLES_DIR, GroqLLM
from app.main import app
from app.models import AISearchRequest, UserAttrs, AIStyleReasoner, ProductDetails
from app.external.llm.prompt import *

router = APIRouter()
# ndb = NeuralDB()


'''
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
'''


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

async def fetch_product_details(
    product_id: str, db: AsyncIOMotorDatabase, collection_name: str
) -> str:
    collection = db[collection_name]
    product_details = await collection.find_one({"_id": ObjectId(product_id)})
    if not product_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="product not found"
        )
    return ProductDetails(**product_details).to_str()

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
        print(results)
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
    core_categories = await llm_client.chat(
        AI_SEARCH_CORE_PROMPT + [{"role": "user", "content": user_query}]
    )
    core_categories = json.loads(core_categories)
    print(core_categories)

    if core_categories.get("data",{}).get("category",None):
        llm_query = f"""
        {user_attrs}
        Extracted Features: {json.dumps(core_categories)}
        User Query: {user_query}
        """
        llm_client.system_prompt = FEATURE_GENERATOR_PROMPT

        open_search_query = await llm_client.chat(
            FEATURE_GENERATOR_PROMPT + [{"role": "user", "content": llm_query}]
            )
        open_search_query = json.loads(open_search_query)
        print(open_search_query)

        core_category = open_search_query["core_categories"]
        # open_search_query = str(open_search_query.get("data"))
        result = open_search_retriever.run(
        {
            "text_embedder": {"text": user_query},
            "bm25_retriever": {
                "query": user_query,
                "scale_score": 0 - 1,
                "top_k": 200,
                # "filters": {
                #     "field": "category",
                #     "operator": "in",
                #     "value": core_categories["core_categories"],
                # }, 
                "filters":{
                    "operator": "OR",
                    "conditions": [
                        {"field": "meta.category", "operator": "in", "value": core_categories["core_categories"]},
                        {"field": "meta.brand", "operator": "in", "value": [open_search_query.get("data").get("brand")]},
                        {"field": "meta.colors", "operator": "in", "value": [open_search_query.get("data").get("color")]},

                    ],
                },
                "custom_query":{
                            "query": {
                                "bool": {
                                    "must": [{"multi_match": {
                                        "query": user_query,                 
                                        "type": "most_fields",
                                        "fields": core_categories["weightage"]}}],          
                                }
                            }
                        } 
            },
            "ranker": {
                "query": user_query,
                "top_k": 500,
            },
        }
    )       

    
    else:
        result = {"ranker":{}}
    

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
        "products": sorted(results, key=lambda x: x["score"], reverse=True),
        "info": {
            "page": user_request.page,
            "page_size": user_request.page_size,
            "count": len(results),
        },
    }


@router.post("/style_reasoner", status_code=status.HTTP_200_OK)
async def style_reasoner(user_request: AIStyleReasoner,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
    llm_client: GroqLLM = Depends(lambda: app.state.llm_client),
    open_search_retriever: Pipeline = Depends(lambda: app.state.open_search_retriever),
    redis: Redis = Depends(lambda: app.state.redis),):
    
    user_id = user_request.user_id
    product_id = user_request.product_id
    print(user_id,product_id)

    product_details = await fetch_product_details(product_id, fa_db, FA_PRODUCT_COLLECTION)
    user_attrs = await fetch_user_attrs(user_id, fa_db, FA_USER_COLLECTION)
    llm_client.system_prompt = STYLE_REASONER_PROMPT
    core_recommendations = await llm_client.chat(
        STYLE_REASONER_PROMPT + [{"role": "user", "content": 
                                  f"""{user_attrs} + "\n\n" + {product_details}"""}],
    )
    core_recommendations = json.loads(core_recommendations)
    print(core_recommendations)
    return {
        "user_id": user_id,
        "Product_id":product_id,
        "Recommendations":core_recommendations["recommendations"]
    }