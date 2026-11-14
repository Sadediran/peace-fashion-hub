#!/usr/bin/env python3
"""Prepare the Peace Fashion Hub site for deployment to Vercel.

1. Copies the fresh Space export (~/workspace/your_files/peace-fashion-hub/
   peace-fashion-hub.html) into this directory as index.html.
2. Adds stable order-based IDs (data-piece-id="piece-01".."piece-27") to each
   gallery piece button, in document order. The admin system keys overrides
   to these IDs, so gallery order must stay stable (append new pieces at the
   end; if pieces are ever reordered, re-run the extractor and re-map).
3. Adds data-edit="key" / data-edit-href="key" markers to every editable
   element (texts, photos, links), keyed to content-schema.json. The loader
   and the admin page use these markers to find each field. Every key is
   verified to be marked exactly once (links may appear several times).
4. Injects the site-overrides loader script before </body>. The loader
   fetches /api/site and applies: gallery photo/name overrides, hidden
   pieces, site-content overrides (texts/photos/links), and designs added
   through the admin page. If the API is unreachable (e.g. the page is
   viewed somewhere without the backend), the original content stays.
5. Makes the small files the admin page needs (thumbs/*.jpg — a 220px
   thumbnail of each design and each editable photo — and
   content-defaults.json, the original text/link value of every field),
   so the admin page loads in a second or two instead of downloading the
   whole 17MB homepage.

Always run this before deploying (see README.md). It does NOT deploy —
deploy afterwards with:  npx vercel --prod --yes   (VERCEL_TOKEN in env).
"""
import re
import shutil
import sys
from pathlib import Path

EXPORT = Path.home() / "workspace/your_files/peace-fashion-hub/peace-fashion-hub.html"
HERE = Path(__file__).resolve().parent
TARGET = HERE / "index.html"

LOADER_MARKER = "pfh-site-overrides"
LOADER_SCRIPT = """
<script>
/* pfh-site-overrides: applies the customisations Peace makes in the admin
   page (/admin.html) — gallery photos/names, hidden designs, added designs,
   and every editable text, photo and link on the site. Originals stay as
   the fallback if the API is unreachable. */
(function () {
  function applyContent(content) {
    Object.keys(content || {}).forEach(function (key) {
      var value = content[key];
      if (typeof value !== 'string' || !value) return;
      document.querySelectorAll('[data-edit="' + key + '"]').forEach(function (el) {
        if (el.tagName === 'IMG') el.src = value;
        else el.textContent = value;
      });
      document.querySelectorAll('[data-edit-href="' + key + '"]').forEach(function (el) {
        if (key === 'link.whatsapp') el.href = 'https://wa.me/' + value;
        else if (key === 'link.instagram') el.href = 'https://www.instagram.com/' + value;
        else el.href = value;
      });
    });
  }

  function currentFilter() {
    var active = document.querySelector('.chip[aria-pressed="true"]');
    return active ? active.getAttribute('data-filter') : 'all';
  }
  function filterAdded() {
    var f = currentFilter();
    document.querySelectorAll('.piece[data-added="1"]').forEach(function (p) {
      var show = f === 'all' || p.getAttribute('data-cat') === f;
      p.hidden = !show;
      if (show) p.classList.add('in');
    });
  }
  function openAddedLb(piece) {
    /* Same behaviour as the page's own lightbox opener, for designs added
       through the admin page (the page's listeners were attached before
       these pieces existed). Closing works via the page's own listeners. */
    var lb = document.getElementById('lightbox');
    var lbImg = document.getElementById('lbImg');
    var lbTag = document.getElementById('lbTag');
    var lbTitle = document.getElementById('lbTitle');
    var lbDesc = document.getElementById('lbDesc');
    var lbDate = document.getElementById('lbDate');
    var lbPost = document.getElementById('lbPost');
    var lbClose = document.getElementById('lbClose');
    if (!lb || !lbImg) return;
    var img = piece.querySelector('img');
    if (img) { lbImg.src = img.getAttribute('src'); lbImg.alt = img.getAttribute('alt'); }
    if (lbTag) lbTag.textContent = piece.getAttribute('data-tag') || '';
    if (lbTitle) lbTitle.textContent = piece.getAttribute('data-title') || '';
    if (lbDesc) lbDesc.textContent = piece.getAttribute('data-desc') || '';
    var pDate = piece.getAttribute('data-date');
    if (lbDate) lbDate.textContent = pDate ? 'Shared on Instagram · ' + pDate : 'From @peace_fashion_hub on Instagram';
    if (lbPost) lbPost.href = piece.getAttribute('data-post') || 'https://www.instagram.com/peace_fashion_hub';
    lb.hidden = false;
    requestAnimationFrame(function () { lb.classList.add('open'); });
    document.body.style.overflow = 'hidden';
    if (lbClose) lbClose.focus();
  }

  function applyPieces(overrides, added) {
    /* Added designs first, so overrides (photo/name/hide) can apply to
       them too — they only exist in the DOM after injection. */
    var list = Object.keys(added || {}).sort();
    if (list.length) {
      var gallery = document.getElementById('gallery');
      var template = document.querySelector('.piece[data-piece-id]');
      if (gallery && template) {
        var tags = { bridal: 'Bridal', occasion: 'Aso-Ebi & Occasion', couture: 'Couture & Poise' };
        list.forEach(function (id) {
          var p = added[id];
          if (!p || document.querySelector('.piece[data-piece-id="' + id + '"]')) return;
          var el = template.cloneNode(true);
          el.setAttribute('data-piece-id', id);
          el.setAttribute('data-added', '1');
          el.setAttribute('data-cat', p.category || 'couture');
          el.setAttribute('data-title', p.name);
          el.setAttribute('data-tag', tags[p.category] || 'Couture & Poise');
          el.setAttribute('data-desc', p.desc || '');
          el.setAttribute('data-post', 'https://www.instagram.com/peace_fashion_hub');
          el.removeAttribute('data-date');
          el.hidden = false;
          el.classList.add('in');
          var img = el.querySelector('img');
          if (img) { img.src = p.image; img.alt = p.name; }
          var nt = el.querySelector('.nt-name');
          if (nt) nt.textContent = p.name;
          var info = el.querySelector('.piece-info');
          if (info) {
            var h = info.querySelector('h1,h2,h3,h4');
            if (h) h.textContent = p.name;
            var d = info.querySelector('p');
            if (d) d.textContent = p.desc || '';
          }
          el.addEventListener('click', function () { openAddedLb(el); });
          gallery.appendChild(el);
        });
        filterAdded();
        document.querySelectorAll('.chip').forEach(function (chip) {
          chip.addEventListener('click', filterAdded);
        });
      }
    }
    /* Overrides for all pieces, original and added. */
    Object.keys(overrides || {}).forEach(function (id) {
      var o = overrides[id];
      if (!o) return;
      var el = document.querySelector('.piece[data-piece-id="' + id + '"]');
      if (!el) return;
      if (o.hidden) { el.style.display = 'none'; return; }
      var oldName = el.getAttribute('data-title') || '';
      if (o.image) {
        var img = el.querySelector('img');
        if (img) img.src = o.image;
      }
      if (o.name) {
        var nt = el.querySelector('.nt-name');
        if (nt) nt.textContent = o.name;
        el.setAttribute('data-title', o.name);
        var info = el.querySelector('.piece-info');
        if (info) {
          info.querySelectorAll('h1,h2,h3,h4').forEach(function (h) {
            if (h.textContent.trim() === oldName) h.textContent = o.name;
          });
        }
      }
    });
  }

  function load() {
    fetch('/api/site', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        if (d.content) applyContent(d.content);
        applyPieces(d.overrides, d.added);
      })
      .catch(function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
</script>
"""


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def section_span(html, start_pat, label):
    """Return (start, end) of a <section>...</section> block."""
    m = re.search(start_pat, html)
    if not m:
        fail(f"{label} section not found ({start_pat})")
    start = m.start()
    end = html.find("</section>", start)
    if end == -1:
        fail(f"{label} section has no </section>")
    return start, end + len("</section>")


def mark_tag(html, pattern, key, label, attr="data-edit"):
    """Add attr="key" to the first opening tag matching pattern (the pattern
    must match the whole opening tag, ending in '>'). Fails unless exactly
    one match is made."""
    new, n = re.subn(pattern, lambda m: m.group(0)[:-1] + f' {attr}="{key}">', html, count=1)
    if n != 1:
        fail(f"could not mark {label} ({key}): {n} matches for {pattern}")
    return new


def mark_first_p_after(span, after_text, key, label, from_pos=0):
    """Add data-edit="key" to the first <p ...> tag after the first
    occurrence of after_text at or after from_pos (the <p> may carry
    attributes, e.g. a style)."""
    pos = span.find(after_text, from_pos)
    if pos == -1:
        fail(f"{label}: anchor {after_text!r} not found")
    m = re.search(r'<p[^>]*>', span[pos:])
    if not m:
        fail(f"{label} not found")
    tag = m.group(0)
    start = pos + m.start()
    end = pos + m.end()
    return span[:start] + tag[:-1] + f' data-edit="{key}">' + span[end:]


def mark_in_section(html, start_pat, label, fn):
    """Run fn(span) on a section's HTML and splice the result back."""
    s, e = section_span(html, start_pat, label)
    return html[:s] + fn(html[s:e]) + html[e:]


shutil.copyfile(EXPORT, TARGET)
html = TARGET.read_text(encoding="utf-8")

# 1. Piece IDs (in document order). Skip buttons that already have one.
piece_re = re.compile(r'<button class="piece reveal"([^>]*)>')
count = 0

def add_id(m):
    global count
    count += 1
    attrs = m.group(1)
    if "data-piece-id=" in attrs:
        return m.group(0)
    return f'<button class="piece reveal" data-piece-id="piece-{count:02d}"{attrs}>'

html = piece_re.sub(add_id, html)
print(f"piece buttons found: {count}")
if count != 27:
    fail("expected 27 gallery pieces")

# 2. Global contact links (every WhatsApp / Instagram button on the page).
def mark_links(h, href, key):
    pat = re.compile(r'(<a[^>]*href="' + re.escape(href) + r'"[^>]*)(>)')
    new, n = pat.subn(lambda m: m.group(1) + f' data-edit-href="{key}"' + m.group(2), h)
    print(f"{key}: {n} links marked")
    if n == 0:
        fail(f"no links found for {key}")
    return new

html = mark_links(html, "https://wa.me/2348024457300", "link.whatsapp")
html = mark_links(html, "https://www.instagram.com/peace_fashion_hub", "link.instagram")

# 3. Hero.
def hero_fn(span):
    span = mark_tag(span, r'<p class="hero-eyebrow">', "hero.eyebrow", "hero eyebrow")
    span = mark_tag(span, r'<h1>', "hero.title", "hero title")
    span = mark_tag(span, r'<p class="hero-lede">', "hero.lede", "hero lede")
    # Hero photo: the <img> inside <figure class="hero-media">.
    fig = span.find('<figure class="hero-media"')
    if fig == -1:
        fail("hero figure not found")
    img = span.find("<img", fig)
    if img == -1:
        fail("hero image not found")
    end = span.find(">", img)
    span = span[:end] + ' data-edit="hero.image"' + span[end:]
    # Hero facts: the 3 <li> inside <ul class="hero-facts">.
    ul_s = span.find('<ul class="hero-facts">')
    ul_e = span.find("</ul>", ul_s)
    if ul_s == -1 or ul_e == -1:
        fail("hero facts list not found")
    facts = span[ul_s:ul_e]
    n = [0]
    def fact(m):
        n[0] += 1
        return f'<li data-edit="hero.fact{n[0]}">'
    facts = re.sub(r'<li>', fact, facts)
    if n[0] != 3:
        fail(f"expected 3 hero facts, found {n[0]}")
    return span[:ul_s] + facts + span[ul_e:]

html = mark_in_section(html, r'<section class="hero"', "hero", hero_fn)

# 4. Collections.
def collections_fn(span):
    span = mark_tag(span, r'<h2>', "collections.title", "collections title")
    # Intro: the first <p> after the <h2>.
    span = mark_first_p_after(span, "</h2>", "collections.intro", "collections intro")
    # The 3 collection cards (<article class="col-card reveal">), in order.
    cats = ["bridal", "occasion", "poise"]
    cards = list(re.finditer(r'<article class="col-card reveal">.*?</article>', span, re.S))
    if len(cards) != 3:
        fail(f"expected 3 collection cards, found {len(cards)}")
    out = []
    last = 0
    for i, c in enumerate(cards):
        cat = cats[i]
        card = c.group(0)
        card = mark_tag(card, r'<h3>', f"collections.{cat}.title", f"{cat} card title")
        card = mark_tag(card, r'<p>', f"collections.{cat}.text", f"{cat} card text")
        img = card.find("<img")
        if img == -1:
            fail(f"{cat} card image not found")
        end = card.find(">", img)
        card = card[:end] + f' data-edit="collections.{cat}.image"' + card[end:]
        out.append(span[last:c.start()])
        out.append(card)
        last = c.end()
    out.append(span[last:])
    return "".join(out)

html = mark_in_section(html, r'<section class="collections" id="collections">', "collections", collections_fn)

# 5. Signature Pieces (section heading + intro).
def pieces_fn(span):
    span = mark_tag(span, r'<h2>', "pieces.title", "pieces title")
    span = mark_first_p_after(span, "</h2>", "pieces.intro", "pieces intro")
    return span

html = mark_in_section(html, r'<section id="pieces">', "pieces", pieces_fn)

# 6. About.
def about_fn(span):
    span = mark_tag(span, r'<h2>', "about.title", "about title")
    # The 3 plain <p> in order: bio1, bio2, method.
    keys = ["about.bio1", "about.bio2", "about.method"]
    n = [0]
    def plain_p(m):
        n[0] += 1
        if n[0] > 3:
            return m.group(0)
        return f'<p data-edit="{keys[n[0] - 1]}">'
    span = re.sub(r'<p>', plain_p, span)
    if n[0] != 3:
        fail(f"expected 3 plain paragraphs in about, found {n[0]}")
    span = mark_tag(span, r'<p class="credits">', "about.credits", "about credits")
    span = mark_tag(span, r'<blockquote>', "about.quote", "about quote")
    # About photo: the <img> whose alt starts "Inside the atelier".
    m = re.search(r'<img[^>]*alt="Inside the atelier[^>]*>', span)
    if not m:
        fail("about image not found")
    tag = m.group(0)
    span = span[:m.start()] + tag[:-1] + ' data-edit="about.image">' + span[m.end():]
    return span

html = mark_in_section(html, r'<section class="about" id="about">', "about", about_fn)

# 7. Atelier.
def atelier_fn(span):
    span = mark_tag(span, r'<h2>', "atelier.title", "atelier title")
    span = mark_first_p_after(span, "</h2>", "atelier.intro", "atelier intro")
    # The 4 steps, matched by their exact headings.
    steps = ["The Conversation", "Base &amp; Drape", "Beadwork &amp; Motif", "Fit &amp; Flight"]
    for i, title in enumerate(steps, start=1):
        h3 = span.find(f"<h3>{title}</h3>")
        if h3 == -1:
            fail(f"atelier step {i} heading not found: {title}")
        span = span[:h3] + f'<h3 data-edit="atelier.step{i}.title">{title}</h3>' + span[h3 + len(f"<h3>{title}</h3>"):]
        span = mark_first_p_after(span, "</h3>", f"atelier.step{i}.text", f"atelier step {i} text", from_pos=h3)
    # Closing note.
    note = span.find("<p>“Dress made with love”")
    if note == -1:
        fail("atelier note not found")
    span = span[:note] + '<p data-edit="atelier.note">“Dress made with love”' + span[note + len("<p>“Dress made with love”"):]
    return span

html = mark_in_section(html, r'<section class="atelier" id="atelier">', "atelier", atelier_fn)

# 8. Academy.
def academy_fn(span):
    span = mark_tag(span, r'<h2>', "academy.title", "academy title")
    span = mark_first_p_after(span, "</h2>", "academy.intro", "academy intro")
    # The 4 list items, in order.
    n = [0]
    def item(m):
        n[0] += 1
        return f'<li data-edit="academy.item{n[0]}">'
    span = re.sub(r'<li>', item, span)
    if n[0] != 4:
        fail(f"expected 4 academy items, found {n[0]}")
    # Academy photo: the <img> whose alt starts "Peace Fashion Academy graduation".
    m = re.search(r'<img[^>]*alt="Peace Fashion Academy graduation[^>]*>', span)
    if not m:
        fail("academy image not found")
    tag = m.group(0)
    span = span[:m.start()] + tag[:-1] + ' data-edit="academy.image">' + span[m.end():]
    return span

html = mark_in_section(html, r'<section id="academy">', "academy", academy_fn)

# 9. Voices.
def voices_fn(span):
    span = mark_tag(span, r'<h2>', "voices.title", "voices title")
    span = mark_first_p_after(span, "</h2>", "voices.intro", "voices intro")
    # The 3 quotes, in order.
    n = [0]
    def quote(m):
        n[0] += 1
        return f'<blockquote data-edit="voices.quote{n[0]}">'
    span = re.sub(r'<blockquote>', quote, span)
    if n[0] != 3:
        fail(f"expected 3 voice quotes, found {n[0]}")
    return span

html = mark_in_section(html, r'<section class="voices" id="voices">', "voices", voices_fn)

# 10. Contact.
def contact_fn(span):
    span = mark_tag(span, r'<h2>', "contact.title", "contact title")
    span = mark_first_p_after(span, "</h2>", "contact.text", "contact text")
    # Button texts (their hrefs were marked by the global link pass).
    m = re.search(r'(<a[^>]*)(>Message @peace_fashion_hub</a>)', span)
    if not m:
        fail("contact Instagram button not found")
    span = span[:m.start()] + m.group(1) + ' data-edit="contact.instagramButton"' + m.group(2) + span[m.end():]
    m = re.search(r'(<a[^>]*)(>Order on WhatsApp</a>)', span)
    if not m:
        fail("contact WhatsApp button not found")
    span = span[:m.start()] + m.group(1) + ' data-edit="contact.whatsappButton"' + m.group(2) + span[m.end():]
    return span

html = mark_in_section(html, r'<section class="contact" id="contact">', "contact", contact_fn)

# 11. Brand line: the wordmark appears twice (header + footer) — mark both
# so they always stay the same.
new, n = re.subn(r'(<a class="wordmark"[^>]*)(>)',
                 lambda m: m.group(1) + ' data-edit="brand.wordmark"' + m.group(2), html)
if n != 2:
    fail(f"expected 2 wordmark links, found {n}")
html = new
print("brand.wordmark: 2 wordmarks marked")

# 12. Verify: every content key (except the two links) marked the expected
# number of times (once, except brand.wordmark which appears twice).
MULTI = {"brand.wordmark": 2}
import json
schema = json.loads((HERE / "content-schema.json").read_text(encoding="utf-8"))
keys = [f["key"] for s in schema["sections"] for f in s["fields"]]
missing, dupes = [], []
for key in keys:
    if key.startswith("link."):
        continue
    expect = MULTI.get(key, 1)
    n = html.count(f'data-edit="{key}"')
    if n == 0:
        missing.append(key)
    elif n != expect:
        dupes.append((key, n, expect))
if missing or dupes:
    if missing:
        print(f"ERROR: unmarked keys: {missing}", file=sys.stderr)
    if dupes:
        print(f"ERROR: wrong count (key, found, expected): {dupes}", file=sys.stderr)
    sys.exit(1)
print(f"content markers verified: {len(keys) - 2} text/image keys")

# 13. Loader script before </body> (once only).
if LOADER_MARKER not in html:
    if "</body>" not in html:
        fail("no </body> tag in export")
    html = html.replace("</body>", LOADER_SCRIPT + "</body>", 1)
    print("loader script injected")
else:
    print("loader script already present")

# 14. Admin thumbnails + content defaults. The admin page used to download
# the whole 17MB homepage to show the current photos and texts — that is
# why it took so long to load. Now the small files it needs are made here,
# at deploy time, from the marked page (so they always match it):
#   thumbs/piece-NN.jpg    — small (220px) thumbnail of each design
#   thumbs/<key>.jpg       — thumbnail of each editable photo
#   content-defaults.json  — the original text/link value of every field
# The admin page loads these instead (a few hundred KB total).
import base64
import html as html_mod
import io
import json as json_mod
from PIL import Image

THUMBS = HERE / "thumbs"
shutil.rmtree(THUMBS, ignore_errors=True)
THUMBS.mkdir(exist_ok=True)

def make_thumb(data_uri, out_path, width=220):
    _header, b64 = data_uri.split(",", 1)
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    w, h = img.size
    nw = min(width, w)
    img = img.resize((nw, round(h * nw / w)), Image.LANCZOS)
    img.save(out_path, "JPEG", quality=80)

def readable(inner):
    return re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()

defaults = {}
# Design thumbnails.
piece_imgs = re.findall(
    r'<button class="piece reveal" data-piece-id="(piece-\d+)"[^>]*>.*?<img[^>]*src="([^"]+)"',
    html, re.S)
if len(piece_imgs) != 27:
    fail(f"expected 27 piece images for thumbnails, found {len(piece_imgs)}")
for pid, src in piece_imgs:
    make_thumb(src, THUMBS / f"{pid}.jpg")
print(f"design thumbnails: {len(piece_imgs)}")

# Content defaults (texts, links, image thumbnails).
field_type = {f["key"]: f["type"] for s in schema["sections"] for f in s["fields"]}
for key in keys:
    if key.startswith("link."):
        m = re.search(r'<a[^>]*href="([^"]+)"[^>]*data-edit-href="' + re.escape(key) + r'"', html)
        if not m:
            fail(f"no link found for {key}")
        href = m.group(1)
        if key == "link.whatsapp":
            defaults[key] = href.replace("https://wa.me/", "")
        else:
            defaults[key] = href.replace("https://www.instagram.com/", "").rstrip("/")
        continue
    if field_type[key] == "image":
        m = re.search(r'<img[^>]*data-edit="' + re.escape(key) + r'"[^>]*>', html)
        if not m:
            fail(f"no image found for {key}")
        src_m = re.search(r'src="([^"]+)"', m.group(0))
        if not src_m:
            fail(f"image {key} has no src")
        fname = key.replace(".", "-") + ".jpg"
        make_thumb(src_m.group(1), THUMBS / fname)
        defaults[key] = f"/thumbs/{fname}"
        continue
    m = re.search(r'<(\w+)[^>]*data-edit="' + re.escape(key) + r'"[^>]*>(.*?)</\1>', html, re.S)
    if not m:
        fail(f"no element found for {key}")
    defaults[key] = readable(m.group(2))

(HERE / "content-defaults.json").write_text(
    json_mod.dumps(defaults, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"content defaults: {len(defaults)} keys -> content-defaults.json")

TARGET.write_text(html, encoding="utf-8")
print(f"wrote {TARGET} ({len(html)} bytes)")
