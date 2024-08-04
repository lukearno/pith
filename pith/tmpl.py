import os
import json
from typing import Any, Optional

import chevron


from fastapi.responses import Response, FileResponse


PITH_TEMPLATE_DIR = os.getenv("PITH_TEMPLATE_DIR")
EMPTY = {}


def render_string(path: str, data: Optional[Any] = None) -> str:
    with open(PITH_TEMPLATE_DIR + path, "r") as f:
        return chevron.render(f, data or EMPTY)


def render(path: str, data: Optional[Any] = None) -> Response:
    return Response(content=render_string(path, data), media_type="text/html")


def exists(path: str):
    return os.path.isfile(PITH_TEMPLATE_DIR + path)


def load_json(path: str):
    if exists(path):
        with open(PITH_TEMPLATE_DIR + path) as fp:
            return json.load(fp)
    else:
        return {}


def serve_file(path: str, media_type: str = "application/pdf"):
    return FileResponse(
        PITH_TEMPLATE_DIR + path,
        media_type=media_type,
    )
