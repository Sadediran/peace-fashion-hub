// POST /api/delete-piece — permanently delete a design that was ADDED
// through the admin page (piece-28 and up). Original designs (piece-01..27)
// cannot be deleted, only hidden.
// Body: { "username": "peace", "password": "...", "pieceId": "piece-28",
//         "imageUrl": "<blob url>" } — imageUrl is the design photo to
// delete (sent by the admin page); optional.
import { deleteAdded, deleteOverride, deleteBlobByUrl, checkCredentials, isPieceId } from './_lib.js';

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
    if (!isPieceId(pieceId)) {
      return res.status(400).json({ ok: false, error: 'bad piece id' });
    }
    const n = parseInt(pieceId.replace('piece-', ''), 10);
    if (n <= 27) {
      return res.status(400).json({ ok: false, error: 'original designs cannot be deleted — hide them instead' });
    }
    // Remove any photo/name override for the piece, then the piece itself.
    try {
      await deleteOverride(pieceId);
    } catch {}
    await deleteAdded(pieceId);
    if (typeof body.imageUrl === 'string' && body.imageUrl) {
      try {
        await deleteBlobByUrl(body.imageUrl);
      } catch (err) {
        console.error('could not delete design photo', body.imageUrl, err);
      }
    }
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('delete-piece failed', err);
    return res.status(500).json({ ok: false, error: 'could not delete the design — please try again' });
  }
}
