from base64 import b64encode as b64
import csv

from . import database as db
from . import auth
from .model import User


def check_user(tenant_id, email):
    with db.cursor() as cursor:
        cursor.execute(
            """
        select u.id 
        from appuser u
        join appuser_pii pii on u.id = pii.user_id
        where pii.email = %s 
          and u.tenant_id = %s
        """,
            [email, tenant_id],
        )
        one = cursor.fetchone()
        if one:
            return one[0]


class Admin:  # singleton
    def __init__(self):
        db.pool()
        auth.db = db

    def sync_users(self, filename):
        with db.cursor() as cursor:
            cursor.execute("select slug, id from tenant")
            slugs = dict(cursor.fetchall())
        with open(filename) as csvfile:
            rdr = csv.DictReader(csvfile)
            for row in rdr:
                user_id = check_user(tenant_id, row["email"])
                if not user_id:
                    auth.new_user(
                        row["email"],
                        row["first_name"],
                        row["last_name"],
                    )
                    user_id = check_user(tenant_id, row["email"])
                auth.set_credentials(row["email"], row["password"], None)
                auth.update_user(
                    User(
                        id=user_id,
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        email=row["email"],
                    )
                )
