// POST /api/auth — check the admin username + password.
// Body: { "username": "peace", "password": "..." }
// Returns { ok: true } on a match, { ok: false, error } otherwise.
import { checkCredentials } from './_lib.js';

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'method not allowed' });
  }
  const body = req.body || {};
  if (await checkCredentials(body.username, body.password)) {
    return res.status(200).json({ ok: true });
  }
  return res.status(401).json({ ok: false, error: 'wrong username or password' });
}
