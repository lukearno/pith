from fastapi import APIRouter, Depends

from . import database as db
from . import auth, model
from . import model
from .tmpl import render


router = APIRouter()


@router.get("/version")
async def version():
    from . import __version__

    return {"version": __version__}


@router.get("/private/{view}")
async def private(view: str, user: model.User = Depends(auth.required_user)):
    response = render(f"views/{view}.html", data={"user": user})
    return response


@router.get("/menu")
async def menu(user: model.User = Depends(auth.optional_user)):
    response = render("menu.html", data={"user": user})
    return response
