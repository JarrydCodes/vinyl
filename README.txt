VINYL SITE
==========
1. Get a Discogs token: discogs.com/settings/developers -> Generate new token
2. In this folder run:
     export DISCOGS_TOKEN=your_token          (Windows: set DISCOGS_TOKEN=your_token)
     python3 build.py Jarrydvinyl
   First run takes a while (about 1 second per record, Discogs rate limit). Later runs only fetch new records.
3. The "site" folder is your website. Preview it with:  cd site && python3 -m http.server
   Host it free on GitHub Pages, Cloudflare Pages or Netlify (just upload the site folder).
4. nfc-links.csv lists the path for each record. On the tag, write the full URL:
     https://YOUR-SITE-ADDRESS/record.html?id=RELEASE_ID
   (use an NFC app such as NFC Tools, "Write" -> "Add a record" -> "URL/URI")

CUSTOMISING
- Page title: edit SITE_TITLE in templates/index.html
- Look and feel: templates/style.css (colours are at the top)
- Your own notes per record: extras.json, keyed by Discogs release ID. Supported fields:
  note, condition, bought, links (list of {label, url})
- Re-run build.py after any change.
