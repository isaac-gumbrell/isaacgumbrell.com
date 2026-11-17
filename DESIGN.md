---
name: Isaac Gumbrell
description: Energy economist and market modeller; a professional home drawn as a merit order on chart paper.
colors:
  paper: "#f7f8f6"
  ink: "#15191b"
  ink-2: "#4a5357"
  rule: "#c9cfcc"
  rule-soft: "#e2e6e3"
  step: "#1f5a57"
  step-ink: "#f7f8f6"
  action: "#c2410c"
  action-hover: "#9a3412"
  action-ink: "#ffffff"
typography:
  display:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "clamp(2.2rem, 4.2vw, 3.6rem)"
    fontWeight: 680
    lineHeight: 1.02
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 82"
  headline:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "clamp(2rem, 4vw, 3rem)"
    fontWeight: 650
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 88"
  headline-section:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "clamp(1.5rem, 2.4vw, 2rem)"
    fontWeight: 650
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 88"
  title:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 600
    lineHeight: 1.35
    fontVariation: "'wdth' 92"
  body:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  lede:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    fontFeature: "'tnum' 1"
  button:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "1.02rem"
    fontWeight: 600
    fontVariation: "'wdth' 92"
  chart-label:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "16px"
    fontWeight: 560
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 85"
rounded:
  none: "0"
  sm: "2px"
spacing:
  row: "0.85rem"
  list-row: "0.7rem"
  gutter: "3rem"
  section: "5.5rem"
  section-narrow: "3.75rem"
components:
  button-action:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "0.65rem 1.3rem"
    height: "2.9rem"
  button-action-hover:
    backgroundColor: "{colors.action-hover}"
    textColor: "{colors.action-ink}"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "0.65rem 1.3rem"
    height: "2.9rem"
  button-line-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  chip-filter:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.3rem 0.8rem"
  chip-filter-pressed:
    backgroundColor: "{colors.step}"
    textColor: "{colors.step-ink}"
  tag-modelling:
    backgroundColor: "{colors.step}"
    textColor: "{colors.step-ink}"
    rounded: "{rounded.sm}"
    padding: "0 0.45rem"
  tag-qualitative:
    backgroundColor: "transparent"
    textColor: "{colors.step}"
    rounded: "{rounded.sm}"
    padding: "0 0.45rem"
  badge-category:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.05rem 0.5rem"
  status-new:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "0.05rem 0.45rem"
---

# Design System: Isaac Gumbrell

## Overview

**Creative North Star: "The Merit Order"**

The site is drawn on cool white chart paper. Isaac's work stacks as supply steps on an ink axis, filled solid where he built the model and hatched where he did the research, review and report drafting; new questions are the orange demand curve that clears on the last, empty step: what comes next. Everything else on the site inherits that chart: ink rules, hairline gridlines, one deep-teal fill, and a single signal orange that only appears where something can be done or is due.

Two type voices carry the two halves of the work. Archivo, at condensed widths with tabular figures, is the quantitative voice: headings, axes, labels, numbers, navigation, buttons and metadata. Source Serif 4 is the qualitative voice: prose, ledes and summaries. Density is that of a well-set report: ruled ledgers, generous section spacing, measured line lengths. The surface is flat; depth comes from overlap and line weight, never from shadow.

The world refuses the consultant default of headshot beside a headline over three service cards. The portrait sits in a ruled rectangular frame, like a figure plate, not a soft avatar.

**Key Characteristics:**

- Cool white chart paper, ink axes, hairline gridlines.
- One teal for modelling fills and links; diagonal hatch for qualitative work.
- Signal orange spent only on actions, the demand curve and things that are due.
- Archivo (condensed, tabular) for the quantitative voice; Source Serif 4 for prose.
- Flat: no shadows, 2px corners, depth by overlap and stroke weight.
- Ruled 2px ink tops open every major section.

## Colors

A cool, near-neutral chart-paper palette with one working teal and one scarce signal orange.

### Primary

- **Plant Teal** (`step`): fills modelling steps, colours links, the pressed filter chip, the Modelling tag, text selection and the qualitative hatch stroke. It is the colour of the work itself.

### Secondary

- **Signal Orange** (`action`): the Email button, the demand curve and clearing point, deadlines closing within seven days, the "Submissions open" tag and filter, the focus ring, the text caret, and the hover state of links and buttons. **Burnt Signal** (`action-hover`) is its pressed and hovered fill. **Action Ink** (`action-ink`) is the white text on it.

### Neutral

- **Chart Paper** (`paper`): page and navbar background. A cool white, deliberately not cream.
- **Axis Ink** (`ink`): text, chart axes, step edges, the ruled section tops, the portrait frame, the outline button and the "New" status chip. Also the inverted fill of the outline button on hover.
- **Pencil Grey** (`ink-2`): secondary text: ledes, metadata, years, axis labels, placeholders.
- **Rule** (`rule`): navbar bottom border, category badge and topic tag borders, the chart footer rule, scrollbar thumb.
- **Hairline** (`rule-soft`): chart gridlines and the row dividers in ledgers, lists and the feed.
- **Step Ink** (`step-ink`): text on teal; equals Chart Paper.

Dark tokens are defined under `html[data-theme="dark"]` (paper `#101415`, ink `#e8ecea`, step `#5fb3ac`, action `#ff7a3d`) but do not ship: `enable_darkmode: false` in `_config.yml`. Treat them as reserved, not as part of the visible system.

### Named Rules

**The Due-or-Doable Rule.** Orange appears only where the visitor can act or where something is due: the Email action, the demand curve and its clearing point, open submissions, deadlines inside seven days, and interaction states (hover, focus, caret). Never on decoration, headings or category labels.

**The Labels-Are-Not-Statuses Rule.** Category and region badges are neutral ink with a Rule border. Colour in the feed belongs to the status ramp alone.

## Typography

**Display Font:** Archivo (variable width 62–125%, weight 100–900; fallback Arial Narrow, sans-serif), self-hosted
**Body Font:** Source Serif 4 (optical size axis, roman and italic; fallback Georgia, serif), self-hosted
**Label Font:** Archivo, with tabular figures

**Character:** A condensed engineering grotesque that reads like chart annotation, paired with a bookish optical-size serif that reads like the report. Width, not weight, does most of the hierarchy work.

### Hierarchy

- **Display** (680, clamp(2.2rem, 4.2vw, 3.6rem), 1.02; width 82%, -0.025em): the home headline only, max 24ch.
- **Headline** (650, clamp(2rem, 4vw, 3rem); width 88%): page titles. Section heads step down to clamp(1.5rem, 2.4vw, 2rem); ruled ledger section heads to 1.5rem.
- **Title** (600, 1.1rem, 1.35; width 92%): project titles and feed item titles, max 70ch. High-importance feed items go to 700.
- **Body** (Source Serif 4, 400, 1.0625rem, 1.6): prose, max 70ch. Ledes run 1.15rem / 1.55 in Pencil Grey, max 58–65ch.
- **Label** (Archivo, 0.8–0.95rem, tabular figures): metadata, dates, badges, chips, legend, role lines. Sentence case; no tracking.
- **Chart label** (Archivo 560, 16px, width 85%; years 15px at 420 in Pencil Grey): axis labels under each step. The narrow chart uses 14px / 12.5px.

### Named Rules

**The Two Voices Rule.** Numbers, structure and anything you would find on a chart axis are Archivo; anything you would find in the written report is Source Serif 4. Do not set prose in Archivo or labels in the serif.

**The Tabular Figures Rule.** Years, dates, times, tables and the feed status line use tabular figures so columns of numbers align.

## Layout

A single reading column inside the theme container. The home hero splits 8fr / 4fr (headline and actions left, a 13.6rem portrait right, bottom-aligned, 3rem gap) above a full-width merit-order chart (SVG viewBox 1200 wide, about 300px tall). The Tools band splits 7fr / 5fr. Sections sit 5.5rem apart (3.75rem under 768px).

Lists are ledgers: a fixed left column for the year or language (5.5rem; 7.5rem on Projects and Repositories) and a flexible right column, rows separated by Hairline rules with 0.85rem vertical padding. Under 576px the year column stacks above the entry.

Under 768px the hero collapses to one column with a 7.2rem portrait moved above the headline, and the wide chart is replaced by the same stack turned on its side (`.mo-rows`): steps become rows whose thickness is years and whose length is price, with the demand curve falling from the upper right.

## Elevation & Depth

Flat. There are no shadows in the world; the theme's navbar, portrait image and hero shadows are explicitly removed. Depth is conveyed by overlap (the hatch over the teal fill, the demand curve crossing the stack), by stroke weight (axis 1.5px, step edges 1px rising to 3px on hover or focus, ruled section tops 2px), and by the thin ink frame with 6px inset around the portrait.

### Named Rules

**The Line-Weight Rule.** To lift something, thicken its line or overlap it; never cast a shadow.

## Shapes

Corners are nearly square: 2px on buttons, the Market Watch nav button, chips, tags, badges and the status chip; 0 on the portrait and on every chart step. Borders are 1px solid in Ink, Rule or Teal; section tops are 2px solid Ink. The one dashed form is the empty "What's next?" step at the end of the chart (1.5px Ink Secondary, dash 6/5). Qualitative work is drawn as a 45° hatch on a 9px pitch.

### Named Rules

**The Three Fills Rule.** Solid teal = modelling; solid teal with a paper hatch over it = modelling and qualitative; teal hatch on paper = qualitative only. The vocabulary is the same in the chart, the legend and the Projects tags, and it means nothing else.

**The What's-Next Dash Rule.** A dashed ink outline marks only the empty last step of the merit order: work not yet done. It is not a call to action and carries no orange.

## Components

### Buttons

Plain, squared and decisive; there are two and only two.

- **Shape:** nearly square (2px), min height 2.9rem, padding 0.65rem 1.3rem, Archivo 600 at 92% width.
- **Action:** Signal Orange fill, white text, matching 1px border. Used for Email Isaac (hero, contact, Projects CV request).
- **Line:** transparent with a 1px Ink border and Ink text; hover inverts to Ink fill with Paper text. Used for the secondary route (Open Market Watch).
- **Hover / Focus:** 160ms ease-out colour transitions; Action darkens to Burnt Signal. Focus is a 2px Signal Orange outline offset 3px (global).

### Chips (Market Watch filters)

- **Style:** transparent, 1px Hairline border, 2px corners, Archivo 0.85rem, padding 0.3rem 0.8rem.
- **State:** hover turns the border Teal; pressed (`aria-pressed="true"`) fills Teal with Paper text.

### Tags and badges

- **Role tags (Projects):** Modelling is a solid Teal tag with Paper text; Qualitative is a Teal-outlined tag carrying a small hatch swatch. 2px corners, 0.85rem.
- **Category badge (feed):** 1px Rule border, Ink text, Archivo 560. Region is the same label without a border at 650.
- **Topic tags (feed):** one to four per entry under the explanation (Generation, Storage, Gas, Market rules…); 1px Rule border, Ink Secondary Archivo 0.82rem, hover to an Ink border. Each tag is a button that sets the topic filter.
- **Submissions open (feed):** the one orange tag, Signal Orange border and text at 600, shown while a consultation's closing date is ahead or unstated. It sets the matching "Submissions open" filter chip, which fills Signal Orange when pressed.
- **Dates (feed):** the publish date taken from the source when one exists; otherwise "Updated …" from the page's last-modified date; "Added …" only when the source states neither.

### Feed status ramp

One ramp for every feed state: **New** is a filled Ink chip (Paper text, 600, shown for items first seen within ~36 hours); **open** is the default meta line; **closing soon** (deadline within seven days) turns the deadline Signal Orange at 600; **closed** strikes the deadline through. The ramp runs in that order and adds no other colours.

### Ledgers

The list form for writing, projects, repositories and the home Tools lists: year or language in a fixed Archivo column, title in Archivo 560–600 Ink, metadata in Pencil Grey, Hairline row rules. Titles hover to Signal Orange with an underline. A targeted project row (linked from its chart step) gets an 8% Teal wash.

### Ruled sections

Major blocks (Tools columns, Projects and Repositories sections, the feed status line) open with a 2px solid Ink rule and 0.75–1rem of space above the heading. No cards, no boxes.

### Inputs / Fields

- **Style:** the feed search and region select take Paper background, Ink text and a Hairline border on the theme's form control.
- **Focus:** the global 2px Signal Orange outline.

### Navigation

Paper navbar with a 1px Rule bottom border and no shadow. The wordmark is Archivo 650 at 88% width, 1.15rem, Ink. Links are Archivo 0.98rem Ink; the active page turns Teal at 600. Market Watch is the one tool with its own navbar button: 1px Ink border, 2px corners, Archivo 600; it fills Ink with Paper text on hover and while any Market Watch page is open. Inside Market Watch, two tabs (Updates, Consultations & opportunities) switch views, the current tab underlined 2px Ink.

### The Merit-Order Chart (signature)

Projects stack left to right in date order on an Ink axis over four Hairline gridlines; step width is years on the project, and the steps share about 190 units of rise, so each rises 190 ÷ the number of projects (21 units at nine). Each step is labelled underneath with the job (one or two short lines from `chart_label`), then its years; the client appears in the readout, not on the axis. Fills follow the Three Fills Rule; every step has a 1px Ink edge that thickens to 3px on hover or active, and to a 3px Signal Orange edge on keyboard focus. The final step is an empty dashed Ink Secondary outline labelled "What's next?"; it is not a link. The orange demand curve (2.5px, round caps) falls from "New questions" at the upper left and clears at an orange point on that step. A live readout under the chart names the project, client, years and roles of the hovered or focused step, beside a three-row legend. With motion allowed, steps rise from the axis (900ms, cubic-bezier(0.16, 1, 0.3, 1), staggered 70ms), then the curve draws (700ms) and its label and point fade in.

## Do's and Don'ts

### Do:

- **Do** spend Signal Orange only on actions, the demand curve and clearing point, open submissions, deadlines inside seven days, and interaction states.
- **Do** encode modelling and qualitative work with the three fills (solid, solid with paper hatch, hatch) wherever roles are shown.
- **Do** open major sections with a 2px Ink rule and list content as ledgers with Hairline row dividers.
- **Do** set numbers, labels, navigation and headings in Archivo at condensed widths (82–92%) with tabular figures, and prose in Source Serif 4.
- **Do** keep corners at 2px on controls and 0 on images and chart steps.
- **Do** express emphasis through line weight and overlap: 1px edges, 2px section rules, 3px on hover or focus.
- **Do** gate chart motion behind `prefers-reduced-motion: no-preference`.

### Don't:

- **Don't** cast shadows on any surface, including cards, the navbar, dropdowns or images.
- **Don't** use Signal Orange for headings, category badges, decoration or anything the visitor cannot act on.
- **Don't** use cream or warm off-white paper; the paper is cool white (`paper`).
- **Don't** add a second accent hue or colour feed categories; colour belongs to the status ramp.
- **Don't** use a dashed outline for anything other than the empty "What's next?" step, and never present it as a sales prompt.
- **Don't** add uppercase tracked kickers or eyebrows above headings; headings stand on their ruled tops.
- **Don't** fall back to the headshot beside a headline over three service cards.
