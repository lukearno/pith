import os
import time
import secrets
import base64

from datetime import datetime, timedelta
from typing import Optional, Union, Any, Annotated

import argon2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.twofactor import InvalidToken

import jwt

from starlette.responses import RedirectResponse, HTMLResponse
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    Form,
    Request,
    Response,
    Security,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from pydantic import BaseModel

from .model import User
from .tmpl import render
from . import database as db

API_TOKEN_SALT = bytes.fromhex(os.getenv("API_TOKEN_SALT"))
TOTP_ISSUER = os.getenv("TOTP_ISSUER")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

ph = argon2.PasswordHasher()
security = HTTPBearer()


class AuthRequired(Exception):
    pass


def hash_token(token: bytes):
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=API_TOKEN_SALT, info=None
    ).derive(token)


def totp_key():
    return secrets.token_bytes(20)


def totp_uri(email: str, key: bytes):
    totp = TOTP(key, 6, hashes.SHA1(), 30)
    return totp.get_provisioning_uri(email, TOTP_ISSUER)


def totp_verify(key: bytes, otp: bytes):
    totp = TOTP(key, 6, hashes.SHA1(), 30)
    try:
        totp.verify(otp, time.time())
        return True
    except InvalidToken:
        return False


async def get_user_id(email: str):
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        select u.id 
        from appuser u
        join appuser_pii pii on pii.user_id = u.id 
        where pii.email = %s
            """,
            [email],
        )
        return (await cursor.fetchone())[0]


async def set_credentials(email: str, password: str, totp: bytes):
    user_id = await get_user_id(email)
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        update appuser_pii
        set password = %s
          , totp = %s
        where user_id = %s
            """,
            [ph.hash(password), totp, user_id],
        )
        await cursor.connection.commit()


async def get_credentials(email: str):
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        select pii.password
             , pii.totp
        from appuser_pii pii
        join appuser u on pii.user_id = u.id
        where pii.email = %s
            """,
            [email],
        )
        return await cursor.fetchone()


async def rehash_password(email: str, password: str):
    user_id = await get_user_id(email)
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        update appuser_pii
        set password = %s
        where email = %s
            """,
            [ph.hash(password), email],
        )
        await cursor.connection.commit()


def verify_password(email: str, hash: str, password: str):
    try:
        ph.verify(hash, password)
        if ph.check_needs_rehash(hash):
            rehash_password(email, password)
        return True
    except argon2.exceptions.VerificationError:
        return False


async def new_user(email: str, first_name: str, last_name: str, role: str):
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        with ins (u_id) as (
          insert into appuser (doreset, role) values (true, %s)
          returning id
        )
        insert into appuser_pii (
           user_id
         , email
         , first_name
         , last_name
         , email_hash
        )
        select ins.u_id, %s, %s, %s, %s from ins
            """,
            [
                role,
                email,
                first_name,
                last_name,
                hash_token(email.encode("utf8")),
            ],
        )
        await cursor.connection.commit()


async def add_access_token(email):
    token = secrets.token_bytes(15)
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        with usr (u_id) as (
          select user_id from appuser_pii
          where email = %s
        )
        insert into access_token (user_id, token)
        select u_id, %s from usr;
            """,
            [email, token],
        )
        await cursor.connection.commit()
    return token


async def load_user(email: str = None, accesstoken: str = None) -> Optional[User]:
    if email is None and accesstoken is None:
        return
    async with db.cursor() as cursor:
        if email is not None:
            await cursor.execute(
                """
            select u.id as id
                 , u.created as created
                 , u.doreset as doreset
                 , u.confirmed as confirmed
                 , u.active as active
                 , u.role as role
                 , pii.email as email
                 , pii.first_name as first_name
                 , pii.last_name as last_name
            from appuser u
            join appuser_pii pii on pii.user_id = u.id
                where u.active and pii.email = %s
                """,
                [email],
            )
        else:
            await cursor.execute(
                """
            select u.id as id
                 , u.created as created
                 , u.doreset as doreset
                 , u.confirmed as confirmed
                 , u.active as active
                 , u.role as role
                 , pii.email as email
                 , pii.first_name as first_name
                 , pii.last_name as last_name
            from appuser u
            join appuser_pii pii on pii.user_id = u.id
            join access_token as t on t.user_id = u.id
                where u.active and t.token = %s
                """,
                [accesstoken],
            )
        fields = [d[0] for d in cursor.description]
        record = await cursor.fetchone()
        if record:
            return User(**dict(zip(fields, record)))


def update_user(user: User):
    with db.cursor() as cursor:
        cursor.execute(
            """
        update appuser_pii set
          first_name = %s
        , last_name = %s
        , email = %s
        , email_hash = %s
        where user_id = %s
            """,
            [
                user.first_name,
                user.last_name,
                user.email,
                hash_token(user.email.encode("utf8")),
                user.id,
            ],
        )
        cursor.execute("update appuser set confirmed = true where id = %s", [user.id])
        cursor.connection.commit()


async def add_guest(role: str, email: str, first_name: str, last_name: str):
    totp = totp_key()
    password = base64.b64encode(secrets.token_bytes(9))
    await new_user(email, first_name, last_name, role)
    await set_credentials(email, password, totp)
    access_token = await add_access_token(email)
    based_totp = base64.b32encode(totp)
    based_token = base64.b32encode(access_token)
    uri = totp_uri(email, totp)
    return based_token, based_totp, uri


def create_jwt(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    data: dict = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "data": data}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt(token, soft=False):
    if token == "12345":
        return

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=JWT_ALGORITHM)

        return payload["sub"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        if not soft:
            raise AuthRequired()
    except Exception as e:
        from . import logging

        logging.exception(e)

        raise AuthRequired()


def _current_email(creds: HTTPAuthorizationCredentials = Security(security)):
    return decode_jwt(creds.credentials)


def _current_email_optional(
    creds: HTTPAuthorizationCredentials = Security(security),
):
    return decode_jwt(creds.credentials, soft=True)


async def _current_user(current_email: str = Depends(_current_email_optional)):
    return await load_user(current_email)


async def optional_user(current_user: Optional[User] = Depends(_current_user)):
    return current_user


async def required_user(current_user: Optional[User] = Depends(_current_user)):
    if current_user is None:
        raise AuthRequired()
    return current_user


async def optional_auth(current_email: Optional[str] = Depends(_current_email)):
    return current_email


async def required_auth(current_email: Optional[str] = Depends(_current_email)):
    if current_email is None:
        raise AuthRequired()
    return current_email


async def log_access(user: User) -> None:
    async with db.cursor() as cursor:
        await cursor.execute(
            """
        insert into access_log (user_id) values (%s)
            """,
            [
                user.id,
            ],
        )
        await cursor.connection.commit()


def add_auth_support(app: FastAPI, prefix: str = ""):
    @app.exception_handler(AuthRequired)
    async def exception_handler(request: Request, exc: AuthRequired) -> Response:
        response = RedirectResponse(url="/auth/login")
        response.delete_cookie("Authorization")
        return response

    @app.middleware("http")
    async def create_auth_header(request: Request, call_next):
        if (
            "Authorization" not in request.headers
            and "Authorization" in request.cookies
        ):
            access_token = request.cookies["Authorization"]
            request.headers.__dict__["_list"].append(
                (
                    "authorization".encode(),
                    f"Bearer {access_token}".encode(),
                )
            )
        elif (
            "Authorization" not in request.headers
            and "Authorization" not in request.cookies
        ):
            request.headers.__dict__["_list"].append(
                (
                    "authorization".encode(),
                    "Bearer 12345".encode(),
                )
            )
        response = await call_next(request)
        return response

    @app.get(f"{prefix}/login")
    async def login_GET(
        request: Request, email: Optional[str] = Depends(optional_auth)
    ):
        if email:
            return render("xfer/login-success.html", dict(user=email))
        return render(
            "views/login.html",
            dict(
                result="",
                failed=False,
            ),
        )

    @app.post(f"{prefix}/login")
    async def login_POST(
        request: Request,
        email: Annotated[str, Form()],
        password: Annotated[str, Form()],
        otp: Annotated[str, Form()],
    ):
        email = email.lower()
        result = await get_credentials(email)
        failed = False
        if result:
            hash, totp = result
            if verify_password(email, hash, password):
                if (not totp) or totp_verify(totp, otp.encode("utf-8")):
                    user = await load_user(email)
                    token = create_jwt(
                        email, data=dict(email=email, first_name=user.first_name)
                    )
                    response = render("xfer/login-success.html", dict(user=user))
                    response.set_cookie(
                        key="Authorization", value=str(token), httponly=True
                    )
                    return response
            failed = True
        return Response(
            status_code=400,
            content='<span class="text-error">Access denied.</span>',
            media_type="text/html",
        )

    @app.get(f"{prefix}/logout")
    async def logout(request: Request, email: Optional[str] = Depends(optional_auth)):
        response = render("xfer/logout-success.html")
        if email:
            response.delete_cookie("Authorization")
        return response

    @app.get(f"{prefix}/access/{{accesstoken}}")
    async def token_access(request: Request, accesstoken: Optional[str]):
        user = await load_user(accesstoken=base64.b32decode(accesstoken))
        await log_access(user)
        response = RedirectResponse(url="/cv.html")
        if user:
            token = create_jwt(
                user.email, data=dict(email=user.email, first_name=user.first_name)
            )
            response.set_cookie(key="Authorization", value=str(token), httponly=True)
        return response

    @app.get(f"{prefix}/current-user", response_model=User)
    async def whoami(current_user: User = Depends(required_user)):
        return current_user

    """
    # written but not yet run, needs password setting too
    # using a script for now
    @app.post(f"{prefix}/signup")
    async def signup(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        first_name: str = Form(...),
        last_name: str = Form(...),
    ):
        await new_user(email, first_name, last_name)
        user = await load_user(email)
        await rehash_password(email, password)

        # TODO verify success and handle errors
        # response = template
        return render("", user)


    @app.put(f"{prefix}/current-user", response_model=User)
    async def update(updated: User, current_user: User = Depends(required_user)):
        await update_user(updated)
        return updated
    """
