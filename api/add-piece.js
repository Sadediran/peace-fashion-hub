// POST /api/add-piece — add a new design to the gallery.
// Body (JSON): {
//   "username": "peace",
//   "password": "...",
//   "name": "Design name",        // 1-80 chars
//   "category": "bridal"|"occasion"|"couture",
//   "image": "<base64 jpeg>",     // the design photo
//   "desc": "Short description"   // optional, up to 200 chars
// }
// Assigns the next free piece id (piece-28 and up), uploads the photo,
// writes added/piece-NN.json. Returns { ok, id, imageUrl }.
import { put } from '@vercel/blob';
import { nextPieceId, writeAdded, checkCredentials } from './_lib.js';

const MAX_BYTES = 2 * 1024 * 1024;
const CATEGORIES = new Set(['bridal', 'occasion', 'couture']);

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
    const name = typeof body.name === 'string' ? body.name.trim() : '';
    if (!name || name.length > 80) {
      return res.status(400).json({ ok: false, error: 'give the design a name' });
    }
    if (!CATEGORIES.has(body.category)) {
      return res.status(400).json({ ok: false, error: 'pick a collection for the design' });
    }
    if (typeof body.image !== 'string' || !body.image) {
      return res.status(400).json({ ok: false, error: 'pick a photo for the design' });
    }
    let buf;
    try {
      buf = Buffer.from(body.image, 'base64');
    } catch {
      return res.status(400).json({ ok: false, error: 'bad photo data' });
    }
    if (buf.length === 0 || buf.length > MAX_BYTES || buf[0] !== 0xff || buf[1] !== 0xd8) {
      return res.status(400).json({ ok: false, error: 'photo must be a JPEG under 2 MB' });
    }
    const desc = typeof body.desc === 'string' ? body.desc.trim().slice(0, 200) : '';
    const id = await nextPieceId();
    const blob = await put(`uploads/${id}-${Date.now()}.jpg`, buf, {
      access: 'public',
      addRandomSuffix: false,
      allowOverwrite: true,
      contentType: 'image/jpeg',
    });
    await writeAdded(id, { name, category: body.category, image: blob.url, desc });
    return res.status(200).json({ ok: true, id, imageUrl: blob.url });
  } catch (err) {
    console.error('add-piece failed', err);
    return res.status(500).json({ ok: false, error: 'could not add the design — please try again' });
  }
}
