After installation, wait some minutes for the app to complete startup. 
The first user to login will be granted admin rights.

## Web search (optional, off by default)

The search (magnifier) button in the chat input only appears when web search is
enabled *and* the engine actually answers — three things must line up:

1. **SearXNG: enable the JSON response format.** Open WebUI always calls
   `?format=json`; if `search.formats` is not enabled in SearXNG's `settings.yml`
   the call fails with 403:
   ```yaml
   search:
     formats:
       - html
       - json
   ```
   then `systemctl restart searxng`.
2. **Open WebUI: enable it as admin.** Open the chat settings (gear icon in the
   chat input) → **Tools** tab → enable *Web Search*, pick *Searxng* as *Web Search
   Engine*, and set *Searxng Query URL* to the instance's **loopback** endpoint,
   e.g. `http://127.0.0.1:8888/search` (find the port with
   `sudo ss -ltnp | grep searxng`). Prefer loopback over the public URL when
   SearXNG sits behind YunoHost SSO: Open WebUI calls it anonymously and would
   only ever get the SSO login page back.
3. **Per model:** the magnifier toggle in the chat bar is per model — turn it on
   for the model you are chatting with.

## Web search: SSO must not front the app (verified fix)

`manifest.toml` declares `sso = false`. YunoHost still applies ssowat at **server
level** in `/etc/nginx/conf.d/<domain>.conf`, and forwards identity as HTTP Basic
(`auth_header: basic-with-password`), which Open WebUI does not consume. Consequence:
`/api/config` is answered without the app's own session being recognised, so it omits
its authenticated block - the block containing `features.enable_web_search` - and the
chat input can never render the web search control, no matter how it is configured.

`conf/nginx.conf` now clears the inherited access phase for the app's location
(`access_by_lua_block { }`). On an existing install the already-rendered file must be
updated by hand once, or it will be flagged as manually modified and reverted by
`yunohost tools regen-conf open-webui`:

    sudo cp /etc/nginx/conf.d/<domain>.d/open-webui.conf /root/open-webui.nginx.bak
    sudoeditor /etc/nginx/conf.d/<domain>.d/open-webui.conf   # add: access_by_lua_block { }
    sudo nginx -t && sudo systemctl reload nginx

Rollback: `sudo cp /root/open-webui.nginx.bak <same path> && sudo systemctl reload nginx`.

After the reload, the app is gated **only** by its own login (local or LDAP) plus
Cloudflare if proxied. There is no supported YunoHost 12 CLI to unprotect a single
URL: `user permission update` has no `--protected`/`--url`, `domain ssowat` does not
exist, and `regen-conf ssowat` has no such category.

Verify:

    curl -sk -o /dev/null -w "%{http_code}\n" https://<domain>/api/config   # 200, not 302

Then in a logged-in tab: `fetch('/api/config',{credentials:'include'}).then(r=>r.json())`
must show `features.enable_web_search: true`. The toggle itself is per model, under the
chat `+` menu -> **Integrations** -> Web Search.

Do **not** set `WEBUI_AUTH_TRUSTED_EMAIL_HEADER` as a workaround: ssowat forwards Basic
rather than a username header, and the setting turns Open WebUI away from its own login
form, locking everyone out of a working instance.
