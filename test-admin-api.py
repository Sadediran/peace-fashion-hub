#!/usr/bin/env python3
"""End-to-end API test for the Peace Fashion Hub admin backend.

Usage: python3 test-admin-api.py <master-password>
The master password is passed on the command line (never stored in a file).

Tests, in order (each step cleans up after itself):
  1. auth: master password works; wrong password / wrong username rejected.
  2. content: save text overrides, verify via /api/site, then reset them.
  3. content image: upload a photo override, verify, then reset (deletes it).
  4. add piece: add a test design, hide it, unhide it, delete it.
  5. hide an original design, then restore it.
  6. password change + username change: set a test password, verify both
     passwords work; change the username, verify the master sign-in
     ('peace' + master) is unaffected and the old username stops working;
     change the username back to 'peace' and the password back to the
     master password. (There is no remove-password endpoint any more —
     Saheed removed it — so the test ends with a credential holding
     username 'peace' and the master password's hash, which behaves
     exactly like the fresh state: only the master sign-in works.)
  7. final state: overrides, content and added are all empty.

Reads of /api/site are polled (up to 90s) because Blob CDN reads can lag
a save by up to ~60s.
"""
import base64
import io
import json
import sys
import time
import urllib.error
import urllib.request

BASE = 'https://peace-fashion-hub.vercel.app'
MASTER = sys.argv[1]
USER = 'peace'
TEST_PW = 'TestPass12345'  # temporary; removed by the test itself

failures = []


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get_site():
    with urllib.request.urlopen(BASE + '/api/site', timeout=30) as r:
        return json.loads(r.read())


def poll_site(label, pred, timeout=90):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = get_site()
        if pred(last):
            print('PASS -', label)
            return last
        time.sleep(5)
    print('FAIL -', label, '| last state:', json.dumps(last)[:300])
    failures.append(label)
    return last


def check(label, cond, extra=''):
    print(('PASS' if cond else 'FAIL'), '-', label, extra)
    if not cond:
        failures.append(label)


def tiny_jpeg():
    from PIL import Image
    img = Image.new('RGB', (8, 8), color=(200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, 'JPEG')
    return base64.b64encode(buf.getvalue()).decode()


JPEG = tiny_jpeg()

# 1. Auth
s, r = post('/api/auth', {'username': USER, 'password': MASTER})
check('auth: master password works', s == 200 and r.get('ok'))
s, r = post('/api/auth', {'username': USER, 'password': 'wrongpassword'})
check('auth: wrong password rejected', s == 401)
s, r = post('/api/auth', {'username': 'someone', 'password': MASTER})
check('auth: wrong username rejected', s == 401)

# Initial state should be clean.
site = get_site()
check('initial state clean', site.get('overrides') == {} and site.get('content') == {} and site.get('added') == {},
      json.dumps(site)[:200])

# 2. Content: text overrides.
s, r = post('/api/content', {'username': USER, 'password': MASTER,
                             'doc': {'hero.title': 'TEST TITLE', 'voices.quote1': 'TEST QUOTE'}})
check('content: save text overrides', s == 200 and r.get('ok'), str(r)[:150])
poll_site('content: text overrides visible',
          lambda d: d.get('content', {}).get('hero.title') == 'TEST TITLE'
          and d.get('content', {}).get('voices.quote1') == 'TEST QUOTE')

# 3. Content: image override (keeps the text overrides).
s, r = post('/api/content', {'username': USER, 'password': MASTER,
                             'doc': {'hero.title': 'TEST TITLE', 'voices.quote1': 'TEST QUOTE'},
                             'images': {'hero.image': JPEG}})
check('content: save image override', s == 200 and r.get('ok'), str(r)[:200])
hero_img = (r.get('doc') or {}).get('hero.image', '')
check('content: image override is a Blob URL', hero_img.startswith('https://') and 'blob.vercel-storage.com' in hero_img, hero_img[:80])
poll_site('content: image override visible',
          lambda d: d.get('content', {}).get('hero.image', '').startswith('https://'))

# Reset all content (removes the text overrides + deletes the test photo).
s, r = post('/api/content', {'username': USER, 'password': MASTER, 'doc': {},
                             'deleteImages': [hero_img] if hero_img else []})
check('content: reset to empty doc', s == 200 and r.get('ok'), str(r)[:150])
poll_site('content: empty after reset', lambda d: d.get('content') == {})

# 4. Add a design.
s, r = post('/api/add-piece', {'username': USER, 'password': MASTER, 'name': 'TEST DESIGN',
                               'category': 'couture', 'desc': 'test design', 'image': JPEG})
check('add-piece: adds a design', s == 200 and r.get('ok'), str(r)[:200])
new_id = r.get('id')
new_img = r.get('imageUrl')
check('add-piece: id is piece-28+', new_id and new_id.startswith('piece-') and int(new_id.split('-')[1]) >= 28, str(new_id))
poll_site('add-piece: visible in /api/site',
          lambda d: new_id in (d.get('added') or {}))

# Hide it, then unhide it.
s, r = post('/api/upload', {'username': USER, 'password': MASTER, 'pieceId': new_id,
                            'hidden': True, 'name': None})
check('hide: added design hides', s == 200 and r.get('ok'), str(r)[:150])
poll_site('hide: override shows hidden',
          lambda d: (d.get('overrides') or {}).get(new_id, {}).get('hidden') is True)
s, r = post('/api/upload', {'username': USER, 'password': MASTER, 'pieceId': new_id,
                            'hidden': False, 'name': None})
check('unhide: added design unhides', s == 200 and r.get('ok'), str(r)[:150])
poll_site('unhide: hidden flag gone',
          lambda d: (d.get('overrides') or {}).get(new_id, {}).get('hidden') is not True)

# Delete it.
s, r = post('/api/delete-piece', {'username': USER, 'password': MASTER, 'pieceId': new_id,
                                  'imageUrl': new_img})
check('delete-piece: removes the design', s == 200 and r.get('ok'), str(r)[:150])
poll_site('delete-piece: gone from /api/site',
          lambda d: new_id not in (d.get('added') or {}) and new_id not in (d.get('overrides') or {}))

# 5. Hide an original design, then restore it.
s, r = post('/api/upload', {'username': USER, 'password': MASTER, 'pieceId': 'piece-01',
                            'hidden': True, 'name': None})
check('hide: original design hides', s == 200 and r.get('ok'), str(r)[:150])
poll_site('hide: original override shows hidden',
          lambda d: (d.get('overrides') or {}).get('piece-01', {}).get('hidden') is True)
s, r = post('/api/reset', {'username': USER, 'password': MASTER, 'pieceId': 'piece-01'})
check('reset: original design restores', s == 200 and r.get('ok'), str(r)[:150])
poll_site('reset: override gone', lambda d: 'piece-01' not in (d.get('overrides') or {}))

# 6. Password change + username change.
s, r = post('/api/change-password', {'username': USER, 'currentPassword': MASTER,
                                     'newPassword': TEST_PW})
check('change-password: sets a new password', s == 200 and r.get('ok'), str(r)[:150])
s, r = post('/api/auth', {'username': USER, 'password': TEST_PW})
check('change-password: new password works', s == 200 and r.get('ok'))
s, r = post('/api/auth', {'username': USER, 'password': MASTER})
check('change-password: master password still works', s == 200 and r.get('ok'))
s, r = post('/api/change-password', {'username': USER, 'currentPassword': 'wrongpassword',
                                     'newPassword': 'AnotherTest123'})
check('change-password: wrong current password rejected', s == 401)
s, r = post('/api/change-username', {'username': USER, 'currentPassword': TEST_PW,
                                     'newUsername': 'testuser'})
check('change-username: changes the username', s == 200 and r.get('ok') and r.get('username') == 'testuser', str(r)[:150])
s, r = post('/api/auth', {'username': 'testuser', 'password': TEST_PW})
check('change-username: new username works', s == 200 and r.get('ok'))
s, r = post('/api/auth', {'username': USER, 'password': MASTER})
check('change-username: master sign-in (peace + master) still works', s == 200 and r.get('ok'))
s, r = post('/api/auth', {'username': USER, 'password': TEST_PW})
check('change-username: old username no longer works with her password', s == 401)
s, r = post('/api/auth', {'username': 'testuser', 'password': MASTER})
check('change-username: master password does not work with the new username', s == 401)
s, r = post('/api/change-username', {'username': 'testuser', 'currentPassword': 'wrongpassword',
                                     'newUsername': 'anotheruser'})
check('change-username: wrong current password rejected', s == 401)
s, r = post('/api/change-username', {'username': 'testuser', 'currentPassword': TEST_PW,
                                     'newUsername': USER})
check('change-username: changes the username back', s == 200 and r.get('ok'), str(r)[:150])
s, r = post('/api/auth', {'username': USER, 'password': TEST_PW})
check('change-username: original username works again', s == 200 and r.get('ok'))
# Put the password back to the master password (no remove endpoint any
# more — this leaves a credential for 'peace' holding the master
# password's hash, which behaves exactly like the fresh state).
s, r = post('/api/change-password', {'username': USER, 'currentPassword': TEST_PW,
                                     'newPassword': MASTER})
check('change-password: password restored to master', s == 200 and r.get('ok'), str(r)[:150])
s, r = post('/api/auth', {'username': USER, 'password': MASTER})
check('change-password: master sign-in works after restore', s == 200 and r.get('ok'))
s, r = post('/api/auth', {'username': USER, 'password': TEST_PW})
check('change-password: test password no longer works', s == 401)

# 7. Final state clean.
site = poll_site('final state clean',
                 lambda d: d.get('overrides') == {} and d.get('content') == {} and d.get('added') == {})

print()
if failures:
    print(f'{len(failures)} FAILURES:', failures)
    sys.exit(1)
print('ALL TESTS PASSED')
