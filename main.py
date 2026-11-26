#!/usr/bin/env python3
"""Render one newspaper front page summarising the world news of
Thursday 26 November 2026 as a single 1024x1024 PNG.

Pure standard library.  The page is drawn on a 4096x4096 canvas with a
hand-built stroke (vector) font and then reduced to 1024x1024 by 4x4
area averaging, which keeps the small type readable.  Output is fully
deterministic: no clock, no randomness, no dict-order dependence.
"""

import os
import struct
import zlib

SS = 4                      # supersampling factor
W = H = 1024                # final image size
IW = IH = W * SS            # internal canvas size

PAPER = (248, 244, 233)     # warm newsprint
INK = (26, 22, 17)          # near-black ink
SOFT = (58, 52, 44)         # dark warm grey for small print
RED = (176, 30, 22)         # kicker red
RULE = (26, 22, 17)
TAG_ON_RECORD = (30, 82, 56)
TAG_REPORTED = (36, 72, 108)
TAG_CLAIM = (148, 50, 24)
CREAM = (250, 246, 236)

FB = bytearray(IW * IH * 3)


def _set(ix, iy, color):
    if 0 <= ix < IW and 0 <= iy < IH:
        o = (iy * IW + ix) * 3
        FB[o] = color[0]
        FB[o + 1] = color[1]
        FB[o + 2] = color[2]


def fill_all(color):
    FB[:] = bytes(color) * (IW * IH)


def fill_rect(x, y, w, h, color):
    """Filled rectangle; coordinates are in final-image units."""
    x0 = int(round(x * SS))
    y0 = int(round(y * SS))
    x1 = int(round((x + w) * SS))
    y1 = int(round((y + h) * SS))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    n = len(row)
    for iy in range(max(0, y0), min(IH, y1)):
        o = (iy * IW + x0) * 3
        FB[o:o + n] = row


def fill_circle(cx, cy, r, color):
    """Filled circle; centre and radius in final-image units."""
    icx = cx * SS
    icy = cy * SS
    ir = r * SS
    y0 = int(icy - ir)
    y1 = int(icy + ir)
    r2 = ir * ir
    for iy in range(max(0, y0), min(IH, y1 + 1)):
        dy = iy + 0.5 - icy
        dx = max(0.0, r2 - dy * dy) ** 0.5
        xa = int(icx - dx)
        xb = int(icx + dx)
        if xb < 0 or xa >= IW:
            continue
        xa = max(0, xa)
        xb = min(IW - 1, xb)
        row = bytes(color) * (xb - xa + 1)
        o = (iy * IW + xa) * 3
        FB[o:o + len(row)] = row


def stroke_line(x1, y1, x2, y2, width, color):
    """Thick line: filled circles stamped along the segment."""
    steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) * SS / max(1.0, width * SS * 0.35)))
    r = width / 2.0
    for i in range(steps + 1):
        t = i / steps
        fill_circle(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r, color)


def stroke_polyline(points, width, color):
    for a, b in zip(points, points[1:]):
        stroke_line(a[0], a[1], b[0], b[1], width, color)
    if len(points) == 1:
        fill_circle(points[0][0], points[0][1], width / 2.0, color)


def hline(x, y, w, width, color=INK):
    fill_rect(x, y - width / 2.0, w, width, color)


def vline(x, y, h, width, color=INK):
    fill_rect(x - width / 2.0, y, width, h, color)


# --------------------------------------------------------------------------
# Stroke font.  Each glyph is a list of strokes; each stroke is a list of
# (x, y) points on a 5-wide, 7-tall grid (y grows downwards, 0 = cap top,
# 7 = baseline).  Lowercase letters are rendered as small capitals.
# --------------------------------------------------------------------------

GLYPHS = {
    'A': [[(0, 7), (2.5, 0), (5, 7)], [(1.25, 4.4), (3.75, 4.4)]],
    'B': [[(0, 0), (0, 7)], [(0, 0), (3.1, 0), (4.4, 1), (4.4, 2.5), (3.1, 3.4), (0, 3.4)],
          [(0, 3.4), (3.5, 3.4), (4.7, 4.4), (4.7, 6), (3.5, 7), (0, 7)]],
    'C': [[(4.7, 1.3), (3.4, 0.2), (1.6, 0.2), (0.4, 1.3), (0.4, 5.7), (1.6, 6.8), (3.4, 6.8), (4.7, 5.7)]],
    'D': [[(0, 0), (0, 7)], [(0, 0), (2.9, 0), (4.7, 1.8), (4.7, 5.2), (2.9, 7), (0, 7)]],
    'E': [[(4.6, 0), (0, 0), (0, 7), (4.6, 7)], [(0, 3.5), (3.7, 3.5)]],
    'F': [[(4.6, 0), (0, 0), (0, 7)], [(0, 3.5), (3.5, 3.5)]],
    'G': [[(4.7, 1.3), (3.4, 0.2), (1.6, 0.2), (0.4, 1.3), (0.4, 5.7), (1.6, 6.8), (3.4, 6.8),
           (4.8, 5.6), (4.8, 3.9), (3.1, 3.9)]],
    'H': [[(0, 0), (0, 7)], [(5, 0), (5, 7)], [(0, 3.5), (5, 3.5)]],
    'I': [[(2.5, 0), (2.5, 7)], [(1.1, 0), (3.9, 0)], [(1.1, 7), (3.9, 7)]],
    'J': [[(4.6, 0), (4.6, 5.5), (3.4, 6.8), (1.5, 6.8), (0.4, 5.7)]],
    'K': [[(0, 0), (0, 7)], [(4.8, 0), (0.5, 3.5)], [(1.4, 2.5), (5, 7)]],
    'L': [[(0, 0), (0, 7), (4.6, 7)]],
    'M': [[(0, 7), (0, 0), (2.5, 3.1), (5, 0), (5, 7)]],
    'N': [[(0, 7), (0, 0), (5, 7), (5, 0)]],
    'O': [[(1.6, 0.2), (3.4, 0.2), (4.6, 1.4), (4.6, 5.6), (3.4, 6.8), (1.6, 6.8),
           (0.4, 5.6), (0.4, 1.4), (1.6, 0.2)]],
    'P': [[(0, 7), (0, 0), (3.3, 0), (4.6, 1.1), (4.6, 2.9), (3.3, 4), (0, 4)]],
    'Q': [[(1.6, 0.2), (3.4, 0.2), (4.6, 1.4), (4.6, 5.6), (3.4, 6.8), (1.6, 6.8),
           (0.4, 5.6), (0.4, 1.4), (1.6, 0.2)], [(3.1, 4.7), (5.1, 7.1)]],
    'R': [[(0, 7), (0, 0), (3.3, 0), (4.6, 1.1), (4.6, 2.9), (3.3, 4), (0, 4)],
          [(2.5, 4), (5, 7)]],
    'S': [[(4.6, 1.2), (3.4, 0.2), (1.5, 0.2), (0.5, 1.2), (0.9, 2.6), (4.1, 4.4),
           (4.6, 5.7), (3.5, 6.8), (1.4, 6.8), (0.4, 5.9)]],
    'T': [[(0.2, 0), (4.8, 0)], [(2.5, 0), (2.5, 7)]],
    'U': [[(0, 0), (0, 5.5), (1.4, 6.8), (3.6, 6.8), (5, 5.5), (5, 0)]],
    'V': [[(0, 0), (2.5, 7), (5, 0)]],
    'W': [[(0, 0), (1.2, 7), (2.5, 3.1), (3.8, 7), (5, 0)]],
    'X': [[(0, 0), (5, 7)], [(5, 0), (0, 7)]],
    'Y': [[(0, 0), (2.5, 3.1)], [(5, 0), (2.5, 3.1), (2.5, 7)]],
    'Z': [[(0.2, 0), (4.8, 0), (0.2, 7), (4.8, 7)]],
    '0': [[(1.5, 0.3), (3.5, 0.3), (4.4, 1.5), (4.4, 5.5), (3.5, 6.7), (1.5, 6.7),
           (0.6, 5.5), (0.6, 1.5), (1.5, 0.3)]],
    '1': [[(1.3, 1.3), (3, 0), (3, 7)], [(1.1, 7), (4.7, 7)]],
    '2': [[(0.6, 1.4), (1.6, 0.2), (3.4, 0.2), (4.4, 1.4), (4.2, 2.9), (0.4, 7), (4.8, 7)]],
    '3': [[(0.5, 1.2), (1.6, 0.2), (3.3, 0.2), (4.4, 1.3), (3.9, 2.8), (2.5, 3.4)],
          [(2.5, 3.4), (4, 3.7), (4.6, 4.9), (4.1, 6.4), (2.9, 7), (1.2, 6.9), (0.4, 6)]],
    '4': [[(3.4, 7), (3.4, 0), (0.2, 4.9), (4.9, 4.9)]],
    '5': [[(4.5, 0), (0.6, 0), (0.6, 3.2), (3.1, 3), (4.5, 4.3), (4.3, 6), (3.1, 7),
           (1.2, 6.8), (0.4, 5.9)]],
    '6': [[(4.4, 1.5), (3, 0.2), (1.4, 0.9), (0.5, 2.7), (0.5, 5.2), (1.6, 6.8), (3.4, 6.8),
           (4.6, 5.6), (4.5, 4.1), (3.4, 3.2), (1.7, 3.3), (0.5, 4.5)]],
    '7': [[(0.3, 0), (4.7, 0), (2.2, 7)]],
    '8': [[(1.8, 3.4), (0.8, 2.6), (0.9, 1.1), (2.1, 0.2), (3.5, 0.2), (4.4, 1.1), (4.3, 2.6),
           (3.2, 3.4), (4.3, 4.4), (4.4, 5.9), (3.5, 6.8), (1.6, 6.8), (0.6, 5.9), (0.7, 4.4),
           (1.8, 3.4)]],
    '9': [[(0.6, 5.5), (2, 6.8), (3.6, 6.1), (4.5, 4.3), (4.5, 1.8), (3.4, 0.2), (1.6, 0.2),
           (0.4, 1.4), (0.5, 3), (1.6, 3.9), (3.3, 3.8), (4.5, 2.7)]],
    '.': [[(2.5, 6.6)]],
    ',': [[(2.9, 5.2), (2.2, 7.1)]],
    ':': [[(2.5, 2.1)], [(2.5, 5.5)]],
    ';': [[(2.5, 2.1)], [(2.9, 5.2), (2.2, 7.1)]],
    "'": [[(2.6, 0.3), (2.1, 1.9)]],
    '"': [[(1.6, 0.3), (1.2, 1.9)], [(3.9, 0.3), (3.5, 1.9)]],
    '-': [[(1, 3.5), (4, 3.5)]],
    '=': [[(0.8, 2.6), (4.2, 2.6)], [(0.8, 4.4), (4.2, 4.4)]],
    '\u2014': [[(0.1, 3.5), (4.9, 3.5)]],
    '/': [[(0.8, 7), (4.4, 0)]],
    '(': [[(3.9, 0.4), (2.1, 1.6), (1.4, 3.5), (2.1, 5.4), (3.9, 6.6)]],
    ')': [[(1.1, 0.4), (2.9, 1.6), (3.6, 3.5), (2.9, 5.4), (1.1, 6.6)]],
    '%': [[(4.4, 0), (0.8, 7)],
          [(1.35, 0.75), (2.15, 1.05), (2.05, 2.05), (1.25, 2.3), (0.5, 2), (0.55, 1), (1.35, 0.75)],
          [(3.85, 4.7), (4.65, 5), (4.55, 6), (3.75, 6.25), (3, 5.95), (3.05, 4.95), (3.85, 4.7)]],
    '+': [[(2.5, 1.6), (2.5, 5.4)], [(0.6, 3.5), (4.4, 3.5)]],
    '$': [[(4.6, 1.2), (3.4, 0.2), (1.5, 0.2), (0.5, 1.2), (0.9, 2.6), (4.1, 4.4),
           (4.6, 5.7), (3.5, 6.8), (1.4, 6.8), (0.4, 5.9)], [(2.5, -0.4), (2.5, 7.4)]],
    '\u20ac': [[(4.7, 1.3), (3.3, 0.2), (1.6, 0.2), (0.5, 1.3), (0.4, 5.7), (1.6, 6.8),
                (3.3, 6.8), (4.7, 5.7)], [(0.1, 2.9), (3.3, 2.9)], [(0.1, 4.1), (3.3, 4.1)]],
    '&': [[(1.9, 3.1), (0.7, 1.7), (1.1, 0.4), (2.7, 0.3), (3.3, 1.5), (1.9, 3.1)],
          [(1.9, 3.1), (4.3, 6.9)], [(4.3, 6.9), (3.1, 5.5), (0.9, 4.4)]],
    '?': [[(0.6, 1.3), (1.7, 0.2), (3.4, 0.2), (4.4, 1.4), (4, 2.8), (2.5, 3.7), (2.5, 4.7)],
          [(2.5, 6.6)]],
    '!': [[(2.5, 0), (2.5, 4.7)], [(2.5, 6.6)]],
}


def text_width(s, size, bold=False):
    """Width of a string in final-image units."""
    scale = size / 7.0
    w = 0.0
    for ch in s:
        if ch == ' ':
            w += 3.4 * scale
        elif ch == '\u2022':
            w += 3.4 * scale
        else:
            w += 6.0 * scale
    return w


def draw_char(x, y, ch, size, color, bold):
    """Draw one glyph with its cap top at y; returns the advance width."""
    scale = size / 7.0
    if ch == ' ':
        return 3.4 * scale
    if ch == '\u2022':
        fill_circle(x + 1.7 * scale, y + 3.5 * scale, 1.05 * scale, color)
        return 3.4 * scale
    glyph = GLYPHS.get(ch)
    lower = False
    if glyph is None and 'a' <= ch <= 'z':
        glyph = GLYPHS.get(ch.upper())
        lower = True
    if glyph is None:
        glyph = GLYPHS['?']
    width = size * (0.155 if bold else 0.088)
    if lower:
        top = y + size * 0.26
        hscale = scale * 0.74
        for stroke in glyph:
            pts = [(x + px * scale, top + py * hscale) for px, py in stroke]
            stroke_polyline(pts, width, color)
    else:
        for stroke in glyph:
            pts = [(x + px * scale, y + py * scale) for px, py in stroke]
            stroke_polyline(pts, width, color)
    return 6.0 * scale


def draw_text(x, y, s, size, color=INK, bold=False, align='left'):
    """Draw a single line of text; y is the cap top.  Returns its width."""
    w = text_width(s, size, bold)
    if align == 'center':
        x -= w / 2.0
    elif align == 'right':
        x -= w
    cx = x
    for ch in s:
        cx += draw_char(cx, y, ch, size, color, bold)
    return w


def wrap_text(s, size, maxw, bold=False):
    """Greedy word wrap; returns a list of lines that fit maxw."""
    words = s.split(' ')
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, size, bold) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Page content.  All display copy was written for this page from the day's
# fact memo; every number matches the memo.  Status tags follow the memo:
# ON RECORD = official, REPORTED = press reports, CLAIM = a party's claim.
# --------------------------------------------------------------------------

# (number, place, category, status, source, headline, summary)
CARDS = [
    (1, 'WASHINGTON', 'TRADE', 'REPORTED', 'REUTERS',
     'US PROPOSES NEW TARIFFS ON 14 PARTNERS',
     'China, EU, Japan, India named; China +20 points over 25%. (Reuters)'),
    (3, 'KYIV', 'CONFLICT', 'REPORTED', 'REUTERS',
     'BALLISTIC MISSILES HIT KYIV; 7 WOUNDED',
     'Two grain ships hit near Odesa; cargo tops 100,000 tonnes. (Reuters)'),
    (5, 'GAZA', 'CONFLICT', 'REPORTED', 'MORNING BRIEFING',
     'AT LEAST NINE KILLED IN GAZA STRIKES AND GUNFIRE',
     'Overnight dead include a Hamas education deputy. (Morning Briefing)'),
    (8, 'DR CONGO', 'HEALTH', 'ON RECORD', 'REUTERS',
     'EBOLA CASES REACH 12,021 IN DR CONGO',
     'Deaths at 5,904; second-largest outbreak on record. (Reuters)'),
    (11, 'NEW YORK', 'SOCIETY', 'REPORTED', 'REUTERS',
     "MACY'S PARADE POSTPONED, A FIRST IN 100 YEARS",
     'Storm halts the centenary parade; 300,000 homes lose power. (Reuters)'),
    (2, 'RIYADH', 'SECURITY', 'CLAIM', 'ONE TURN',
     'HOUTHIS CLAIM STRIKES ON SAUDI OIL SITES',
     'Ports and the Ras Tanura refinery are claimed hit; Riyadh says a missile was destroyed. (One Turn)'),
    (7, 'BRUSSELS', 'EU POLITICS', 'ON RECORD', 'AP',
     'EU SUMMIT OPENS ON \u20ac1.582TN BUDGET PLAN',
     'The 2028-34 budget and a \u20ac45bn Ukraine loan, in a framework up to \u20ac100bn. All 27 must agree. (AP)'),
    (9, 'PYONGYANG', 'SECURITY', 'REPORTED', 'ECONOMIC TIMES',
     'KIM VOWS MORE NUCLEAR WEAPONS',
     'Pyongyang also shuts the Swiss diplomatic office; its envoy has 48 hours to leave. (Economic Times)'),
    (12, 'MARKETS', 'MARKETS + AI', 'ON RECORD', 'REUTERS',
     'S&P PUTS NVIDIA ON NEGATIVE WATCH',
     'Nvidia fell 3.9% to $149.30. Asia rebounded: Nikkei +1.6%, KOSPI +1.9%; Brent $94.81. (Reuters)'),
    (4, 'NIZHNY NOVGOROD', 'CONFLICT', 'CLAIM', 'ONE TURN',
     'KYIV SAYS 5 JETS HIT AT RUSSIAN AIRBASE',
     "Ukraine says its strike on the Savasleyka airbase hit five Russian military aircraft. (One Turn)"),
    (6, 'CAIRO', 'DISASTER', 'REPORTED', 'REUTERS',
     'TANKER FIRE KILLS AT LEAST 31 IN CAIRO',
     'A fuel tanker overturned and burned on the ring road; at least 31 dead, 21 hurt. (Reuters)'),
    (10, 'TIANGONG', 'SPACE', 'REPORTED', 'ONE TURN',
     'FIRST FOREIGN ASTRONAUT REACHES TIANGONG',
     "Pakistan's Muhammad Zeeshan Ali arrived on Shenzhou 24, a first for China's station. (One Turn)"),
    (13, 'UNITED STATES', 'TECHNOLOGY', 'REPORTED', 'THE EDITION',
     'FCC CLEARS ORBITAL DATA-CENTRE FLEET',
     'Regulators clear SpaceX Starmind: up to 1,000,000 satellites for orbital data centres. (The Edition)'),
]

# (number, place, text)
BRIEFS = [
    (14, 'SUDAN', 'RSF drone strike kills at least 19 in Blue Nile State.'),
    (15, 'INDONESIA', 'More than 20 trapped as an illegal gold mine floods.'),
    (16, 'MYANMAR', 'May not fully comply with ICJ orders in the genocide case.'),
    (17, 'SOUTH AFRICA', 'Court rules Ramaphosa impeachment report unlawful.'),
    (18, 'ROMANIA', 'Far-right leader Simion charged with incitement.'),
    (19, 'ITALY', 'Rome asks Berlin to act on Henkel closure, 102 jobs.'),
    (20, 'INDIA', 'Congress sues Meta and the government over blocked posts.'),
    (21, 'BANGLADESH', 'Garment wage protest in Dhaka; 3 arrested.'),
    (22, 'IOWA, US', 'Army destroys lead explosives; no spread found.'),
    (23, 'MIAMI, US', 'FedEx cargo jet overruns the runway at Miami airport.'),
    (24, 'US SOUTH COAST', 'Six die in aircraft crash off the coast.'),
    (25, 'NEW YORK STATE', 'AI chatbots may not pose as human to children.'),
    (26, 'EUROPE', 'Liverpool 3-0 Bruges; Lille 2-1 Bayern in Europe.'),
    (27, 'UNITED STATES', 'Musk pledges two SpaceX shares to every US child.'),
    (28, 'SHANGHAI', 'Probe of party chief Chen Jining continues.'),
]

NUMBERS = [
    ('14', 'TARIFF PARTNERS'),
    ('31', 'DEAD IN CAIRO FIRE'),
    ('12,021', 'EBOLA CASES, DRC'),
    ('5,904', 'EBOLA DEATHS, DRC'),
    ('\u20ac45bn', 'UKRAINE LOAN PLAN'),
    ('1,000,000', 'SATELLITES CLEARED'),
]

CHIPS = [
    ('NORTH AMERICA', 9), ('EUROPE', 6), ('ASIA', 6),
    ('AFRICA', 4), ('MIDDLE EAST', 2), ('SPACE', 1),
]

# Timeline entries: (fraction of the day, label).  Sequence is approximate;
# the band says so in print.
TIMELINE = [
    (0.06, 'KYIV STRUCK'),
    (0.22, 'GAZA STRIKES'),
    (0.38, 'RIYADH CLAIM'),
    (0.52, 'CAIRO TOLL: 31'),
    (0.66, 'EU SUMMIT OPENS'),
    (0.80, 'ASIA MARKETS UP'),
    (0.93, 'FCC CLEARS FLEET'),
]

# Dotted world map: 60 columns x 30 rows, '#' = land.  Column c covers
# longitude -180+6c .. -174+6c; row r covers latitude 85-5r .. 80-5r.
MAP_ROWS = [
    '#.....###............###.......#..#.##...##.................',
    '.####..######........####......#............................',
    '.#####.##########.....###.....####################..........',
    '..#####.###########...##......##########################....',
    '...##################.#.......############################..',
    '........############..........############################..',
    '.........###########.........#############################..',
    '.........############........####################.##........',
    '.........############........#########.################.....',
    '.........############.......#######################..#......',
    '.........##########.........#####################...........',
    '..........#####.............#########.###########...........',
    '..........####...............#################..##..........',
    '...........###...............#################..#...........',
    '.................####........#############.#....##..........',
    '.................#####.......##########......#######........',
    '.................######......#########........##########....',
    '.................######......#########.........##########...',
    '..................######.....########...........####.###....',
    '..................######.....#########..#.......########....',
    '..................######.....########...........########....',
    '..................#####......#######............########....',
    '...................####.......######............#######.....',
    '...................####.......#####.............######..#...',
    '....................##...........................##.##......',
    '....................##................................#.....',
    '....................#.......................................',
    '....................#.......................................',
    '............................................................',
    '............................................................',
]

# Card pins on the map: card number -> (longitude, latitude, dx, dy nudge).
PINS = {
    1: (-77.0, 38.9, -7, 5),
    2: (46.7, 24.6, 2, 3),
    3: (30.5, 50.4, 2, -1),
    4: (44.0, 56.3, 6, -4),
    5: (34.3, 31.5, 6, -6),
    6: (31.2, 30.0, -7, 7),
    7: (4.35, 50.85, -6, 1),
    8: (29.9, 1.6, 0, 2),
    9: (125.75, 39.0, -4, -5),
    10: (112.0, 30.0, -5, 6),
    11: (-74.0, 40.7, 7, -5),
    12: (139.7, 35.7, 6, 7),
    13: (-97.2, 26.0, -2, 2),
}


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

MARGIN = 26
PAGE_W = W - 2 * MARGIN


def draw_masthead():
    draw_text(W / 2, 14, 'THE WORLD IN ONE PAGE \u2022 ALL TIMES UTC \u2022 THURSDAY EDITION',
              11, RED, bold=True, align='center')
    hline(MARGIN, 36, PAGE_W, 2.6)
    draw_text(W / 2, 46, 'THE GLOBAL LEDGER', 53, INK, bold=True, align='center')
    draw_text(W / 2, 111, 'THURSDAY 26 NOVEMBER 2026', 38, INK, bold=True, align='center')
    draw_text(W / 2, 159, '28 STORIES FROM SIX REGIONS \u2014 EVERY ONE REPORTED ON THE DAY',
              10.5, SOFT, align='center')
    hline(MARGIN, 183, PAGE_W, 1.4)


def draw_chips(y):
    labels = ['%s %d' % (name, n) for name, n in CHIPS]
    labels.append('28 STORIES')
    widths = [text_width(t, 10.5, True) + 20 for t in labels]
    total = sum(widths) + 8 * (len(labels) - 1)
    x = (W - total) / 2
    for t, w in zip(labels, widths):
        if t == '28 STORIES':
            fill_rect(x, y, w, 25, INK)
            draw_text(x + w / 2, y + 7, t, 10.5, CREAM, bold=True, align='center')
        else:
            fill_rect(x, y, w, 1.2, INK)
            fill_rect(x, y + 23.8, w, 1.2, INK)
            fill_rect(x, y, 1.2, 25, INK)
            fill_rect(x + w - 1.2, y, 1.2, 25, INK)
            draw_text(x + w / 2, y + 7, t, 10.5, INK, bold=True, align='center')
        x += w + 8


def draw_timeline(y):
    x0 = MARGIN + 6
    x1 = W - MARGIN - 6
    draw_text(x0, y, 'THE DAY IN UTC \u2014 SEQUENCE APPROXIMATE', 9.5, SOFT, bold=True)
    hline(x0, y + 18, x1 - x0, 1.6)
    for i in range(9):
        fx = x0 + (x1 - x0) * i / 8
        vline(fx, y + 13, 10, 1.4)
        draw_text(fx, y + 25, '%02d' % (i * 3), 9, SOFT, align='center')
    for frac, label in TIMELINE:
        fx = x0 + (x1 - x0) * frac
        fill_circle(fx, y + 18, 3.4, RED)
        draw_text(fx, y + 38, label, 9, INK, align='center')


STATUS_COLORS = {
    'ON RECORD': TAG_ON_RECORD,
    'REPORTED': TAG_REPORTED,
    'CLAIM': TAG_CLAIM,
}


def draw_card(x, y, w, h, card, tall):
    num, place, category, status, source, headline, summary = card
    hline(x, y, w, 1.6)
    # number badge
    fill_circle(x + 10, y + 13, 8.6, INK)
    draw_text(x + 10, y + 8.6, str(num), 10.5, CREAM, bold=True, align='center')
    # place and category
    draw_text(x + 24, y + 6.5, '%s \u2014 %s' % (place, category), 10.5, INK, bold=True)
    # status tag, right aligned
    tag = status
    tw = text_width(tag, 9, True) + 13
    fill_rect(x + w - tw, y + 4.5, tw, 16.5, STATUS_COLORS[tag])
    draw_text(x + w - tw / 2, y + 8.1, tag, 9, CREAM, bold=True, align='center')
    # headline, then summary stacked directly underneath
    hsize = 14 if tall else 12
    cy = y + 25
    for line in wrap_text(headline, hsize, w - 4, bold=True)[:2]:
        draw_text(x + 1, cy, line, hsize, INK, bold=True)
        cy += hsize + (3.2 if tall else 2.9)
    ssize = 10.5 if tall else 9.6
    cy += 2
    maxlines = 3 if tall else 2
    for line in wrap_text(summary, ssize, w - 4)[:maxlines]:
        draw_text(x + 1, cy, line, ssize, INK)
        cy += ssize + (2.4 if tall else 2.2)


def draw_cards():
    top = 272
    zone_h = 424
    col_w = (PAGE_W - 2 * 14) / 3
    cols = [CARDS[0:5], CARDS[5:9], CARDS[9:13]]
    for ci, cards in enumerate(cols):
        x = MARGIN + ci * (col_w + 14)
        n = len(cards)
        gap = 5
        ch = (zone_h - gap * (n - 1)) / n
        for ri, card in enumerate(cards):
            draw_card(x, top + ri * (ch + gap), col_w, ch, card, tall=(n == 4))


def draw_briefs(x, y, w):
    draw_text(x, y, 'ALSO ON THURSDAY', 13, RED, bold=True)
    hline(x, y + 20, w, 1.6)
    col_w = (w - 18) / 2
    per = 8
    pitch = 23.1
    for i, (num, place, text) in enumerate(BRIEFS):
        cx = x + (i // per) * (col_w + 18)
        cy = y + 25 + (i % per) * pitch
        head = '%d %s \u2014 ' % (num, place)
        lines = wrap_text(head + text, 9.0, col_w)
        ly = cy
        for line in lines[:2]:
            draw_text(cx, ly, line, 9.0, INK)
            ly += 11.3


def draw_map(x, y, w, h):
    draw_text(x, y, 'WHERE IT HAPPENED', 13, RED, bold=True)
    hline(x, y + 20, w, 1.6)
    top = y + 27
    mh = h - 27
    cols = len(MAP_ROWS[0])
    rows = len(MAP_ROWS)
    cw = w / cols
    chh = mh / rows
    r = min(cw, chh) * 0.30
    for ri, row in enumerate(MAP_ROWS):
        for ci, cell in enumerate(row):
            if cell == '#':
                fill_circle(x + (ci + 0.5) * cw, top + (ri + 0.5) * chh, r, (120, 112, 98))
    for num in sorted(PINS):
        lon, lat, dx, dy = PINS[num]
        px = x + (lon + 180) / 360 * w + dx
        py = top + (85 - lat) / 150 * mh + dy
        fill_circle(px, py, 8.4, RED)
        draw_text(px, py - 4.4, str(num), 9, CREAM, bold=True, align='center')


def draw_numbers(y):
    fill_rect(MARGIN, y, PAGE_W, 47, INK)
    draw_text(MARGIN + 14, y + 6, 'THE DAY IN', 10.5, CREAM, bold=True)
    draw_text(MARGIN + 14, y + 19.5, 'NUMBERS', 10.5, CREAM, bold=True)
    cell_x = MARGIN + 108
    cell_w = (W - MARGIN - cell_x) / len(NUMBERS)
    for i, (big, label) in enumerate(NUMBERS):
        cx = cell_x + i * cell_w
        if i:
            vline(cx - 7, y + 7, 32, 1, (110, 102, 90))
        size = 19
        while text_width(big, size, True) > cell_w - 12 and size > 12:
            size -= 1
        draw_text(cx, y + 5, big, size, CREAM, bold=True)
        draw_text(cx, y + 28, label, 8.6, (214, 206, 190))


def draw_footer(y):
    hline(MARGIN, y, PAGE_W, 1.6)
    lines = wrap_text(
        'DATE CHECK \u2014 Every story on this page was reported on Thursday 26 November 2026. '
        'Nothing from an earlier day is presented as news of the day: earlier items are '
        'excluded, or named as background only.', 9.5, PAGE_W)
    ly = y + 8
    for line in lines[:2]:
        draw_text(MARGIN, ly, line, 9.5, INK)
        ly += 12.5
    ly += 2
    draw_text(MARGIN, ly, 'STATUS KEY:', 9.5, INK, bold=True)
    lx = MARGIN + text_width('STATUS KEY: ', 9.5, True)
    for tag, note in [('ON RECORD', 'official'),
                      ('REPORTED', 'press reports'),
                      ('CLAIM', "a party's claim")]:
        tw = text_width(tag, 8.6, True) + 10
        fill_rect(lx, ly - 1.5, tw, 14.5, STATUS_COLORS[tag])
        draw_text(lx + tw / 2, ly + 1.6, tag, 8.6, CREAM, bold=True, align='center')
        lx += tw + 5
        draw_text(lx, ly, '= ' + note, 9.5, SOFT)
        lx += text_width('= ' + note, 9.5) + 14
    draw_text(W - MARGIN, ly, 'PAGE 1 OF 1', 9.5, SOFT, align='right')


def render():
    fill_all(PAPER)
    draw_masthead()
    draw_chips(189)
    draw_timeline(219)
    draw_cards()
    bottom = 696
    draw_briefs(MARGIN, bottom, 618)
    draw_map(662, bottom, 336, 192)
    draw_numbers(908)
    draw_footer(970)


# --------------------------------------------------------------------------
# Downsample (4x4 area average) and PNG output
# --------------------------------------------------------------------------

def downsample():
    out = bytearray(W * H * 3)
    rowlen = IW * 3
    for oy in range(H):
        base = oy * SS * rowlen
        rows = [FB[base + dy * rowlen: base + (dy + 1) * rowlen] for dy in range(SS)]
        summed = [a + b + c + d for a, b, c, d in zip(*rows)]
        obase = oy * W * 3
        for c in range(3):
            chan = summed[c::3]
            vals = [(chan[i] + chan[i + 1] + chan[i + 2] + chan[i + 3] + 8) // 16
                    for i in range(0, len(chan), SS)]
            out[obase + c: obase + W * 3: 3] = bytes(vals)
    return out


def png_bytes(img):
    raw = bytearray()
    rowlen = W * 3
    for y in range(H):
        raw.append(0)
        raw += img[y * rowlen:(y + 1) * rowlen]

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))


def main():
    render()
    img = downsample()
    data = png_bytes(img)
    out = os.environ.get('ENTRY_OUT', '/output/entry.png')
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, 'wb') as f:
        f.write(data)


if __name__ == '__main__':
    main()
