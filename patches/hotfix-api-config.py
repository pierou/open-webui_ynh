#!/usr/bin/env python3
"""Hotfix: make /api/config resolve sessions through the shared helper.

Target: /var/www/open-webui/backend/open_webui/main.py  (Open WebUI 0.11.3)
Refuses to write unless the old block appears exactly once.
Backup: /root/main.py.bak   Rollback: cp it back + systemctl restart open-webui
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
