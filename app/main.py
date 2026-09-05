"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

import nltk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import analyze
from .services import scraper

_NLTK_RESOURCES = ("punkt", "stopwords", "wordnet", "punkt_tab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for resource in _NLTK_RESOURCES:
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass
    yield
    scraper.close_driver()


app = FastAPI(title="AI Fake News Detection API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)


@app.get("/test")
def test():
    """Health check endpoint."""
    return {"message": "Server is running!"}
