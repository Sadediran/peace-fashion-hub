// POST /api/change-username — Peace changes her admin username.
// Body: {
//   "username": "<current username>",
//   "currentPassword": "...",   // her current password, or Saheed's master password
//   "newUsername": "<new>"      // 3-30 chars, letters, numbers, dots, underscores
// }
// Verifies the current sign-in, then writes a new credential file with the
// new username and the same password (re-hashed with a fresh salt).
// Saheed's master sign-in (username "peace" + the master password) is
// unaffected and keeps working.
import { checkCredentials, writeCredential } from './_lib.js';

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'method not allowed' });
  }
  try {
    const body = req.body || {};
    if (!(await checkCredentials(body.username, body.currentPassword))) {
      return res.status(401).json({ ok: false, error: 'your current password is not correct' });
    }
    const next = typeof body.newUsername === 'string' ? body.newUsername.trim().toLowerCase() : '';
    if (!/^[a-z0-9._]{3,30}$/.test(next)) {
      return res.status(400).json({ ok: false, error: 'username: 3–30 characters, letters, numbers, dots and underscores' });
    }
    const current = String(body.username || '').trim().toLowerCase();
    if (next === current) {
      return res.status(400).json({ ok: false, error: 'that is already your username' });
    }
    await writeCredential(body.currentPassword, next);
    return res.status(200).json({ ok: true, username: next });
  } catch (err) {
    console.error('change-username failed', err);
    return res.status(500).json({ ok: false, error: 'could not change the username — please try again' });
  }
}
