// Shared helpers for the Peace Fashion Hub admin API functions.
// Files starting with _ in api/ are not treated as functions by Vercel.
import { put, del, list } from '@vercel/blob';
import { timingSafeEqual, scryptSync, randomBytes } from 'node:crypto';

// Public Blob store 'peace-fashion-hub-images' (easyall team).
// Public URL base — not a secret. If the store is ever recreated, update this.
export const BLOB_BASE = 'https://equaeh2ua6pqkfjr.public.blob.vercel-storage.com';

// ---------------------------------------------------------------------------
// Gallery piece overrides: one JSON file per piece, overrides/piece-NN.json
// {"image": "<blob url>", "name": "<new name>", "hidden": true?}.
// Per-piece files (not one shared file) because the Blob CDN caches reads
// for ~60s — a read-modify-write of a single shared file silently dropped a
// just-saved change (found in testing 14 Nov). Writes never read first.
export function overridePath(pieceId) {
  return `overrides/${pieceId}.json`;
}
export function overrideUrl(pieceId) {
  return `${BLOB_BASE}/${overridePath(pieceId)}`;
}

// Current overrides, from the store listing (API call, consistent — not
// CDN-cached). File contents may lag a save by up to ~60s (CDN), which is
// fine: the site shows the new photo within about a minute.
export async function listOverrides() {
  try {
    const { blobs } = await list({ prefix: 'overrides/' });
    const entries = await Promise.all(
      blobs.map(async (b) => {
        const m = /^overrides\/(piece-\d+)\.json$/.exec(b.pathname || '');
        if (!m) return null;
        try {
          const r = await fetch(b.url, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
          });
          if (!r.ok) return null;
          const data = await r.json();
          if (!data || typeof data !== 'object') return null;
          return [m[1], data];
        } catch {
          return null;
        }
      }),
    );
    return Object.fromEntries(entries.filter(Boolean));
  } catch {
    return {};
  }
}

export async function writeOverride(pieceId, data) {
  await put(overridePath(pieceId), JSON.stringify(data), {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
    cacheControlMaxAge: 0,
    contentType: 'application/json',
  });
}

export async function deleteOverride(pieceId) {
  await del(overrideUrl(pieceId));
}

export async function deleteBlobByUrl(url) {
  await del(url);
}

// ---------------------------------------------------------------------------
// Site content: a SINGLE document, content/site.json, mapping content keys
// to values. The admin always sends the full document on save, so the
// function overwrites without reading first (no read-modify-write race).
// Keys must match content-schema.json (served at /content-schema.json) and
// the data-edit markers added by prepare-deploy.py.
export const CONTENT_KEYS = new Set([
  'about.bio1', 'about.bio2', 'about.credits', 'about.image', 'about.method',
  'about.quote', 'about.title', 'academy.image', 'academy.intro',
  'academy.item1', 'academy.item2', 'academy.item3', 'academy.item4',
  'academy.title', 'atelier.intro', 'atelier.note', 'atelier.step1.text',
  'atelier.step1.title', 'atelier.step2.text', 'atelier.step2.title',
  'atelier.step3.text', 'atelier.step3.title', 'atelier.step4.text',
  'atelier.step4.title', 'atelier.title', 'collections.bridal.image',
  'collections.bridal.text', 'collections.bridal.title', 'collections.intro',
  'collections.occasion.image', 'collections.occasion.text',
  'collections.occasion.title', 'collections.poise.image',
  'collections.poise.text', 'collections.poise.title', 'collections.title',
  'contact.instagramButton', 'contact.text', 'contact.title',
  'contact.whatsappButton', 'brand.wordmark', 'hero.eyebrow', 'hero.fact1',
  'hero.fact2', 'hero.fact3', 'hero.image', 'hero.lede', 'hero.title',
  'link.instagram', 'link.whatsapp', 'pieces.intro', 'pieces.title',
  'voices.intro', 'voices.quote1', 'voices.quote2', 'voices.quote3',
  'voices.title',
]);
export const IMAGE_KEYS = new Set([
  'hero.image', 'collections.bridal.image', 'collections.occasion.image',
  'collections.poise.image', 'about.image', 'academy.image',
]);

export const CONTENT_DOC_URL = `${BLOB_BASE}/content/site.json`;

export async function readContentDoc() {
  try {
    const r = await fetch(CONTENT_DOC_URL + '?t=' + Date.now(), {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
    });
    if (!r.ok) return {};
    const data = await r.json();
    return data && typeof data === 'object' ? data : {};
  } catch {
    return {};
  }
}

export async function writeContentDoc(doc) {
  await put('content/site.json', JSON.stringify(doc), {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
    cacheControlMaxAge: 0,
    contentType: 'application/json',
  });
}

// ---------------------------------------------------------------------------
// Added designs: one JSON file per added piece, added/piece-NN.json
// {"name", "category", "image", "desc"}. Original pieces are piece-01..27;
// added pieces are piece-28 and up.
export function addedPath(pieceId) {
  return `added/${pieceId}.json`;
}
export function addedUrl(pieceId) {
  return `${BLOB_BASE}/${addedPath(pieceId)}`;
}

export async function listAdded() {
  try {
    const { blobs } = await list({ prefix: 'added/' });
    const entries = await Promise.all(
      blobs.map(async (b) => {
        const m = /^added\/(piece-\d+)\.json$/.exec(b.pathname || '');
        if (!m) return null;
        try {
          const r = await fetch(b.url, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
          });
          if (!r.ok) return null;
          const data = await r.json();
          if (!data || typeof data !== 'object' || !data.name || !data.image) return null;
          return [m[1], { id: m[1], ...data }];
        } catch {
          return null;
        }
      }),
    );
    return Object.fromEntries(entries.filter(Boolean));
  } catch {
    return {};
  }
}

// Next free piece id: one above the highest existing (originals end at 27).
export async function nextPieceId() {
  const added = await listAdded();
  let max = 27;
  for (const id of Object.keys(added)) {
    const n = parseInt(id.replace('piece-', ''), 10);
    if (!Number.isNaN(n) && n > max) max = n;
  }
  return `piece-${String(max + 1).padStart(2, '0')}`;
}

export async function writeAdded(pieceId, data) {
  await put(addedPath(pieceId), JSON.stringify(data), {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
    cacheControlMaxAge: 0,
    contentType: 'application/json',
  });
}

export async function deleteAdded(pieceId) {
  await del(addedUrl(pieceId));
}

// ---------------------------------------------------------------------------
// Admin sign-in: username + password.
// The starting username is ADMIN_USERNAME ('peace'). Peace can change her
// username and her password herself, from the admin page
// (POST /api/change-username, POST /api/change-password). Her sign-in is
// stored as a salted scrypt hash in Blob (auth/<random>.json, newest file
// wins — the file holds her current username, salt and hash).
// Saheed's master sign-in — username "peace" + the ADMIN_PASSWORD env var —
// always works, whatever Peace calls herself. It is the recovery route:
// if Peace ever forgets her password, she signs in with the master password
// and sets a new one. A fresh install has no Blob credential yet, so only
// the master sign-in works until Peace sets her own password or username.
// The credential file's name is a random 128-bit hex string (unguessable,
// unlinked); it holds only a salted hash, never the password itself.
export const ADMIN_USERNAME = 'peace';

// Newest credential file (by upload time), or null if Peace has not set a
// password yet. Listing is an API call (consistent); each password change
// writes a brand-new file, so reads are never stale.
async function readLatestCredential() {
  try {
    const { blobs } = await list({ prefix: 'auth/' });
    const creds = blobs
      .filter((b) => /^auth\/[0-9a-f]{32}\.json$/.test(b.pathname || ''))
      .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
    if (!creds.length) return null;
    const r = await fetch(creds[0].url, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
    });
    if (!r.ok) return null;
    const data = await r.json();
    if (!data || typeof data.salt !== 'string' || typeof data.hash !== 'string') return null;
    return data;
  } catch {
    return null;
  }
}

function hashPassword(password, saltHex) {
  return scryptSync(password, Buffer.from(saltHex, 'hex'), 64).toString('hex');
}

export async function writeCredential(password, username) {
  const user = String(username || ADMIN_USERNAME).trim().toLowerCase() || ADMIN_USERNAME;
  const salt = randomBytes(16).toString('hex');
  const hash = hashPassword(password, salt);
  const name = `auth/${randomBytes(16).toString('hex')}.json`;
  await put(name, JSON.stringify({
    username: user, salt, hash, createdAt: new Date().toISOString(),
  }), {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
    cacheControlMaxAge: 0,
    contentType: 'application/json',
  });
  // Remove older credential files (best effort) so only the newest works.
  try {
    const { blobs } = await list({ prefix: 'auth/' });
    for (const b of blobs) {
      if (b.pathname !== name && /^auth\/[0-9a-f]{32}\.json$/.test(b.pathname || '')) {
        try {
          await del(b.url);
        } catch {}
      }
    }
  } catch {}
}

export async function checkCredentials(username, password) {
  if (typeof username !== 'string' || typeof password !== 'string' || !username || !password) return false;
  const user = username.trim().toLowerCase();
  // Peace's credential (if she has set a password or changed her username).
  const cred = await readLatestCredential();
  if (cred && user === String(cred.username || '').trim().toLowerCase()) {
    try {
      const attempt = Buffer.from(hashPassword(password, cred.salt), 'hex');
      const expected = Buffer.from(cred.hash, 'hex');
      if (attempt.length === expected.length && timingSafeEqual(attempt, expected)) return true;
    } catch {}
  }
  // Saheed's master sign-in: username "peace" + the master password. It
  // always works, whatever Peace calls herself — it is the recovery route.
  if (user === ADMIN_USERNAME) {
    const master = process.env.ADMIN_PASSWORD || '';
    if (!master) return false;
    const a = Buffer.from(password);
    const b = Buffer.from(master);
    return a.length === b.length && timingSafeEqual(a, b);
  }
  return false;
}

export function isPieceId(s) {
  return typeof s === 'string' && /^piece-\d{2,}$/.test(s);
}
