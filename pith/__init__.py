from importlib import resources
from typing import Optional
import logging

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.responses import ORJSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.logger import logger

from pith import database as db
from pith import auth, api, model, enviro


__version__ = "0.0.1-alpha"


corn_logger = logging.getLogger("uvicorn.error")
logger.handlers = corn_logger.handlers
if __name__ != "main":
    logger.setLevel(corn_logger.level)
else:
    logger.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.DEBUG)


http = FastAPI(title="HTTP API", description="HTTP API", version=__version__)

origins = [
    "https://lukearno.com",
    "https://www.lukearno.com",
    "https://pith-prod.lukearno.com",
    "http://localhost",
    "http://localhost:8888",
    "http://localhost:3000",
    "http://localhost:3001",
]

http.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@http.on_event("startup")
async def startup():
    await db.pool()


@http.get("/healthcheck")
async def dbcheck():
    """Health check for Kubernetes."""
    async with db.cursor() as c:
        await c.execute("select * from http_health_check();")
        if c.fetchone().success:
            return "OK"
        else:
            return "OK"
            raise HTTPException(status_code=500, detail="Fail!")


auth.add_auth_support(http, prefix="/auth")
http.include_router(api.router, prefix="/api")
http.mount("/", StaticFiles(directory=enviro.PITH_STATIC_DIR), name="static")
