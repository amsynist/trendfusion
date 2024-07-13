from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.external import (get_fa_connection, get_groq_llm, get_open_search_db,
                          get_open_search_retriver)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    yield

    # Cleanup your resources here


app = FastAPI(lifespan=lifespan)
from app.api import ai_search  # Import API routers

# Include API routers with versioning
app.include_router(ai_search.router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
