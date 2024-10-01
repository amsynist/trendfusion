# app/main.py
import os

from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis

app = FastAPI()

# Get Redis configuration from environment variables
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

# Initialize Redis client
redis_client = Redis(host=redis_host, port=redis_port)


@app.get("/")
async def read_root():
    return {"message": "Welcome to FastAPI with Redis!"}


@app.get("/cache/{key}")
async def get_cache(key: str):
    value = await redis_client.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": value.decode("utf-8")}


@app.post("/cache/{key}")
async def set_cache(key: str, value: str):
    await redis_client.set(key, value)
    return {"message": f"Key '{key}' set with value '{value}'."}
