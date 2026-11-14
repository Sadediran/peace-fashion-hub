// POST /api/change-password — Peace changes her own admin password.
// Body: {
//   "username": "peace",
//   "currentPassword": "...",   // her current password, or Saheed's master password
//   "newPassword": "..."        // at least 8 characters
// }
// Writes a new credential file; the old password stops working immediately
// (the old credential files are deleted). Saheed's master password (the
// ADMIN_PASSWORD env var) still works after the change — it is the recovery
// route if she ever forgets hers.
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
    const next = body.newPassword;
    if (typeof next !== 'string' || next.length < 8 || next.length > 100) {
      return res.status(400).json({ ok: false, error: 'the new password must be at least 8 characters' });
    }
    if (next === body.currentPassword) {
      return res.status(400).json({ ok: false, error: 'the new password must be different from the current one' });
    }
    await writeCredential(next, body.username);
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('change-password failed', err);
    return res.status(500).json({ ok: false, error: 'could not change the password — please try again' });
  }
}
