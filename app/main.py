import logging
from contextlib import asynccontextmanager

import redis
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson import ObjectId

scheduler = AsyncIOScheduler()
from fastapi import FastAPI
from thirdai import licensing

from app.external import (
    THIRD_AI_KEY,
    TRENDICLES_CORE_COLLECTION,
    TRENDICLES_NEURAL_ID,
    update_local_neural_trendicles,
)

# licensing.activate(THIRD_AI_KEY)

jobstores = {"default": MemoryJobStore()}

# Initialize an AsyncIOScheduler with the jobstore
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Asia/Kolkata")


# Job running daily at 23:44:00
@scheduler.scheduled_job("cron", day_of_week="mon-sun", hour=0, minute=0, second=0)
async def daily_refresh_trendicles():
    print("Trigger Local Neural Trendicles Refreshing ..")
    fa_db = await get_fa_connection()
    collection = fa_db[TRENDICLES_CORE_COLLECTION]
    neural_core = await collection.find_one({"_id": ObjectId(TRENDICLES_NEURAL_ID)})
    neural_s3_key = neural_core["trendicles_index_zip_s3_key"]
    # load neural db
    update_local_neural_trendicles(neural_s3_key)
    print("Finished Local Neural Trendicles Refreshing.")


from app.external import (
    REDIS_HOST,
    REDIS_PORT,
    get_fa_connection,
    get_groq_llm,
    get_open_search_db,
    get_open_search_retriver,
)

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # loa
    # Initialize your resources here
    fa_db = await get_fa_connection()
    llm_client = await get_groq_llm()
    open_search_db = await get_open_search_db()
    open_search_retriever = await get_open_search_retriver(open_search_db)

    # Attach resources to the app state
    app.state.fa_db = fa_db
    app.state.llm_client = llm_client
    app.state.open_search_db = open_search_db
    app.state.open_search_retriever = open_search_retriever
    app.state.redis = redis.Redis(
        host=REDIS_HOST, port=int(REDIS_PORT), db=0, decode_responses=True
    )
    collection = fa_db[TRENDICLES_CORE_COLLECTION]
    neural_core = await collection.find_one({"_id": ObjectId(TRENDICLES_NEURAL_ID)})
    neural_s3_key = neural_core["trendicles_index_zip_s3_key"]
    # load neural db
    # update_local_neural_trendicles(neural_s3_key)
    scheduler.start()
    yield

    # Cleanup your resources here


app = FastAPI(lifespan=lifespan)


from app.api import ai_search  # Import API routers
from app.api import refresh_trendicles, size_recommender, wardrobe_recommender

# Include API routers with versioning
app.include_router(ai_search.router, prefix="/v1/ai")
app.include_router(refresh_trendicles.router, prefix="/v1/internal")
app.include_router(size_recommender.router, prefix="/v1/products")
app.include_router(wardrobe_recommender.router, prefix="/v1/wardrobe")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
