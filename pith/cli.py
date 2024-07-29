"""pith - Simple CLI

Usage:
pith http <host> <port> [dev]
pith profile <host> <port> [dev]
pith add-guest <email> <first-name> <last-name>

Options:
  -h --help     Show this screen.
  --version     Show version.

Args:
  <host>             host name
  <port>             port number
  <first-name>       firt name
  <last-name>        last name
  <email>            email
  <filename>         file name
"""

import asyncio
import code
import json
import sys


import uvicorn

from docopt import docopt

from . import __version__, http, auth


class CLI(object):
    def __init__(self, opt):
        self.opt = opt

    def __call__(self):
        if self.opt["http"]:
            self.http(self.opt["<host>"], self.opt["<port>"], self.opt.get("dev"))
        elif self.opt["profile"]:
            self.profile(self.opt["<host>"], self.opt["<port>"], self.opt.get("dev"))
        elif self.opt["add-guest"]:
            asyncio.run(auth.db.pool())
            print(
                " ".join(
                    [
                        "add-guest",
                        self.opt["<email>"],
                        self.opt["<first-name>"],
                        self.opt["<last-name>"],
                    ]
                )
            )
            access_token, totp, uri = asyncio.run(
                auth.add_guest(
                    self.opt["<email>"],
                    self.opt["<first-name>"],
                    self.opt["<last-name>"],
                ),
            )
            access_token = access_token.decode("ascii")
            totp = totp.decode("ascii")
            print("totp", totp)
            print("uri", uri)
            print("token", access_token)
            print("link", f"https://lukearno.com/auth/access/{access_token}")

    def http(self, host, port, dev=False):
        extras = {}
        if dev:
            uvicorn.run(
                "pith:http", host=host, port=int(port), log_level="debug", reload=True
            )
        else:
            uvicorn.run(http, host=host, port=int(port), log_level="info", **extras)

    def profile(self, host, port, dev=False):
        import cProfile
        import pstats

        with cProfile.Profile() as profile:
            try:
                self.http(host, port, dev)
            except:
                pass
            with open("profile.txt", "w") as stream:
                profile_result = pstats.Stats(profile, stream=stream)
                profile_result.sort_stats("ncalls")
                profile_result.print_stats()


def run():
    arguments = docopt(__doc__, version=f"Pith {__version__}")
    CLI(arguments)()


if __name__ == "__main__":
    run()
