# Energy feed (Market Watch)

Feeds the two Market Watch pages:

- `/market-watch/updates/` lists everything.
- `/market-watch/opportunities/` lists open consultations, tenders and events.

The pages render `_data/energy_feed.json`. `update_feed.py` refreshes that file.

## How it works

1. **Collect**: fetches the direct sources in `config.yml`: official RSS feeds (AEMC, ARENA, energy.gov.au, Beehive, and the AusTender and GETS tender portals, filtered to energy by keyword), plus listing pages (EPWA, ERA, AER, DCCEEW, the NZ Electricity Authority, Transpower and the Commerce Commission). Feeds marked `keeper: true` were checked for quality in November 2026.

   AEMO and ASL (AEMO Services) refuse plain HTTP behind Cloudflare, so hosts in `settings.browser_hosts` are rendered in headless Chromium (Playwright). The browser is not disguised: it sends the same identifying user agent, `robots.txt` allows these pages, and loads are spaced 2 seconds apart and capped at 40 per run. If a site serves a challenge anyway (more likely from a GitHub Actions data-centre address than from a home connection), that source fails softly and the AEMO research beat still covers it. MBIE and the Beehive portfolio pages (Imperva) block the browser too and are left to the research beat and the Beehive site-wide feed.
2. **Triage**: the AI model classifies and summarises new links and finds closing dates. It drops anything not about energy.
3. **Research**: the model runs web search and web fetch for each research beat: AEMO (which blocks scripted requests), WA politics, federal policy, tenders and events, plus two New Zealand beats (regulators and government; tenders and events).
4. **Merge**: dedupes by URL and title, keeps `first_seen`, and drops items older than 180 days unless a deadline is still ahead.

`state.json` remembers links the model rejected, so they aren't triaged again.

## Credentials

The script uses `ANTHROPIC_API_KEY` if it is set. Otherwise it uses `OPENROUTER_API_KEY` through OpenRouter's Anthropic-compatible endpoint.

- **Locally**: put the key in `.env` (see `.env.example`). `.env` is gitignored, excluded from Docker and Jekyll, and should be `chmod 600`.
- **GitHub Actions**: go to **Settings → Secrets and variables → Actions** and add a repository **secret** named `OPENROUTER_API_KEY`. Never put the key in a workflow file or commit it.
- **Optional repository variables**:
  - `ENERGY_FEED_MODEL` (default `~deepseek/deepseek-flash-latest` on OpenRouter, `claude-opus-5-5` direct). On OpenRouter, non-Anthropic models get OpenRouter's own web search and fetch tools.

### Cost

Each run logs its cost per step (`cost: $… total (triage $…, aemo $…, …)`), as reported by OpenRouter. With DeepSeek Flash almost all of it is web-search fees, roughly US$0.0075 per search, so `search_uses_per_beat` in `config.yml` is the main dial. At 4 searches per beat, 7 beats and two runs a day, expect around US$0.30 per run, or about $18 a month. The same setup on Claude Opus 5.5 measured about $5.50 per run.

Researched items are checked before they are published: links that return 404 or point at a host that does not exist are dropped (this guards against a model guessing a URL), as are items whose deadline or event date has already passed. Near-identical headlines are merged.
  - `ENERGY_FEED_EFFORT`: `low`, `medium` (default) or `high`.

With no key the script still runs in "direct-only" mode. It publishes direct-source links unsummarised, and the model triages them once a key is available.

## Running

```bash
pip install -r scripts/energy_feed/requirements.txt
python scripts/energy_feed/update_feed.py                 # full run
python scripts/energy_feed/update_feed.py --no-llm        # no API calls
python scripts/energy_feed/update_feed.py --only aemo --skip-triage   # one research beat
```

Each run ends with a `usage:` log line (tokens, searches and fetches), so you can check what a run costs.

## Schedule

`.github/workflows/energy-feed.yml` runs at 06:00 and 18:00 Perth time. You can also run it by hand from the Actions tab. It commits the refreshed JSON and then triggers `deploy.yml`.

## Moving to a home server

Run the same script from cron, then push. A push made with your own credentials triggers the normal deploy workflow:

```cron
0 6,18 * * * cd /path/to/isaacgumbrell.com && git pull -q && .venv/bin/python scripts/energy_feed/update_feed.py && git add _data/energy_feed.json scripts/energy_feed/state.json && git commit -qm "Update energy feed" && git push -q
```

Then disable the `schedule:` trigger in `energy-feed.yml`.
