from fastapi import FastAPI

from app.api import ai_search  # Import API routers

app = FastAPI()

# Include API routers with versioning
app.include_router(ai_search.router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
