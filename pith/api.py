from fastapi import APIRouter, Depends

from . import database as db
from . import auth, model
from . import model
from .tmpl import render, exists


router = APIRouter()


@router.get("/version")
async def version():
    from . import __version__

    return {"version": __version__}


@router.get("/private/{view}")
async def private(view: str, user: model.User = Depends(auth.required_user)):
    path = f"views/{view}.html"
    if view == "cv":
        # This allows use of another repo to keep private
        # content out of the public repo:
        personal_path = f"priv/{view}-{user.id}.html"
        role_path = f"priv/{view}-{user.role}.html"
        priv_path = f"priv/{view}.html"
        if exists(personal_path):
            path = personal_path
        elif exists(role_path):
            path = role_path
        elif exists(priv_path):
            path = priv_path
    return render(path, data={"user": user})


@router.get("/menu")
async def menu(user: model.User = Depends(auth.optional_user)):
    return render("menu.html", data={"user": user})
