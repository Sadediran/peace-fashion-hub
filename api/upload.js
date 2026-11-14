// POST /api/upload — replace a gallery piece's photo and/or name, and/or
// hide or show it on the site.
// Body (JSON): {
//   "username": "peace",          // admin username
//   "password": "...",            // admin password (Peace's or Saheed's master)
//   "pieceId": "piece-01",        // must match piece-NN (2+ digits)
//   "image": "<base64 jpeg>",     // optional; a NEW photo to upload
//   "imageUrl": "<blob url>",     // optional; the CURRENT override photo to
//                                 // keep (for a name-only or hide-only change)
//   "oldImageUrl": "<blob url>",  // optional; the previous override photo to
//                                 // delete after a new photo is uploaded
//   "name": "New Name" | null,    // optional; string sets a name override,
//                                 // null removes it (back to the default name)
//   "hidden": true | false        // optional; true hides the piece from the
//                                 // site, false shows it again
// }
// The caller sends the full desired state, so this function never reads the
// store first (Blob CDN reads lag writes by ~60s and a read-modify-write
// would silently drop a just-saved change). Returns { ok, imageUrl? }.
import { put } from '@vercel/blob';
import { writeOverride, deleteBlobByUrl, checkCredentials } from './_lib.js';

const MAX_BYTES = 2 * 1024 * 1024; // admin page compresses photos first; 2 MB is ample

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
    const pieceId = body.pieceId;
    if (typeof pieceId !== 'string' || !/^piece-\d{2,}$/.test(pieceId)) {
      return res.status(400).json({ ok: false, error: 'bad piece id' });
    }
    const hasImage = typeof body.image === 'string' && body.image.length > 0;
    const hasName = Object.prototype.hasOwnProperty.call(body, 'name');
    const hasHidden = Object.prototype.hasOwnProperty.call(body, 'hidden');
    if (!hasImage && !hasName && !hasHidden) {
      return res.status(400).json({ ok: false, error: 'nothing to change' });
    }

    const next = {};

    if (hasImage) {
      let buf;
      try {
        buf = Buffer.from(body.image, 'base64');
      } catch {
        return res.status(400).json({ ok: false, error: 'bad image data' });
      }
      if (buf.length === 0 || buf.length > MAX_BYTES) {
        return res.status(400).json({ ok: false, error: 'image too large' });
      }
      // JPEG magic bytes (client always sends a compressed JPEG).
      if (buf[0] !== 0xff || buf[1] !== 0xd8) {
        return res.status(400).json({ ok: false, error: 'image must be a JPEG photo' });
      }
      const path = `uploads/${pieceId}-${Date.now()}.jpg`;
      const blob = await put(path, buf, {
        access: 'public',
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: 'image/jpeg',
      });
      next.image = blob.url;
    } else if (typeof body.imageUrl === 'string' && body.imageUrl) {
      next.image = body.imageUrl;
    }

    if (hasName && typeof body.name === 'string' && body.name.trim()) {
      next.name = body.name.trim().slice(0, 80);
    }

    if (hasHidden && body.hidden === true) {
      next.hidden = true;
    }

    await writeOverride(pieceId, next);

    // Free the old override photo (best effort; never fail the save over this).
    if (hasImage && typeof body.oldImageUrl === 'string' && body.oldImageUrl && body.oldImageUrl !== next.image) {
      try {
        await deleteBlobByUrl(body.oldImageUrl);
      } catch (err) {
        console.error('could not delete old override image', body.oldImageUrl, err);
      }
    }

    return res.status(200).json({ ok: true, imageUrl: next.image || null });
  } catch (err) {
    console.error('upload failed', err);
    return res.status(500).json({ ok: false, error: 'upload failed — please try again' });
  }
}
