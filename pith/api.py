from fastapi import APIRouter, Depends, Response

from . import database as db
from . import auth, model
from . import model
from .tmpl import render, exists, load_json, serve_file


router = APIRouter()


@router.get("/version")
async def version():
    from . import __version__

    return {"version": __version__}


users_to_packages = load_json("priv/users.json")


@router.get("/private/{file}.{ext}")
async def private(file: str, ext: str, user: model.User = Depends(auth.required_user)):
    # This allows use of another repo to keep private
    # content out of the public repo:
    package = users_to_packages.get(str(user.id))
    if not package:
        package = users_to_packages.get(user.role)
    package_path = f"priv/{package}/{file}.{ext}"
    priv_path = f"priv/{file}.{ext}"
    if exists(package_path):
        path = package_path
    elif exists(priv_path):
        path = priv_path
    else:
        path = f"views/{file}.{ext}"
    if exists(path):
        if ext.lower() == "pdf":
            return serve_file(path)
        else:
            return render(path, data={"user": user})
    else:
        return Response(
            status_code=404,
            content='<span class="text-error">Not Found.</span>',
            media_type="text/html",
        )


@router.get("/menu")
async def menu(user: model.User = Depends(auth.optional_user)):
    return render("menu.html", data={"user": user})
