import base64
from datetime import datetime
from typing import Dict, Optional,Any

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.main import app

router = APIRouter()

import boto3

from app.external import (
    BODY_GRAM_API_KEY,
    BODY_GRAM_BUCKET,
    BODY_GRAM_ORG_ID,
    BODY_GRAM_SCAN_COLLECTION,
    FA_USER_COLLECTION,
)

S3 = boto3.client("s3")

import httpx
from fastapi import HTTPException


@router.post("/scan")
async def save_scan_images(
    user_id: str,
    front_image: UploadFile = File(...),
    right_image: UploadFile = File(...),
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
) -> Optional[Dict[str, str]]:
    """
    Save front and right images for a user to S3 and store the image metadata in MongoDB.

    This endpoint uploads the front and right images to a predefined S3 bucket and updates
    the user's collection with the S3 paths of the uploaded images.

    Parameters:
    - user_id (str): The ID of the user for whom the images are being uploaded.
    - front_image (UploadFile): The front image file to be uploaded.
    - right_image (UploadFile): The right image file to be uploaded.
    - fa_db (AsyncIOMotorDatabase): MongoDB database instance (dependency injection).

    Returns:
    - dict: A dictionary containing the `scan_id` if the operation is successful.
    - None: Returns None or raises an HTTPException in case of failure.

    Raises:
    - HTTPException: Raised in case of any failure during file upload or database operation.
    """

    # S3 key paths for storing images
    s3_front_image_key = f"bodygram/users/{user_id}/images/front_image.jpg"
    s3_right_image_key = f"bodygram/users/{user_id}/images/right_image.jpg"

    try:
        # Upload front image to S3
        S3.upload_fileobj(
            front_image.file,
            BODY_GRAM_BUCKET,
            s3_front_image_key,
            ExtraArgs={"ContentType": front_image.content_type},  # Set content type
        )

        # Upload right image to S3
        S3.upload_fileobj(
            right_image.file,
            BODY_GRAM_BUCKET,
            s3_right_image_key,
            ExtraArgs={"ContentType": right_image.content_type},  # Set content type
        )

    except Exception as upload_error:
        # Handle failure during S3 upload
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload images to S3: {str(upload_error)}",
        )

    try:
        # Insert document into MongoDB for tracking scan details
        result = await fa_db[BODY_GRAM_SCAN_COLLECTION].insert_one(
            {
                "user_id": user_id,
                "front_image_key": s3_front_image_key,
                "right_image_key": s3_right_image_key,
                "created_at": datetime.utcnow(),
                "validated": False,
            }
        )

        # Return the inserted scan document's ID
        return {"scan_id": str(result.inserted_id)}

    except Exception as db_error:
        # Handle failure during MongoDB operation
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save scan metadata to MongoDB: {str(db_error)}",
        )


@router.get("/scan/{scan_id}")
async def get_scan_images_and_submit(
    scan_id: str,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
) -> Dict[str, Any]:
    """
    Get scan images for a given scan_id, convert them to Base64, fetch user details, and submit to the external Bodygram API.

    This endpoint retrieves the images associated with a scan ID from S3, converts them to Base64,
    retrieves the corresponding user's details from MongoDB, and submits all the data to an external API.

    Parameters:
    - scan_id (str): The scan ID used to fetch the scan details and images.
    - fa_db (AsyncIOMotorDatabase): MongoDB database instance.

    Returns:
    - dict: A dictionary containing the scan ID and the result of the external API call.
    - Raises HTTPException in case of any errors.
    """

    # Step 1: Fetch scan details from the MongoDB collection
    scan = await fa_db[BODY_GRAM_SCAN_COLLECTION].find_one({"_id": ObjectId(scan_id)})
    if not scan:
        raise HTTPException(
            status_code=404, detail="Scan not found for the given scan ID"
        )

    # Step 2: Fetch user details from MongoDB based on the user_id in scan
    user = await fa_db[FA_USER_COLLECTION].find_one({"_id": ObjectId(scan["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Step 3: Retrieve the image paths from S3
    try:
        front_image = S3.get_object(
            Bucket=BODY_GRAM_BUCKET, Key=scan["front_image_key"]
        )["Body"].read()
        right_image = S3.get_object(
            Bucket=BODY_GRAM_BUCKET, Key=scan["right_image_key"]
        )["Body"].read()
    except Exception as s3_error:
        raise HTTPException(
            status_code=500, detail=f"Error fetching images from S3: {str(s3_error)}"
        )

    # Step 4: Convert images to Base64
    front_photo_base64 = base64.b64encode(front_image).decode()
    right_photo_base64 = base64.b64encode(right_image).decode()

    # Step 5: Prepare the data payload for the external API
    data = {
        "customScanId": scan_id,
        "photoScan": {
            "age": user["age"],
            "weight": user["weight"],
            "height": user["height"],
            "gender": user["gender"],
            "frontPhoto": front_photo_base64,
            "rightPhoto": right_photo_base64,
        },
    }

    # Step 6: Submit data to the external Bodygram API using httpx
    url = f"https://platform.bodygram.com/api/orgs/{BODY_GRAM_ORG_ID}/scans"
    headers = {"Authorization": BODY_GRAM_API_KEY}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=300)
            resp = response.json()

            # Check for successful API response
            if response.status_code == 200:
                scan_status = resp.get("entry", {}).get("status")
                if scan_status == "failure":
                    raise HTTPException(
                        status_code=400,  # Bad request for failed scan
                        detail=resp.get("entry"),
                    )

                # Step 7: Update the scan result in MongoDB
                await fa_db[BODY_GRAM_SCAN_COLLECTION].update_one(
                    {"_id": ObjectId(scan_id)},
                    {"$set": {"scan_result": resp}},
                )

                # Return the scan result
                return {"scan_id": scan_id, "scan_result": resp}

            # Handle non-200 responses from the external API
            raise HTTPException(status_code=response.status_code, detail=resp)

    except httpx.TimeoutException:
        # Handle timeouts specifically
        raise HTTPException(
            status_code=408,  # Request Timeout
            detail="Scan in progress, please come back a little later.",
        )
    except Exception as api_error:
        # Handle any other exceptions during the API call
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit data to the external API: {str(api_error)}",
        )


@router.patch("/scan/{scan_id}")
async def update_scan_id_in_user(
    scan_id: str,
    fa_db: AsyncIOMotorDatabase = Depends(lambda: app.state.fa_db),
) -> dict:
    """
    Update the bodygram_scan_id field in the user collection by querying the scan collection using scan_id.

    :param scan_id: The scan ID to identify the scan.
    :param fa_db: Async MongoDB database instance.
    :return: A success message or error details.
    """

    # Ensure scan_id is a valid ObjectId
    if not ObjectId.is_valid(scan_id):
        raise HTTPException(status_code=400, detail="Invalid scan ID format")

    try:
        # Fetch scan document to verify existence and fetch user_id
        scan = await fa_db.get_collection(BODY_GRAM_SCAN_COLLECTION).find_one(
            {"_id": ObjectId(scan_id)}
        )

        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        user_id = scan.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=400, detail="User ID not found in scan document"
            )

        # Ensure the scan has a scan result before proceeding
        if not scan.get("scan_result"):
            raise HTTPException(
                status_code=409, detail="Scan result not found, cannot update"
            )

        # Update the user's bodygram_scan_id with the provided scan_id
        result = await fa_db.get_collection(FA_USER_COLLECTION).update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"bodygram_scan_id": scan_id}}
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=409,
                detail="No changes made, failed to update bodygram_scan_id",
            )

        return {"message": "bodygram_scan_id updated successfully for user"}

    except Exception as e:
        # Log the error (consider using an actual logger in production)
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
