from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.external import TRENDICLES_CORE_COLLECTION, TRENDICLES_NEURAL_ID

router = APIRouter()
from app.external import update_local_neural_trendicles
from app.main import app


@router.post("/refresh_trendicles")
async def refresh_trendicles(
    background_tasks: BackgroundTasks,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
):
    collection = fa_db[TRENDICLES_CORE_COLLECTION]
    neural_core = await collection.find_one({"_id": ObjectId(TRENDICLES_NEURAL_ID)})
    if neural_core:

        neural_s3_key = neural_core["trendicles_index_zip_s3_key"]
        background_tasks.add_task(update_local_neural_trendicles, neural_s3_key)
        return {"message": "Trendicles Refreshing Initiated ."}
    return {"message": "Failed to Refresh,No Neural Core doc !"}
