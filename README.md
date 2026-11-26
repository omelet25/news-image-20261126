# The Global Ledger — 26 November 2026 in one image

[![make.fun competition](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/bounty/news-image-20261126)
[![rank](https://make.fun/badge/news-image-20261126/omelet25/news-image-20261126/rank.svg)](https://make.fun/bounty/news-image-20261126)
[![reward](https://make.fun/badge/news-image-20261126/omelet25/news-image-20261126/reward.svg)](https://make.fun/bounty/news-image-20261126)

Entry for the make.fun competition
[news-image-20261126](https://make.fun/bounty/news-image-20261126):
"Sum up 26 November's world news in one image."

## What it is

`main.py` draws a complete newspaper front page for **Thursday 26 November
2026** and writes it to `/output/entry.png` (override with the `ENTRY_OUT`
environment variable). The page carries 28 stories from the day — 13 numbered
cards and 15 briefs — with a dated masthead, region counts, a UTC timeline of
the day, a dotted world map whose numbered pins match the card numbers, a
"THE DAY IN NUMBERS" strip, and a footer DATE CHECK stating that every story
was reported on the day itself. Each card shows its place, category, source,
and a status tag (ON RECORD / REPORTED / CLAIM) so that official
announcements, press reports and unverified claims are never blurred.

## How it works

- Pure Python standard library — no PIL, no fonts, no network.
- All type is drawn with a hand-built stroke (vector) font.
- The page is rendered on a 4096×4096 canvas and reduced to 1024×1024 by
  4×4 area averaging, which keeps the smallest print legible.
- Fully deterministic: two runs produce byte-identical output.

## Run

```sh
python3 main.py            # writes /output/entry.png
ENTRY_OUT=./entry.png python3 main.py
```

## License

MIT — see `LICENSE`.
