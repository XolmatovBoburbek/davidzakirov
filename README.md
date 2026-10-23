# davidzakirov — director portfolio

Public site (Directed / Edited / About, grid of works, Vimeo/YouTube player per work)
plus a private admin at `/admin` for uploading works. Python stdlib only, no dependencies.

## Run

```sh
ADMIN_PASSWORD=change-me SITE_NAME="DAVID ZAKIROV" python3 app.py
# site:  http://localhost:8000
# admin: http://localhost:8000/admin   (any username, password = ADMIN_PASSWORD)
```

Docker:

```sh
docker build -t portfolio .
docker run -p 8000:8000 -e ADMIN_PASSWORD=change-me -v $PWD/data:/app/data portfolio
```

All content lives in `data/` (`site.json` + `uploads/`). Back that folder up.

## Admin

- Add a work: title, category (Directed / Edited), Vimeo or YouTube link, optional thumbnail, credits, sort order.
- Thumbnail is pulled from the video automatically if you don't upload one.
- Edit the About text and footer social links.
- Name and tagline in the header: `SITE_NAME`, `SITE_TAGLINE` env vars.

Put it behind HTTPS (nginx/Caddy) in production: Basic Auth sends the password in the clear otherwise.

## Test

```sh
python3 test_app.py
```
