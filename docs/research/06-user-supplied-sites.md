# Sites suggested by the owner

## youtubetotranscript.com
- Paste a YouTube link, get the transcript. No login, no stated length or count limits.
- URL pattern: `/transcript?v=VIDEO_ID&current_language_code=en`. It is a web page, not a documented API.
- Shows the transcript beside an embedded player; can switch language and translate (claims 125+ languages). Arabic is not mentioned explicitly.
- No download option (planned). Copy-to-clipboard only.
- Paid programmatic access is sold separately at transcriptapi.com, and they also link an MCP offering. Pricing and endpoints are not public on the page.

**Use in real-eyes:** an optional late-ladder fallback for YouTube only (scraping a third-party page is fragile and may break at any time). Not a core dependency. Worth checking whether its output is plain server-rendered HTML.
