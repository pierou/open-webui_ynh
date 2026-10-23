#!/usr/bin/env python3
"""Hotfix: make /api/config resolve sessions through the shared helper.

Target: /var/www/open-webui/backend/open_webui/main.py  (Open WebUI 0.11.3)
Refuses to write unless the old block appears exactly once.
Backup: /root/main.py.bak   Rollback: cp it back + systemctl restart open-webui

STATUS (verified 2026-10-23): DO NOT USE. Two independent reasons.
1. Wrong file. This tree is NOT the running code. scripts/upgrade runs
   `venv/bin/pip install open-webui==X`, so the served code is the PyPI wheel
   in $install_dir/venv/lib/python3.11/site-packages/open_webui/, and
   conf/systemd.service starts `venv/bin/open-webui serve`. The extracted
   GitHub tarball under $install_dir/backend/ is inert - ynh_setup_source only
   auto-applies `patches/<source_id>/*.patch` (i.e. patches/main/), and this
   file is not there either.
2. Anchor is stale. v0.12.3 main.py:2303 reads
   `if data is not None and 'id' in data and await is_valid_token(data, request.app.state.redis):`
   so OLD no longer matches and this script aborts safely (untouched file).

The web-search symptom was fixed for real in conf/nginx.conf by clearing the
inherited ssowat access phase (commit b3d3c7575), which is version-independent.
Upstream still has NOT fixed /api/config as of v0.12.3 - keep the nginx fix.
Kept here as the upstream-PR text only.
"""
import shutil

P = '/var/www/open-webui/backend/open_webui/main.py'
BAK = '/root/main.py.bak'

OLD = """    user = None
    token = None

    auth_header = request.headers.get('Authorization')
    if auth_header:
        cred = get_http_authorization_cred(auth_header)
        if cred:
            token = cred.credentials

    if not token and 'token' in request.cookies:
        token = request.cookies.get('token')

    if token:
        try:
            data = decode_token(token)
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token',
            )
        if data is not None and 'id' in data:
            user = await Users.get_user_by_id(data['id'])
"""

NEW = """    try:
        user = await get_optional_verified_user_from_request(request)
    except HTTPException:
        user = None
"""

s = open(P).read()

if 'get_optional_verified_user_from_request' in s and 'await get_optional_verified_user_from_request(request)' in s:
    print('ALREADY PATCHED - nothing to do')
    raise SystemExit(0)

n = s.count(OLD)
if n != 1:
    print('ABORT: anchor matched %d times, file untouched' % n)
    raise SystemExit(1)

print('import present:', 'get_optional_verified_user_from_request,' in s)
shutil.copy2(P, BAK)
print('backup:', BAK)

s = s.replace(OLD, NEW, 1)
compile(s, P, 'exec')
open(P, 'w').write(s)
print('PATCHED ok - now: sudo systemctl restart open-webui')
