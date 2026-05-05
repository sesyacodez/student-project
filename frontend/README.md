# EduManage frontend (vanilla HTML / CSS / JS)

No bundler: open static files with any static server so ES modules load correctly.

## Run

1. Start Django: from `student-project/backend/` run `python manage.py runserver` (default `http://127.0.0.1:8000/`).
2. Start static server: from this folder run:

   ```bash
   python -m http.server 5500
   ```

3. Open `http://localhost:5500/index.html`.

The app calls `http://localhost:8000/api/v1` (see `js/config.js`). Change `API_BASE` if your backend uses another host or port.

## CORS

`DevCorsMiddleware` in the Django project allows browser requests from another origin during local development.

## Auth

- When Member 1 adds `POST /api/v1/auth/login/`, use the normal sign-in form.
- Until then, use **Dev login as ADMIN / TEACHER** on the login page.

## Styles

One shared stylesheet: `styles/global.css`. Add new blocks at the end with a comment (`/* Member 1: … */`) so the team does not overwrite each other.

## Old path

If anything still pointed at `src/styles/global.css`, it was moved to `styles/global.css`.
