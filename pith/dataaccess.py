from dataclasses import dataclass
from typing import Any
import functools
import io
import re
import unicodedata

from contextlib import asynccontextmanager

from fastapi import HTTPException

from . import model, auth


# Here one might flesh out data access patterns, as they emerge,
# into something that resembles an organized state machine.


@dataclass
class DataAccess:
    context: Any
    cursor: Any


@asynccontextmanager
async def dbaccess(context):
    async with db.cursor() as cursor:
        yield DataAccess(context, cursor)
