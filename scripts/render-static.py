from pith.tmpl import render_string

# render static pages

pages = [
    ("index", "/views/key.html"),
    ("key", "/views/key.html"),
    ("login", "/auth/login"),
    ("cv", "/api/private/cv"),
    ("home", "/api/private/home"),
]

for page, view in pages:
    with open(f"www/{page}.html", "w") as fp:
        print("static render:", page, view)
        fp.write(render_string("app.html", data={"view": view, "page": page}))
