# `/api/config` ignores proxy-injected credentials, so web search can never appear

## Symptom

Web search is enabled and fully working at the HTTP layer, but the search control
never renders in the chat input for any model.

## Measured on a YunoHost 12 + ssowat + Cloudflare install (Open WebUI 0.11.3)

| request | result |
|---|---|
| `GET 127.0.0.1:PORT/api/config` + `Authorization: Bearer <minted admin JWT>` | `200`, full block, `features.enable_web_search: true` |
| browser `fetch('/api/config', {credentials:'include'})` | `200`, **anonymous block only** (`status,name,version,default_locale,oauth,features`; 7 feature keys) |
| browser `fetch('/api/v1/auths/', {credentials:'include'})` | `200` + **the logged-in user object** |
| loopback capture of the `/api/config` request as delivered to the app | `cookie: cf_clearance=…, yunohost.portal=eyJhbGci…` — **no Open WebUI session cookie** |
| ssowat permission for the app | `auth_header: "basic-with-password"`, `uris: ["<domain>"]` |

Same browser, same front door, same instant: `/api/v1/*` resolves the user, `/api/config` does not.

## Cause

`get_current_user` accepts three channels (`utils/auth.py:357-367`): Bearer, the
`token` cookie, then `request.state.token` — the fallback populated when a reverse
proxy or SSO front door injects credentials.

`/api/config` does not use it. It re-implements session resolution inline
(`main.py:2211-2223`), reading only the `Authorization` header and the `token`
cookie. Behind a proxy that authenticates by injected credentials, both are absent,
so `user` stays `None` and the handler skips its entire authenticated block
(`if user is not None`), which is where `features.enable_web_search` lives
(`main.py:2329`).

The frontend gates the control on precisely that key:

```js
// src/lib/components/chat/MessageInput.svelte:805-808
showWebSearchButton =
  selectedModelIds.length === webSearchCapableModels.length &&
  $config?.features?.enable_web_search &&
  ($_user.role === 'admin' || $_user?.permissions?.features?.web_search);
```

`undefined` is falsy, so the control can never render — regardless of
`web.search.enable`, the engine, or the model's `capabilities.web_search`
(verified `true` on the affected install).

## Fix

Delegate to the existing `get_optional_verified_user_from_request`
(`utils/auth.py:555`) so `/api/config` honours the same channels as the rest of
the API, degrading to anonymous rather than 401. See
`open-webui-api-config-optional-user.patch`.

## Tests

1. Anonymous `GET /api/config` → `features` has no `enable_web_search` (unchanged behaviour).
2. Authenticated via the shared helper's non-Bearer channels (cookie, `request.state`)
   → `features.enable_web_search` present and equal to `web.search.enable`.
3. Invalid Bearer still yields `401`, so no silent privilege change.

## Notes

- `apps/open-webui` style packages declaring `sso = false` + `ldap = true` hit this
  whenever the domain is ssowat-protected, because YunoHost forwards identity as
  HTTP Basic (`basic-with-password`) and Open WebUI has no Basic support in
  `utils/auth.py`.
- Every other endpoint already works under that proxy, which is why the app is fully
  usable while web search is silently impossible.
