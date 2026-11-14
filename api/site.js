// GET /api/site — returns everything the public page and the admin page
// need to show the current customisations:
//   { overrides: {pieceId: {image?, name?, hidden?}},
//     content: {contentKey: value},
//     added: {pieceId: {id, name, category, image, desc?}} }
// Public (no password): the data is public website content.
import { listOverrides, readContentDoc, listAdded } from './_lib.js';

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method !== 'GET') {
    return res.status(405).json({ ok: false, error: 'method not allowed' });
  }
  const [overrides, content, added] = await Promise.all([
    listOverrides(),
    readContentDoc(),
    listAdded(),
  ]);
  return res.status(200).json({ ok: true, overrides, content, added });
}
