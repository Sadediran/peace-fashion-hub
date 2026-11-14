// POST /api/content — save the site-content document (texts, photos, links).
// Body (JSON): {
//   "username": "peace",            // admin username
//   "password": "...",              // admin password (Peace's or Saheed's master)
//   "doc": { "<contentKey>": "<value>", ... },  // FULL document — the admin
//                                               // sends every key it knows,
//                                               // so this overwrites without
//                                               // reading first (no race).
//   "images": { "<imageKey>": "<base64 jpeg>" }, // optional; new photos to
//                                               // upload (replaces doc values)
//   "oldImages": { "<imageKey>": "<blob url>" }  // optional; old photos to
//                                               // delete after upload
// }
// Keys must be in the CONTENT_KEYS allowlist. Text values are capped at
// 5000 chars. Image values in the doc must be Blob URLs from this store.
// link.whatsapp must be digits (10-15); link.instagram a valid handle.
// Returns { ok, doc } with the saved document.
import { put } from '@vercel/blob';
import {
  BLOB_BASE, CONTENT_KEYS, IMAGE_KEYS, writeContentDoc, deleteBlobByUrl,
  checkCredentials,
} from './_lib.js';

const MAX_BYTES = 2 * 1024 * 1024;
const MAX_TEXT = 5000;

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'method not allowed' });
  }
  try {
    const body = req.body || {};
    if (!(await checkCredentials(body.username, body.password))) {
      return res.status(401).json({ ok: false, error: 'wrong username or password' });
    }
    const doc = body.doc;
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
      return res.status(400).json({ ok: false, error: 'bad document' });
    }
    // Validate every key/value.
    for (const [key, value] of Object.entries(doc)) {
      if (!CONTENT_KEYS.has(key)) {
        return res.status(400).json({ ok: false, error: `unknown field: ${key}` });
      }
      if (typeof value !== 'string' || value.length === 0 || value.length > MAX_TEXT) {
        return res.status(400).json({ ok: false, error: `bad value for: ${key}` });
      }
      if (IMAGE_KEYS.has(key) && !value.startsWith(BLOB_BASE + '/')) {
        return res.status(400).json({ ok: false, error: `bad photo for: ${key}` });
      }
      if (key === 'link.whatsapp' && !/^\d{10,15}$/.test(value)) {
        return res.status(400).json({ ok: false, error: 'WhatsApp number must be digits only, with country code' });
      }
      if (key === 'link.instagram' && !/^[A-Za-z0-9._]{1,30}$/.test(value)) {
        return res.status(400).json({ ok: false, error: 'Instagram username is not valid' });
      }
    }
    // Upload any new photos, replacing their doc values with Blob URLs.
    const images = body.images || {};
    const oldImages = body.oldImages || {};
    for (const [key, b64] of Object.entries(images)) {
      if (!IMAGE_KEYS.has(key) || typeof b64 !== 'string' || !b64) {
        return res.status(400).json({ ok: false, error: `bad photo for: ${key}` });
      }
      let buf;
      try {
        buf = Buffer.from(b64, 'base64');
      } catch {
        return res.status(400).json({ ok: false, error: `bad photo data for: ${key}` });
      }
      if (buf.length === 0 || buf.length > MAX_BYTES || buf[0] !== 0xff || buf[1] !== 0xd8) {
        return res.status(400).json({ ok: false, error: `photo must be a JPEG under 2 MB: ${key}` });
      }
      const safeKey = key.replace(/\./g, '-');
      const blob = await put(`content-uploads/${safeKey}-${Date.now()}.jpg`, buf, {
        access: 'public',
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: 'image/jpeg',
      });
      doc[key] = blob.url;
      const old = oldImages[key];
      if (typeof old === 'string' && old && old !== blob.url) {
        try {
          await deleteBlobByUrl(old);
        } catch (err) {
          console.error('could not delete old content photo', old, err);
        }
      }
    }
    // Delete photos for image fields that were reset to their default.
    const deleteImages = Array.isArray(body.deleteImages) ? body.deleteImages : [];
    for (const url of deleteImages) {
      if (typeof url === 'string' && url.startsWith(BLOB_BASE + '/')) {
        try {
          await deleteBlobByUrl(url);
        } catch (err) {
          console.error('could not delete reset photo', url, err);
        }
      }
    }
    await writeContentDoc(doc);
    return res.status(200).json({ ok: true, doc });
  } catch (err) {
    console.error('content save failed', err);
    return res.status(500).json({ ok: false, error: 'save failed — please try again' });
  }
}
