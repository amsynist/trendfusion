import json

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis import Redis

from app.external import FA_SIZE_CHART_COLLECTION
from app.main import app
from app.models import SizeRecommendRequest

load_dotenv()

router = APIRouter()
# ndb = NeuralDB()


# Define size recommendation prompt template
SIZE_RECOMMEND_TEMPLATE = """
You are a clothing size assistant. I'll provide you the body measurements, size chart of the product, and product name. Based on all these parameters you just have to reply in a single word. That word would be the size of the clothing that would fit on the user.

*Body Measurements* : {measurements}

*Product Name* : {product_title}

*Size Chart* : {size_chart}
"""

# Initialize ChatGroq model
prompt = PromptTemplate(
    input_variables=["measurements", "product_title", "size_chart"],
    template=SIZE_RECOMMEND_TEMPLATE,
)


async def fetch_product_chart(
    product_id: str, fa_db: AsyncIOMotorDatabase
) -> dict | None:
    """Fetch the size chart for a given product from the database."""
    size_chart = await fa_db[FA_SIZE_CHART_COLLECTION].find_one(
        {"product_id": product_id}
    )
    return size_chart if size_chart else None


@router.post("/recommended_size", status_code=status.HTTP_200_OK)
async def size_recommend(
    size_recommend_request: SizeRecommendRequest,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
    redis: Redis = Depends(lambda: app.state.redis),
):
    """Get the recommended clothing size based on user measurements and product size chart."""
    llm = ChatGroq(model="llama3-8b-8192", temperature=0.1, stop_sequences=["."])
    chain = LLMChain(llm=llm, prompt=prompt, verbose=True)
    # Check for cached response first
    cache_key = str(size_recommend_request)
    cached_result = redis.get(cache_key)

    if cached_result:
        print(f"Cached response found: {cache_key}")
        return json.loads(str(cached_result))

    # Fetch size chart from the database
    chart = await fetch_product_chart(size_recommend_request.product_id, fa_db)
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Size chart not found for the given product",
        )

    # Get the recommended size using the LLM chain
    recommended_size = chain.invoke(
        {
            "measurements": size_recommend_request.measurements,
            "product_title": size_recommend_request.product_title,
            "size_chart": chart,
        }
    )

    # Cache the response on first request
    redis.set(cache_key, json.dumps(recommended_size), ex=10)
    return recommended_size
