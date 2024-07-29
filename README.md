# Pith

This is a project start for a
PG/FastAPI/Moustache/HTMX/Web Components/Surreal/Tailwind
application deploying to Google Cloud.

## Dev Setup

Provision a PostGRES instance in Cloud SQL. You will need a *service accout key* and the binary for `cloud_sql_proxy`. You will need to copy `env/example.sh` to `env/dev.sh` and `env/prod.sh` and fill in their values, supplying locations/values for the requisit cryptographic materia. You will also need node, `venv` and your distro's postgresql-server and inotify-tool packages for running the dev server. 

```shell
$ python3 -m venv .v
$ source .v/bin/activate
$ pip install -r requirements.txt
$ pip install -r dev-requirements.txt
$ pip install -e '.'
$ source env/dev.sh
$ make start_proxy
$ make psql
```

Then you will need to paste the schema from `sql/schema.sql` into psql, exit and you are ready to run.

```shell
$ source env/dev.sh && make run-dev
```

Visit http://localhost:8888/index.html in your browser, or whatever address and port you have chosen.


## Deploy to Google Cloud

For setup, see the Makefile.

```shell
$ source env/prod.sh && make ship
```

## Notes on HTMX and this stack:

Overall, the balance of simplicity and power as compared to Vite/Vue or SveltKit SPAs on one hand and oldschool server-side web applications on the other, is very compelling. Producing a production-grade boilerplate was very low effort. Many of the problems that "modern Javascript frameworks" "solve" are simply sidestepped or returned to the server where they belong. I have long thought that most front-end complexity is a facade (in the technical sense) and could, in theory, be simplified away. I think HTMX's simplifying effect on a boilerplate like this demonstrates the veracity of the claim that we would be best served by working with and through the Web's native architecture, rather than fighting to pile other architectures on top of it. The results are superior, it's far easier to work with and the supply chain attack surface is dramatically decreaed. The reduction in complexity is very satisfying and it feels light and fun to work in. The right tool to use is always situational, of course, and there were a few minor rough edges that I did notice, which I will now point out.

### Tailwind

Tailwind is a bit awkward (but still awesome) in this setup. There is a hot re-compile script that is run by the dev server, and it will pick up most utility classes automatically, but is possible to add them where they will not be found by the compiler. In particular, this happens when the only use of a utility class is in a web component. If you run into this, just add the class in question to `www/tailwind.html` which exists for just this case. You can verify that a class is being picked up by grepping the compiled stylesheet in `www/css/site.css`.

### Web Components

This was the first time in a long time I've looked closely at Web Components, but HTMX implicitly makes a case for them to finally be adopted. They are still a little clunky and, in particular, attaching inputs to a form needs explicit handling. It's a bit verbose, but I don't think it's a big deal. All of this would get generally get sorted out early in the implementation of a design system and into the basic structure of the application componentry. It could definitely be a bit of a gotcha for someone who was not aware of the issue, though.

### Python and FastAPI

I've used FastAPI a bit and it is capable, easy to work with and reasonably fast. Python feels heavy for the API, though. I may rewrite it in Zig.

## A Note on Security

Take a look at `auth.py` and use-at-your-own-risk. (I make no promises or guarantees to anyone by sharing this code, of course.) I think it's right and is nothing fancy, but it needs some additional review and test coverage before anyone should put it into production. And, of course, use the most battle-tested code available for anything cryptography related.