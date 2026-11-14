# Peace Fashion Hub — Vercel site + admin backend

Public site: https://peace-fashion-hub.vercel.app
Vercel project: easyall1/peace-fashion-hub (team `easyall`, free Hobby)
Muse Space (design master): slug `peace-fashion-hub`

## What this is

The public site is a static page (exported from the Muse Space) plus a small
admin backend so Peace (Saheed's client, non-technical) can edit the whole
site herself from her phone — no coding, no GitHub.

- Admin page: https://peace-fashion-hub.vercel.app/admin.html
  (NOT linked from the public site.)
- Sign-in is username + password. The starting username is `peace`
  (ADMIN_USERNAME in `api/_lib.js`); Peace can change her username herself
  from the admin page ("Sign-in details" → "Change username", 3–30 chars,
  letters, numbers, dots and underscores). There are two valid passwords:
  - Peace's own password, which she sets and changes herself from the admin
    page ("Change password", min 8 chars). Stored as a salted scrypt hash
    in Blob (`auth/<random>.json`, newest file wins — the file holds her
    current username, salt and hash).
  - Saheed's master password, the `ADMIN_PASSWORD` env var (set by Saheed in
    the Vercel dashboard; the value is never recorded anywhere here). It
    always works with the username `peace`, whatever Peace calls herself —
    so Saheed can always get in, and if Peace ever forgets hers, she signs
    in with the master password and sets a new one. (There is no
    remove-password option any more — Saheed removed it 14 Nov.)
  Every password field has a Show/Hide button, so she can see what she types.
- Site content tab: every heading, paragraph, photo and link on the site
  (57 fields across 10 sections, defined in `content-schema.json`) — she
  edits what she likes and taps "Save all changes". "Reset" next to a field
  puts the original wording or photo back.
- Designs tab: the 27 gallery designs — replace a photo, rename, hide a
  design from the site, restore the original — plus "Add a new design"
  (name, collection, description, photo). Added designs can be edited,
  hidden, and deleted; original designs can be hidden but not deleted.
- Everything she saves appears on the public site within about a minute
  (Blob CDN delay).

## How it works

### Gallery pieces
- The 27 original pieces have stable order-based IDs (`piece-01`…`piece-27`,
  in gallery order in the HTML). Overrides are keyed to these IDs. Added
  designs get `piece-28` and up.
- Original photos stay inlined in the page itself (no Blob copies). The
  admin page shows small thumbnails made at deploy time (`thumbs/*.jpg`,
  220px, ~20KB each) plus the original texts from `content-defaults.json`
  — it never downloads the 17MB homepage, so it loads in a second or two
  (it used to take 15–40s). Blob holds only Peace's uploads and the
  override files — nothing else.
- Replacements Peace uploads go to Blob at `uploads/<pieceId>-<ts>.jpg`
  (client-side compressed to max 1200px JPEG before upload).
- Overrides live as ONE JSON FILE PER PIECE in Blob:
  `overrides/piece-NN.json` = `{image: <blob url>, name?: <new name>, hidden?: true}`.
  Only changed pieces have a file. Per-piece files (not one shared file)
  because the Blob CDN caches reads for ~60s — a read-modify-write of a
  single shared file silently dropped a just-saved change (found in testing
  14 Nov). Writes never read first, so nothing can be lost.
  Note: an orphaned `gallery-overrides.json` from the first version still
  sits in Blob, unreferenced and harmless.
- Added designs live as one JSON file per design in Blob:
  `added/piece-NN.json` = `{name, category, image, desc}`.

### Site content
- Every editable element carries a `data-edit="key"` (text/photo) or
  `data-edit-href="key"` (link) marker, added by `prepare-deploy.py` at
  deploy time and verified against `content-schema.json` (55 text/image
  keys, each exactly once except `brand.wordmark`, which appears twice —
  header + footer — and the 2 link keys, which appear on every matching
  button: 4 WhatsApp, 11 Instagram).
- Overrides live as ONE document in Blob: `content/site.json` = `{key: value}`.
  A single document is safe here because the admin always sends the FULL
  document on save — the function overwrites without reading first (no
  read-modify-write race). (Two people editing in two tabs at once could
  overwrite each other; Peace uses one phone, so this is accepted.)
- Link values are stored as the raw number/handle (`link.whatsapp` =
  digits with country code, `link.instagram` = username without @); the
  loader builds the `https://wa.me/…` / `https://www.instagram.com/…` URLs.
- Content photos go to Blob at `content-uploads/<key>-<ts>.jpg`.

### Loader (public page)
- The loader script (injected at deploy time by `prepare-deploy.py`)
  fetches `/api/site` on load and applies: content overrides (text → the
  element's text, photo → the img src, link → every matching button's href),
  gallery overrides (photo/name/hide), and added designs (cloned from the
  first piece's markup, with their own lightbox opener and filter handling —
  the page's own listeners were attached before these pieces existed). If
  the API is unreachable, the original content stays — the site never breaks.
- Note: replacing a heading's text drops its inner styling (e.g. the hero
  title's italic second half, the bold lead word in the fact lists) — the
  new text shows plain. Accepted: Peace edits the words, not the styling.

### API functions (`api/`, Node, `@vercel/blob` SDK)
- `GET /api/site` — `{overrides, content, added}` (public, no password).
- `POST /api/auth` — username + password check.
- `POST /api/change-password` — Peace changes her own password (min 8 chars).
- `POST /api/change-username` — Peace changes her username (3–30 chars).
- `POST /api/content` — save the full content document (+ photo uploads).
- `POST /api/upload` — replace a design's photo and/or name, hide/show it.
- `POST /api/reset` — remove a design's override (photo, name, hidden flag).
- `POST /api/add-piece` — add a new design (name, category, photo, desc).
- `POST /api/delete-piece` — delete an added design (piece-28+ only).
- Env vars on the project (Vercel dashboard → Settings → Environment Variables):
  - `BLOB_READ_WRITE_TOKEN` — auto-set when the Blob store was connected.
  - `ADMIN_PASSWORD` — Saheed's master password; changing it needs a redeploy.

## Files here

- `index.html` — the public page (copy of the Space export + piece IDs +
  content markers + loader). Regenerated by `prepare-deploy.py`.
- `admin.html` — the admin page (NOT linked from the public site).
- `pieces.json` — original piece list (id, name, category).
- `content-schema.json` — the 57 editable content fields (sections, labels,
  types); the admin page builds its form from this file.
- `content-defaults.json` — the original text/link value of every field
  (made by `prepare-deploy.py` at deploy time); the admin page reads its
  defaults from here.
- `thumbs/` — 220px thumbnails of the 27 designs + 6 editable photos
  (made by `prepare-deploy.py` at deploy time); the admin page shows these
  instead of the full-size photos.
- `api/*.js` — serverless functions (`_lib.js` is a shared helper, not a route).
- `package.json` — declares `@vercel/blob` for the functions.
- `prepare-deploy.py` — copy export → add piece IDs → add content markers →
  inject loader → make thumbs + content defaults. Fails loudly if any
  marker is missing or duplicated.
- `test-admin-api.py` — end-to-end API test (usage: `python3
  test-admin-api.py <master-password>`). Cleans up after itself; leaves the
  site in its original state. Run after any API change.
- `extract-gallery.py` — in `~/workspace/peace-fashion-hub/`; extracts the
  27 gallery images + pieces list from the Space export.

## Redeploying (after a Space edit)

ALWAYS run the prepare step first — a plain export has no piece IDs, no
content markers and no loader, so admin changes would silently stop applying:

```
cd ~/workspace/peace-fashion-hub-site/peace-fashion-hub
python3 prepare-deploy.py
VERCEL_TOKEN=... npx vercel --prod --yes
```

(VERCEL_TOKEN is the `peace-fashion-hub-redeploy` token; value not recorded.
Create a fresh one via the browser if needed.)

After any API change, run the test: `python3 test-admin-api.py <master-password>`.

## Rules / gotchas

- Gallery order is the ID source: append new pieces at the END of the
  gallery. If pieces are ever reordered in the Space, re-run
  `extract-gallery.py`, re-upload defaults, and re-map overrides manually.
- If the Space export changes section markup (new classes, moved elements),
  `prepare-deploy.py` will fail on the affected marker — fix the marker
  code to match the new markup (and update `content-schema.json` if a field
  was added or removed).
- The Muse public link (muse.ai/s/…) serves the Space build WITHOUT the
  backend, so admin changes do not apply there. The Vercel URL is the real site.
- `pieces.json` defaultImage URLs are public Blob URLs (public content).
- Never commit or record `ADMIN_PASSWORD`, `BLOB_READ_WRITE_TOKEN`, or any
  token value. The Blob token is passed via the environment only, when needed
  for uploads, and never written to a file.
