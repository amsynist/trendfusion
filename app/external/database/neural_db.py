import asyncio
import json
import os
import zipfile
from io import BytesIO

import boto3

from app.external import KRAKENOPS_BUCKET, LOCAL_STORAGE, LOCAL_TRENDICLES_DIR


def update_local_neural_s3_key(new_neural_s3_key: str):
    with open(LOCAL_STORAGE) as f:
        data = json.load(f)
        data["local_neural_s3_key"] = new_neural_s3_key
    with open(LOCAL_STORAGE, "w") as f:
        json.dump(data, f)


def load_local_neural_s3_key():
    with open(LOCAL_STORAGE) as f:
        data = json.load(f)
    return data.get("local_neural_s3_key")


def download_and_extract_zip_from_s3(s3_key: str, extract_to: str):
    s3 = boto3.client("s3")

    # Download the zip file from S3
    response = s3.get_object(Bucket=KRAKENOPS_BUCKET, Key=s3_key)
    zip_content = response["Body"].read()
    # Check if the extract_to directory exists, if not, create it
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
    # Extract the zip file to the specified directory
    with zipfile.ZipFile(BytesIO(zip_content)) as z:
        z.extractall(extract_to)
    print(f"Extracted {s3_key} to {extract_to}")


def update_local_neural_trendicles(new_neural_s3_key):
    local_s3_key = load_local_neural_s3_key()

    if local_s3_key == new_neural_s3_key:
        print("Skipping neural trendicles refresh, already up to date.")
    else:
        print("Updating neural trendicles...")
        download_and_extract_zip_from_s3(new_neural_s3_key, LOCAL_TRENDICLES_DIR)
        # Update the local_s3_key in the database
        update_local_neural_s3_key(new_neural_s3_key)

        print("Neural trendicles updated.")
