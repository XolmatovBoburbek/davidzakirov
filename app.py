#!/usr/bin/env python3
"""Director portfolio: public site + /admin for uploading works. Stdlib only.

Run:  ADMIN_PASSWORD=secret python3 app.py   (port 8000, override with PORT)
Data: data/site.json, uploads in data/uploads/
"""
import hmac, html, json, os, re, sys, uuid
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
try:  # ponytail: .env = plain KEY=VALUE lines, no quoting; env vars still win
    with open(os.path.join(ROOT, ".env")) as _f:
        for _l in _f:
            if "=" in _l and not _l.startswith("#"):
                _k, _v = _l.rstrip("\n").split("=", 1)
                os.environ.setdefault(_k.strip(), _v)
except FileNotFoundError:
    pass
DATA_DIR = os.path.join(ROOT, "data")
UPLOADS = os.path.join(DATA_DIR, "uploads")
DB = os.path.join(DATA_DIR, "site.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SITE_NAME = os.environ.get("SITE_NAME", "DAVID ZAKIROV")
SITE_TAGLINE = os.environ.get("SITE_TAGLINE", "Director & Editor")
MAX_UPLOAD = 20 * 1024 * 1024
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CATEGORIES = [("directed", "Directed", "/"), ("edited", "Edited", "/edited")]

os.makedirs(UPLOADS, exist_ok=True)


def load():
    try:
        with open(DB) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"works": [], "about": "", "socials": ""}


def save(db):  # ponytail: single JSON file, move to sqlite if works > ~1000
    tmp = DB + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB)


def embed(url):
    """Video page URL -> (iframe src, fallback thumbnail)."""
    m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
    if m:
        return f"https://player.vimeo.com/video/{m[1]}", f"https://vumbnail.com/{m[1]}.jpg"
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})", url)
    if m:
        return f"https://www.youtube.com/embed/{m[1]}", f"https://img.youtube.com/vi/{m[1]}/hqdefault.jpg"
    return url, ""


def thumb(w):
    return w.get("thumb") or embed(w["video"])[1]


e = html.escape

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#000;color:#fff;font:14px/1.6 Helvetica,Arial,sans-serif;letter-spacing:.08em}
a{color:#fff;text-decoration:none}
header{display:flex;justify-content:space-between;align-items:center;padding:28px 40px;text-transform:uppercase}
header .logo{font-size:18px;font-weight:700;letter-spacing:.2em;line-height:1.3}
header .logo small{display:block;font-size:11px;font-weight:400;letter-spacing:.25em;opacity:.6}
nav a{margin-left:28px;opacity:.6}nav a.on,nav a:hover{opacity:1}
main{padding:0 40px 60px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.grid a{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;background:#111}
.grid img{width:100%;height:100%;object-fit:cover;transition:transform .5s,opacity .3s}
.grid a:hover img{transform:scale(1.04);opacity:.35}
.grid span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;
 padding:16px;text-transform:uppercase;font-weight:700;opacity:0;transition:opacity .3s}
.grid a:hover span{opacity:1}
.player{aspect-ratio:16/9;width:100%;max-width:1200px;margin:0 auto 32px;background:#111}
.player iframe{width:100%;height:100%;border:0}
h1{text-transform:uppercase;font-size:16px;letter-spacing:.2em;margin-bottom:16px}
.text{max-width:720px;margin:0 auto;white-space:pre-wrap;opacity:.85}
footer{padding:40px;text-align:center;opacity:.4;font-size:12px}
footer .soc a{margin:0 10px;text-transform:uppercase}footer .soc{margin-bottom:12px}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}header,main{padding-left:16px;padding-right:16px}}
@media(max-width:560px){.grid{grid-template-columns:1fr}header{flex-direction:column;gap:12px}nav a{margin:0 12px}}
/* admin */
form.admin{max-width:720px;margin:0 auto;display:grid;gap:10px}
input,textarea,select,button{font:inherit;padding:8px;background:#111;color:#fff;border:1px solid #333;width:100%}
button{cursor:pointer;background:#fff;color:#000;font-weight:700;text-transform:uppercase}
table{width:100%;max-width:1000px;margin:0 auto 40px;border-collapse:collapse}
td{padding:8px;border-bottom:1px solid #222;vertical-align:middle}
td img{height:48px}td form{display:inline}td button{width:auto;padding:4px 10px}
"""


def socials(db):
    """One link per line: "Instagram https://instagram.com/x". Label optional."""
    out = []
    for line in db.get("socials", "").splitlines():
        parts = line.split()
        if parts:
            url = parts[-1]
            label = " ".join(parts[:-1]) or re.sub(r"^https?://(www\.)?|/.*$", "", url)
            out.append(f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a>')
    return f'<div class="soc">{"".join(out)}</div>' if out else ""


def page(title, body, path="", db=None):
    nav = "".join(f'<a href="{href}" class="{"on" if path == href else ""}">{label}</a>'
                  for _, label, href in CATEGORIES)
    nav += f'<a href="/about" class="{"on" if path == "/about" else ""}">About</a>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<style>{CSS}</style></head><body>
<header><a class="logo" href="/">{e(SITE_NAME)}<small>{e(SITE_TAGLINE)}</small></a><nav>{nav}</nav></header>
<main>{body}</main><footer>{socials(db or {})}&copy; {e(SITE_NAME)}</footer></body></html>""".encode()


def grid(works):
    if not works:
        return '<p class="text" style="text-align:center">Coming soon.</p>'
    return '<div class="grid">' + "".join(
        f'<a href="/work/{w["id"]}"><img src="{e(thumb(w))}" alt="{e(w["title"])}" loading="lazy">'
        f'<span>{e(w["title"])}</span></a>' for w in works) + "</div>"


def sorted_works(db, cat):
    return sorted((w for w in db["works"] if w["cat"] == cat), key=lambda w: (w.get("sort", 0), -w["id"]))


def admin_page(db, msg=""):
    opts = "".join(f'<option value="{k}">{l}</option>' for k, l, _ in CATEGORIES)
    rows = "".join(f"""<tr><td><img src="{e(thumb(w))}"></td><td>{e(w["title"])}</td><td>{w["cat"]}</td>
<td>{w.get("sort", 0)}</td><td><a href="/admin?edit={w["id"]}">edit</a></td>
<td><form method="post" action="/admin/delete"><input type="hidden" name="id" value="{w["id"]}">
<button onclick="return confirm('Delete?')">x</button></form></td></tr>"""
                   for w in sorted(db["works"], key=lambda w: (w["cat"], w.get("sort", 0), -w["id"])))
    return f"""{f'<p class="text" style="text-align:center;color:#8f8">{e(msg)}</p>' if msg else ''}
<h1 style="text-align:center">Works</h1>
<form method="post" action="/admin/logout" style="text-align:center;margin-bottom:20px"><button style="width:auto">Log out</button></form>
<table>{rows}</table>
<form class="admin" method="post" action="/admin/work" enctype="multipart/form-data" id="wf">
<h1>Add / edit work</h1>
<input type="hidden" name="id" id="f-id">
<input name="title" id="f-title" placeholder="Title, e.g. ARTIST /// SONG" required>
<select name="cat" id="f-cat">{opts}</select>
<input name="video" id="f-video" placeholder="Vimeo or YouTube link" required>
<input name="sort" id="f-sort" type="number" value="0" title="Lower = earlier">
<label>Thumbnail (optional, auto from video if empty) <input type="file" name="thumb" accept="image/*"></label>
<textarea name="credits" id="f-credits" rows="8" placeholder="Credits"></textarea>
<button>Save work</button></form>
<form class="admin" method="post" action="/admin/pages" style="margin-top:60px">
<h1>Pages</h1>
<label>About page text<textarea name="about" rows="10">{e(db["about"])}</textarea></label>
<label>Social links in footer, one per line: "Instagram https://instagram.com/you"<textarea name="socials" rows="4">{e(db.get("socials", ""))}</textarea></label>
<button>Save pages</button></form>
<script>
const W={json.dumps({str(w["id"]): w for w in db["works"]})};
const id=new URLSearchParams(location.search).get('edit');
if(id&&W[id]){{const w=W[id];for(const k of['id','title','cat','video','sort','credits'])document.getElementById('f-'+k).value=w[k]??'';document.getElementById('wf').scrollIntoView();}}
</script>"""


def parse_multipart(headers, body):
    msg = BytesParser(policy=policy.HTTP).parsebytes(
        b"Content-Type: " + headers["Content-Type"].encode() + b"\r\n\r\n" + body)
    fields, files = {}, {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if part.get_filename():
            files[name] = (part.get_filename(), part.get_payload(decode=True))
        else:
            fields[name] = part.get_payload(decode=True).decode("utf-8", "replace")
    return fields, files


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/html; charset=utf-8", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, to):
        self.send(303, b"", extra=[("Location", to)])

    def token(self):
        return hmac.new(ADMIN_PASSWORD.encode(), b"admin-session", "sha256").hexdigest()

    def authed(self):
        if not ADMIN_PASSWORD:
            self.send(503, page("Admin", '<p class="text">Set ADMIN_PASSWORD in .env to enable admin.</p>'))
            return False
        cookie = dict(c.strip().split("=", 1) for c in self.headers.get("Cookie", "").split(";") if "=" in c)
        if hmac.compare_digest(cookie.get("adm", ""), self.token()):
            return True
        self.send(200, page("Login", '''<form class="admin" method="post" action="/admin/login"><h1>Admin login</h1>
<input type="password" name="password" placeholder="Password" autofocus required><button>Log in</button></form>'''))
        return False

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        db = load()
        for cat, label, href in CATEGORIES:
            if p == href or (href == "/" and p == "/main"):
                return self.send(200, page(label, grid(sorted_works(db, cat)), href, db))
        if p == "/about":
            return self.send(200, page("About", f'<h1 style="text-align:center">About</h1><div class="text">{e(db["about"])}</div>', "/about", db))
        if p.startswith("/work/"):
            w = next((w for w in db["works"] if str(w["id"]) == p[6:]), None)
            if not w:
                return self.send(404, page("404", '<p class="text">Not found</p>'))
            src, _ = embed(w["video"])
            body = (f'<div class="player"><iframe src="{e(src)}" allow="autoplay; fullscreen" allowfullscreen></iframe></div>'
                    f'<h1 style="text-align:center">{e(w["title"])}</h1><div class="text">{e(w.get("credits", ""))}</div>')
            return self.send(200, page(w["title"], body, db=db))
        if p.startswith("/uploads/"):
            name = os.path.basename(p)
            try:
                with open(os.path.join(UPLOADS, name), "rb") as f:
                    return self.send(200, f.read(), "image/" + name.rsplit(".", 1)[-1].replace("jpg", "jpeg"),
                                     [("Cache-Control", "public, max-age=31536000")])
            except FileNotFoundError:
                return self.send(404, b"", "text/plain")
        if p == "/admin":
            if self.authed():
                self.send(200, page("Admin", admin_page(db, q.get("msg", [""])[0])))
            return
        self.send(404, page("404", '<p class="text">Not found</p>'))

    def do_POST(self):
        if self.path == "/admin/login":
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            pw = parse_qs(body.decode("utf-8", "replace")).get("password", [""])[0]
            if ADMIN_PASSWORD and hmac.compare_digest(pw.encode(), ADMIN_PASSWORD.encode()):
                return self.send(303, b"", extra=[("Location", "/admin"),
                                                  ("Set-Cookie", f"adm={self.token()}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")])
            return self.redirect("/admin")
        if self.path == "/admin/logout":
            return self.send(303, b"", extra=[("Location", "/"), ("Set-Cookie", "adm=; Path=/; Max-Age=0")])
        if not self.path.startswith("/admin/") or not self.authed():
            return
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_UPLOAD:
            return self.send(413, b"too large", "text/plain")
        body = self.rfile.read(n)
        db = load()
        if self.path == "/admin/delete":
            wid = parse_qs(body.decode())["id"][0]
            db["works"] = [w for w in db["works"] if str(w["id"]) != wid]
            save(db)
            return self.redirect("/admin?msg=Deleted")
        if self.path == "/admin/pages":
            f = parse_qs(body.decode(), keep_blank_values=True)
            db["about"], db["socials"] = (f.get(k, [""])[0] for k in ("about", "socials"))
            save(db)
            return self.redirect("/admin?msg=Pages+saved")
        if self.path == "/admin/work":
            fields, files = parse_multipart(self.headers, body)
            wid = fields.get("id") or ""
            w = next((w for w in db["works"] if str(w["id"]) == wid), None)
            if w is None:
                w = {"id": max((x["id"] for x in db["works"]), default=0) + 1}
                db["works"].append(w)
            w.update(title=fields.get("title", "").strip(), cat=fields.get("cat", "directed"),
                     video=fields.get("video", "").strip(), credits=fields.get("credits", ""),
                     sort=int(fields.get("sort") or 0))
            fn, data = files.get("thumb", ("", b""))
            ext = os.path.splitext(fn)[1].lower()
            if data and ext in IMG_EXT:
                name = uuid.uuid4().hex + ext
                with open(os.path.join(UPLOADS, name), "wb") as f:
                    f.write(data)
                w["thumb"] = "/uploads/" + name
            save(db)
            return self.redirect("/admin?msg=Saved")
        self.send(404, b"", "text/plain")

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % a))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"http://0.0.0.0:{port}  admin: /admin  (ADMIN_PASSWORD {'set' if ADMIN_PASSWORD else 'NOT set'})")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
