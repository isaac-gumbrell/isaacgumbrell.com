# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, weighted equally:

- **Prospective clients and employers in the energy industry** (market operators, regulators, generators, retailers, consultancies) who are evaluating Isaac for energy market modelling or economics work. Their job: decide quickly whether he is credible and relevant, then get in touch.
- **Energy professionals, including Isaac himself,** who use the site's tools as part of their working week. Their job: see what has changed in Australian and New Zealand energy markets (announcements, rule changes, consultations, tenders, events) and find the tools Isaac builds and maintains.

## Product Purpose

isaacgumbrell.com is Isaac Gumbrell's professional home. It introduces him as an energy economist and market modelling specialist, and it hosts working tools he uses himself. Success means two things: clients and employers make contact, and peers come back to the tools regularly. The tools are the credibility; the hero is the introduction.

## Positioning

Quantitative modelling combined with qualitative work. Isaac's projects pair model design and execution with research, review and report drafting: five of the seven listed projects include qualitative work and four combine it with modelling (for example, the BRCP Review: "Modelling design and execution, report drafting"; the IESO data review: "Research, report drafting"). The site must present him as someone who builds the model *and* writes the advice, never as a modeller alone (confirmed by Isaac).

It is also a modeller's site that runs on its own tools. Market Watch is a real, automatically refreshed tracker of Australian and New Zealand energy announcements (AEMO, Energy Policy WA, AEMC, AER, ERA, ARENA, the NZ Electricity Authority, Transpower, government), with a focus on Western Australia, the NEM and the NZ electricity market. The open-source repositories are tools he authors or contributes to (scenario_framework_manager, ASSUME). A generic consultant page cannot copy this, because the evidence is live and in daily use.

## Operating Context

- Hosted on GitHub Pages; built with Jekyll (al-folio theme, Bootstrap 4) through GitHub Actions.
- Market Watch data (`_data/energy_feed.json`) refreshes every 12 hours via `.github/workflows/energy-feed.yml`; pages must read well whether the feed holds AI summaries or bare direct-source links.
- Contact happens by email (`isaacgumbrell+inquiries@gmail.com`), LinkedIn and GitHub. There is no form or booking system.
- The theme's dark-mode toggle is currently off (`enable_darkmode: false` in `_config.yml`), so visitors see the light theme. Dark tokens exist in `_sass/_world.scss` in case it is switched on.

## Capabilities and Constraints

- Pages: home (hero), Market Watch (landing, Market Updates, Consultations & Opportunities), Projects, Repositories, 404.
- Featured tools for now: Market Watch and the open-source repositories, presented as tools rather than a plain repo list. Further in-browser tools may be added later; none are committed yet.
- Static site only: no server-side code at request time; client-side JavaScript is allowed.
- External scripts and stylesheets load through the theme's `_config.yml` third-party library list; purgecss strips unused CSS after the build.

## Brand Commitments

- Keep the portrait photo (`assets/img/portrait_pic.jpg`) in the hero.
- No other wording, titles, colours or assets are binding; copy may be rewritten as long as it stays factual.

## Evidence on Hand

- Portrait: `assets/img/portrait_pic.jpg`.
- Projects and writing: `_pages/projects.md` (Medium article 2024, Ethically Kate article 2021, client projects with roles and dates).
- Repositories: `_pages/repositories.md` (scenario_framework_manager, author and maintainer; ASSUME, contributor).
- Market Watch: live data in `_data/energy_feed.json`. Entries carry an explanation, topic tags, a submissions-open flag, and the publish date read from the source page.
- No testimonials, client logos, metrics or case-study results are on hand. Do not fabricate any.

## Product Principles

1. Show, don't claim: live tools and real project history carry the credibility, not adjectives.
2. Useful on every visit: someone returning for Market Watch should reach it in one click from the home page.
3. Australasian energy specificity (WA, the NEM and New Zealand) over generic "energy transition" language.
4. Contact is always one step away, but never pushy.
