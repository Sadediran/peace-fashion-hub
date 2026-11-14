// POST /api/reset — remove a piece's override (photo, name and hidden flag),
// restoring the original photo and name from the site.
// Body: { "username": "peace", "password": "...", "pieceId": "piece-01",
//         "imageUrl": "<blob url>" } — imageUrl is the override photo to
// delete (sent by the admin page, which knows it); optional.
// The override file is deleted directly, with no read first, so the reset
// can never be a silent no-op when the store listing lags a recent save.
import { deleteOverride, deleteBlobByUrl, checkCredentials } from './_lib.js';

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
    await deleteOverride(pieceId);
    if (typeof body.imageUrl === 'string' && body.imageUrl) {
      try {
        await deleteBlobByUrl(body.imageUrl);
      } catch (err) {
        console.error('could not delete old override image', body.imageUrl, err);
      }
    }
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('reset failed', err);
    return res.status(500).json({ ok: false, error: 'reset failed — please try again' });
  }
}
