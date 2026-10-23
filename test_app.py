"""Smoke test: add a work via admin, see it on the front, delete it. Run: python3 test_app.py"""
import http.client, os, shutil, tempfile, threading
from http.server import ThreadingHTTPServer

os.environ["ADMIN_PASSWORD"] = "пароль"
import app

app.DATA_DIR = tempfile.mkdtemp()
app.UPLOADS = os.path.join(app.DATA_DIR, "uploads"); os.makedirs(app.UPLOADS)
app.DB = os.path.join(app.DATA_DIR, "site.json")
app.ADMIN_PASSWORD = "пароль"

srv = ThreadingHTTPServer(("127.0.0.1", 0), app.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
def login():
    c = http.client.HTTPConnection("127.0.0.1", srv.server_port)
    c.request("POST", "/admin/login", "password=%D0%BF%D0%B0%D1%80%D0%BE%D0%BB%D1%8C", {"Content-Type": "application/x-www-form-urlencoded"})
    r = c.getresponse(); r.read()
    assert r.status == 303 and r.getheader("Location") == "/admin"
    return {"Cookie": r.getheader("Set-Cookie").split(";")[0]}
AUTH = login()


def req(method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_port)
    c.request(method, path, body, headers or {})
    r = c.getresponse()
    return r.status, r.read().decode(), dict(r.getheaders())


B = "----b"
form = (f"--{B}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nARTIST /// SONG\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"cat\"\r\n\r\ndirected\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"video\"\r\n\r\nhttps://vimeo.com/265364614\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"credits\"\r\n\r\nDirector: X\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"thumb\"; filename=\"t.png\"\r\nContent-Type: image/png\r\n\r\nPNGDATA\r\n"
        f"--{B}--\r\n").encode()
MP = {"Content-Type": f"multipart/form-data; boundary={B}", **AUTH}

assert "Admin login" in req("GET", "/admin")[1]
assert req("POST", "/admin/login", "password=wrong", {"Content-Type": "application/x-www-form-urlencoded"})[2]["Location"] == "/admin"
assert "Add / edit work" in req("GET", "/admin", headers=AUTH)[1]
assert req("POST", "/admin/work", form, MP)[0] == 303
s, html, _ = req("GET", "/")
assert s == 200 and "ARTIST /// SONG" in html and "/uploads/" in html, html
s, html, _ = req("GET", "/work/1")
assert "player.vimeo.com/video/265364614" in html and "Director: X" in html
assert req("GET", "/edited")[1].count("ARTIST") == 0
assert req("POST", "/admin/delete", "id=1", {"Content-Type": "application/x-www-form-urlencoded", **AUTH})[0] == 303
assert "ARTIST" not in req("GET", "/")[1]
assert req("POST", "/admin/pages", "about=A&socials=Instagram+https://instagram.com/x%0Ahttps://vimeo.com/y&contacts=David+%2B998900002998%0Azakirovdirector%40gmail.com%0ATelegram+%40destonoff",
           {"Content-Type": "application/x-www-form-urlencoded", **AUTH})[0] == 303
html = req("GET", "/about")[1]
assert '<a href="https://instagram.com/x" target="_blank" rel="noopener">Instagram</a>' in html, html
assert '>vimeo.com</a>' in html
assert 'href="mailto:zakirovdirector@gmail.com"' in html and 'href="tel:+998900002998"' in html and 'href="https://t.me/destonoff"' in html, html
# photo work: no video, image only
photo = form.replace(b"https://vimeo.com/265364614", b"").replace(b"\r\n\r\ndirected\r\n", b"\r\n\r\nphoto\r\n")
assert req("POST", "/admin/work", photo, MP)[0] == 303
html = req("GET", "/photo")[1]; assert "ARTIST /// SONG" in html, html
html = req("GET", "/work/1")[1]; assert '<img class="photo"' in html and "<iframe" not in html, html
assert app.embed("https://youtu.be/dQw4w9WgXcQ")[0] == "https://www.youtube.com/embed/dQw4w9WgXcQ"
shutil.rmtree(app.DATA_DIR)
print("ok")
