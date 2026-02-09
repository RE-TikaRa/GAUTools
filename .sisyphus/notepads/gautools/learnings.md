Convention: credentials resolve in order prompt -> env -> config.

- oldversion/gsau_schedule.py flow: GET jwgl entry -> extract pwdEncryptSalt/execution -> POST CAS login -> follow JS redirects -> GET /jsxsd/xskb/xskb_list.do (no term params); session cookies handled by requests.Session.
- Current CLI command routing: cli.py handlers create GSAUClient then call gautools.schedule.get_schedule (/jwglxt/kbcx/xskbcx_cxXsgrkb.html) and gautools.grades.get_grades (/jwglxt/cjcx/cjcx_cxDgXscj.html) / get_grade_detail (/jwglxt/cjcx/cjcx_cxCjxq.html).
- README claims CLI planned but cli.py exists; docs are out of sync.
- HTTPX: Client persists cookies; use follow_redirects=True to follow; see https://www.python-httpx.org/advanced/clients/ and quickstart cookies/redirection sections.
- Requests: Session persists cookies; allow_redirects controls; see https://docs.python-requests.org/en/latest/user/advanced/#session-objects and quickstart cookies/redirection sections.

- Added pycryptodome to requirements.txt to support Crypto.Cipher AES imports.

- Schedule parsing now targets `/jsxsd/xskb/xskb_list.do` with `xnxq01id` built as `year-term` (unless year already includes term suffix); term options come from the schedule page select `xnxq01id`.

- Grades now use old-system `/jsxsd/kscj/cjcx_list` with `kksj` as `year-term`, parsing HTML rows into `Grade` objects; detail uses `/jsxsd/kscj/pscj_list.do` and maps header/value pairs into breakdown.

- Grade tests now validate HTML table parsing, including `openWindow('/jsxsd/kscj/pscj_list.do?...')` extraction into `detail_url`.
- Grade detail breakdown parsing now prefers tables with a header row and a data row, mapping headers to the next row values; falls back to pairwise header/value parsing.
