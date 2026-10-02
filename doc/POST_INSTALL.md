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
