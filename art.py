"""Original AR/VR artwork (drawn as SVG, nothing to download) and the colourful theme CSS for ARticulate."""
import base64
import html
import random
from pathlib import Path

ASSETS = Path(__file__).with_name("assets")


def _uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def _cube(x, y, s, top, left, right, op=1.0):
    """Isometric solid cube. (x, y) is the top vertex, s the half-width."""
    h = s * 0.5
    t = f"{x},{y} {x + s},{y + h} {x},{y + 2 * h} {x - s},{y + h}"
    l = f"{x - s},{y + h} {x},{y + 2 * h} {x},{y + 2 * h + s} {x - s},{y + h + s}"
    r = f"{x},{y + 2 * h} {x + s},{y + h} {x + s},{y + h + s} {x},{y + 2 * h + s}"
    return (f'<g opacity="{op}"><polygon points="{l}" fill="{left}"/><polygon points="{r}" fill="{right}"/>'
            f'<polygon points="{t}" fill="{top}"/></g>')


def _wire_cube(x, y, s, color, w=2.2, op=0.9):
    """Hologram-style wireframe cube."""
    h = s * 0.5
    pts = {
        "t": (x, y), "r": (x + s, y + h), "b": (x, y + 2 * h), "l": (x - s, y + h),
        "tb": (x, y + s), "rb": (x + s, y + h + s), "bb": (x, y + 2 * h + s), "lb": (x - s, y + h + s),
    }
    edges = [("t", "r"), ("r", "b"), ("b", "l"), ("l", "t"), ("l", "lb"), ("b", "bb"), ("r", "rb"),
             ("lb", "bb"), ("bb", "rb")]
    lines = "".join(f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}"/>' for a, b in edges)
    return f'<g stroke="{color}" stroke-width="{w}" stroke-linecap="round" fill="none" opacity="{op}">{lines}</g>'


def hero_svg():
    rnd = random.Random(7)
    stars = "".join(
        f'<circle cx="{rnd.randint(10, 1190)}" cy="{rnd.randint(8, 190)}" r="{rnd.choice([1.2, 1.8, 2.4])}" '
        f'fill="#fff" opacity="{rnd.choice([0.35, 0.55, 0.8])}"/>' for _ in range(46)
    )
    grid = "".join(f'<line x1="600" y1="196" x2="{x}" y2="320" />' for x in range(-900, 2101, 120))
    grid += "".join(f'<line x1="0" y1="{y}" x2="1200" y2="{y}" />' for y in (204, 216, 232, 252, 278, 312))
    cubes = (
        _cube(70, 38, 20, "#ffe66d", "#ff9f1c", "#e85d04", .95)
        + _cube(205, 214, 14, "#9ef0ff", "#2ec4ff", "#1b8ed6", .9)
        + _cube(470, 30, 24, "#ff9ff3", "#f368e0", "#c11fa3", .9)
        + _cube(585, 206, 16, "#b2ffb2", "#3ddc84", "#1fa85a", .9)
        + _cube(715, 58, 13, "#ffe66d", "#ff9f1c", "#e85d04", .9)
        + _cube(770, 200, 20, "#c3b5ff", "#8a6dff", "#5b3fd1", .95)
        + _cube(1125, 190, 26, "#9ef0ff", "#2ec4ff", "#1b8ed6", .95)
        + _cube(40, 190, 12, "#ff9ff3", "#f368e0", "#c11fa3", .85)
    )
    wires = (_wire_cube(1095, 34, 30, "#7cf9ff", 2.6) + _wire_cube(345, 70, 16, "#ffffff", 2, .7)
             + _wire_cube(655, 128, 11, "#ffe66d", 1.8, .8))
    headset = """
  <g>
    <path d="M826 120 C770 120 770 205 826 205" fill="none" stroke="url(#strap)" stroke-width="16" stroke-linecap="round"/>
    <path d="M1034 120 C1090 120 1090 205 1034 205" fill="none" stroke="url(#strap)" stroke-width="16" stroke-linecap="round"/>
    <path d="M880 92 C930 52 980 52 1000 92" fill="none" stroke="url(#strap)" stroke-width="14" stroke-linecap="round"/>
    <rect x="814" y="96" width="232" height="116" rx="36" fill="url(#body)" stroke="#ffffff" stroke-opacity=".45" stroke-width="2"/>
    <rect x="828" y="108" width="204" height="90" rx="28" fill="url(#visor)"/>
    <path d="M846 118 C900 108 960 108 1014 118 L1014 128 C960 120 900 120 846 128 Z" fill="#fff" opacity=".16"/>
    <circle cx="884" cy="152" r="31" fill="url(#lens)"/><circle cx="884" cy="152" r="31" fill="none" stroke="#7cf9ff" stroke-width="3"/>
    <circle cx="976" cy="152" r="31" fill="url(#lens)"/><circle cx="976" cy="152" r="31" fill="none" stroke="#ff9ff3" stroke-width="3"/>
    <circle cx="874" cy="142" r="8" fill="#fff" opacity=".75"/><circle cx="966" cy="142" r="8" fill="#fff" opacity=".75"/>
    <path d="M918 198 Q930 178 942 198" fill="#0b0720"/>
    <rect x="804" y="130" width="14" height="44" rx="7" fill="#ff3cac"/><rect x="1042" y="130" width="14" height="44" rx="7" fill="#00e5ff"/>
    <rect x="896" y="100" width="68" height="6" rx="3" fill="#ffe66d" opacity=".9"/>
  </g>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300" preserveAspectRatio="xMidYMid slice">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff3cac"/><stop offset=".48" stop-color="#6a3df0"/><stop offset="1" stop-color="#16b7ff"/></linearGradient>
  <radialGradient id="glow1" cx=".82" cy=".45" r=".5"><stop offset="0" stop-color="#7cf9ff" stop-opacity=".75"/><stop offset="1" stop-color="#7cf9ff" stop-opacity="0"/></radialGradient>
  <radialGradient id="glow2" cx=".12" cy=".2" r=".45"><stop offset="0" stop-color="#ffe66d" stop-opacity=".55"/><stop offset="1" stop-color="#ffe66d" stop-opacity="0"/></radialGradient>
  <linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b3fd1"/><stop offset="1" stop-color="#1b1464"/></linearGradient>
  <linearGradient id="visor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a1550"/><stop offset="1" stop-color="#07041c"/></linearGradient>
  <radialGradient id="lens" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#d6fbff"/><stop offset=".45" stop-color="#3fb7ff"/><stop offset="1" stop-color="#2a1a9e"/></radialGradient>
  <linearGradient id="strap" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff9ff3"/><stop offset="1" stop-color="#7cf9ff"/></linearGradient>
</defs>
<rect width="1200" height="300" fill="url(#bg)"/>
<rect width="1200" height="300" fill="url(#glow1)"/><rect width="1200" height="300" fill="url(#glow2)"/>
{stars}
<g stroke="#ffffff" stroke-opacity=".28" stroke-width="1.4">{grid}</g>
{cubes}{wires}{headset}
</svg>"""


def _avatar(inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs>'
            '<linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff9ff3"/><stop offset="1" stop-color="#7cf9ff"/></linearGradient>'
            '<linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe66d"/><stop offset="1" stop-color="#ff7a59"/></linearGradient>'
            '</defs><circle cx="32" cy="32" r="30" fill="#1b1464" stroke="url(#g1)" stroke-width="3"/>' + inner + '</svg>')


AVATARS = [
    # 1 Rookie: cube
    _avatar(_cube(32, 15, 15, "#ffe66d", "#ff9f1c", "#e85d04")),
    # 2 Apprentice: headset
    _avatar('<rect x="12" y="23" width="40" height="22" rx="9" fill="#6a3df0" stroke="#fff" stroke-opacity=".5"/>'
            '<circle cx="24" cy="34" r="7" fill="#7cf9ff"/><circle cx="40" cy="34" r="7" fill="#ff9ff3"/>'
            '<path d="M14 28 C6 28 6 42 14 42 M50 28 C58 28 58 42 50 42" stroke="#ffe66d" stroke-width="3" fill="none" stroke-linecap="round"/>'),
    # 3 Challenger: AR glasses
    _avatar('<rect x="10" y="26" width="19" height="14" rx="6" fill="#7cf9ff" fill-opacity=".85" stroke="#fff"/>'
            '<rect x="35" y="26" width="19" height="14" rx="6" fill="#ff9ff3" fill-opacity=".85" stroke="#fff"/>'
            '<path d="M29 32 H35" stroke="#fff" stroke-width="3"/><path d="M10 30 L5 26 M54 30 L59 26" stroke="#fff" stroke-width="3" stroke-linecap="round"/>'
            '<path d="M32 14 L35 20 L41 21 L36 25 L38 31" stroke="#ffe66d" stroke-width="0" fill="none"/>'
            '<circle cx="32" cy="16" r="3" fill="#ffe66d"/><circle cx="22" cy="20" r="2" fill="#fff"/><circle cx="42" cy="19" r="2" fill="#fff"/>'),
    # 4 Veteran: controller rings
    _avatar('<circle cx="22" cy="38" r="9" fill="none" stroke="url(#g2)" stroke-width="5"/>'
            '<circle cx="42" cy="38" r="9" fill="none" stroke="url(#g1)" stroke-width="5"/>'
            '<rect x="18" y="14" width="6" height="16" rx="3" fill="#ffe66d"/><rect x="40" y="14" width="6" height="16" rx="3" fill="#7cf9ff"/>'),
    # 5 Hero: shield with star
    _avatar('<path d="M32 10 L50 17 V32 C50 43 42 50 32 55 C22 50 14 43 14 32 V17 Z" fill="url(#g1)" stroke="#fff" stroke-width="2"/>'
            '<polygon points="32,20 35,28 44,28 37,33 40,42 32,36 24,42 27,33 20,28 29,28" fill="#1b1464"/>'),
    # 6 Legend: crown
    _avatar('<path d="M12 44 L16 22 L26 33 L32 16 L38 33 L48 22 L52 44 Z" fill="url(#g2)" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>'
            '<rect x="12" y="44" width="40" height="7" rx="3" fill="#ff9ff3" stroke="#fff"/>'
            '<circle cx="16" cy="21" r="3" fill="#7cf9ff"/><circle cx="32" cy="15" r="3" fill="#7cf9ff"/><circle cx="48" cy="21" r="3" fill="#7cf9ff"/>'),
]

TROPHY = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs>'
          '<linearGradient id="t" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe66d"/><stop offset="1" stop-color="#ff7a59"/></linearGradient></defs>'
          '<path d="M20 10 H44 V28 C44 38 38 43 32 43 C26 43 20 38 20 28 Z" fill="url(#t)" stroke="#fff" stroke-width="2"/>'
          '<path d="M20 14 H10 C10 26 14 30 21 31 M44 14 H54 C54 26 50 30 43 31" fill="none" stroke="#ffe66d" stroke-width="3"/>'
          '<rect x="29" y="43" width="6" height="8" fill="#ffe66d"/><rect x="21" y="51" width="22" height="6" rx="3" fill="#ff3cac" stroke="#fff"/>'
          '<polygon points="32,15 34,21 40,21 35,25 37,31 32,27 27,31 29,25 24,21 30,21" fill="#fff" opacity=".9"/></svg>')


def _hero_background():
    """A custom picture dropped into an 'assets' folder (hero.jpg/.png/.webp) replaces the drawn banner."""
    for ext, mime in (("jpg", "image/jpeg"), ("jpeg", "image/jpeg"), ("png", "image/png"), ("webp", "image/webp")):
        p = ASSETS / f"hero.{ext}"
        if p.exists() and p.stat().st_size < 3_000_000:
            return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return _uri(hero_svg())


def build_css():
    av = "".join(f".av{i + 1}{{background-image:url({_uri(s)});}}\n" for i, s in enumerate(AVATARS))
    return """<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
.stApp { background:
  radial-gradient(circle at 8% 0%, rgba(124,77,255,.45) 0, transparent 38%),
  radial-gradient(circle at 95% 8%, rgba(0,200,255,.30) 0, transparent 40%),
  radial-gradient(circle at 60% 105%, rgba(255,60,172,.28) 0, transparent 45%), #0a0620; }
[data-testid="stSidebar"], section[data-testid="stSidebar"] > div:first-child {
  background: linear-gradient(180deg, #2a1470 0%, #14205f 55%, #0b3a5c 100%) !important; }
h1, h2, h3 { color: #fff; }
h3 { background: linear-gradient(90deg, #ff9ff3, #7cf9ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero { position: relative; border-radius: 20px; overflow: hidden; min-height: 190px; display: flex; align-items: center;
        padding: 1.2rem 1.8rem; margin: .2rem 0 1rem; background-size: cover; background-position: center;
        box-shadow: 0 10px 34px rgba(106,61,240,.55); border: 2px solid rgba(255,255,255,.25);
        background-image: url(__HERO__); }
.hero::before { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(10,6,32,.55) 0%, rgba(10,6,32,0) 60%); }
.hero-text { position: relative; max-width: 58%; }
.hero-title { font-family: 'Press Start 2P', monospace; font-size: clamp(1.1rem, 3.4vw, 2.1rem); color: #fff;
              text-shadow: 0 0 18px rgba(124,249,255,.85), 3px 3px 0 #ff3cac; line-height: 1.35; }
.hero-sub { margin-top: .7rem; font-size: clamp(.85rem, 1.6vw, 1.05rem); color: #fff; text-shadow: 0 1px 6px rgba(0,0,0,.6); }
.quest { border: 3px solid transparent; border-radius: 16px; padding: 1.1rem 1.3rem; margin: .5rem 0 .6rem; font-size: 1.2rem;
         background: linear-gradient(#171042, #171042) padding-box, linear-gradient(135deg, #ff3cac, #7c4dff, #16b7ff, #3ddc84) border-box;
         box-shadow: 0 0 24px rgba(124,77,255,.45); }
.quest .tag { font-family: 'Press Start 2P', monospace; font-size: .65rem; color: #ffe66d; margin-bottom: .6rem; letter-spacing: 1px; }
.lvlrow { display: flex; align-items: center; gap: .7rem; margin: .4rem 0; }
.avatar { width: 56px; height: 56px; flex: none; background-size: contain; background-repeat: no-repeat; background-position: center; }
.lvl { font-family: 'Press Start 2P', monospace; font-size: .75rem; color: #ffe66d; line-height: 1.5; }
.done { display: flex; align-items: center; gap: .7rem; margin: 1rem 0 .3rem; font-size: 1.6rem; font-weight: 700; }
.trophy { width: 52px; height: 52px; background-size: contain; background-repeat: no-repeat; background-image: url(__TROPHY__); }
.grade { font-family: 'Press Start 2P', monospace; font-size: 2.6rem; text-align: center; line-height: 1.3; }
.grade-S { color: #ffe66d; text-shadow: 0 0 16px #ffe66d; } .grade-A { color: #3ddc84; text-shadow: 0 0 12px #3ddc84; }
.grade-B { color: #7cf9ff; text-shadow: 0 0 12px #7cf9ff; } .grade-C { color: #ffa726; } .grade-D { color: #ff5252; }
.gcap { text-align: center; font-size: .75rem; opacity: .75; }
[data-testid="stMetricValue"] { color: #7cf9ff; }
div.stButton > button, div.stDownloadButton > button, button[kind="secondaryFormSubmit"], button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #7c4dff, #16b7ff); color: #fff; border: 0; border-radius: 12px; font-weight: 700; }
div.stButton > button:hover, div.stDownloadButton > button:hover { background: linear-gradient(135deg, #ff3cac, #7c4dff); color: #fff; box-shadow: 0 0 16px rgba(255,60,172,.65); }

/* ---- floating particles: they live behind the page content but above the colourful background ---- */
[data-testid="stAppViewContainer"], [data-testid="stMain"], .stMain, header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMainBlockContainer"], .block-container { position: relative; z-index: 1; }
.particles { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.p { position: absolute; top: 0; left: 0; opacity: 0; animation-name: floatUp; animation-timing-function: linear;
     animation-iteration-count: infinite; will-change: transform, opacity; }
.p-dot { border-radius: 50%; background: var(--c); box-shadow: 0 0 12px var(--c); }
.p-ring { border-radius: 50%; border: 2px solid var(--c); box-shadow: 0 0 10px var(--c); }
.p-sq { border: 2px solid var(--c); border-radius: 3px; background: rgba(255,255,255,.07); box-shadow: 0 0 10px var(--c); }
.p-dia { background: var(--c); clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); filter: drop-shadow(0 0 6px var(--c)); }
@keyframes floatUp {
  0%   { transform: translate3d(0, 105vh, 0) rotate(0deg); opacity: 0; }
  12%  { opacity: .75; }
  88%  { opacity: .75; }
  100% { transform: translate3d(var(--dx), -15vh, 0) rotate(360deg); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) { .particles { display: none; } }
@media (max-width: 700px) { .hero { min-height: 150px; padding: 1rem; } .hero-text { max-width: 100%; } }
""".replace("__HERO__", _hero_background()).replace("__TROPHY__", _uri(TROPHY)) + av + "</style>"


def particles_html(n=36):
    """Slowly rising dots, rings, squares and diamonds. Pure CSS, so there is no script and nothing to load."""
    rnd = random.Random(21)
    colours = ["#ff9ff3", "#7cf9ff", "#ffe66d", "#3ddc84", "#c3b5ff", "#ff7a59"]
    shapes = ["p-dot", "p-dot", "p-ring", "p-sq", "p-dia"]
    items = []
    for _ in range(n):
        size = rnd.choice([6, 8, 10, 14, 18, 24])
        dur = rnd.randint(16, 38)
        style = (f"left:{rnd.randint(1, 98)}%;width:{size}px;height:{size}px;--c:{rnd.choice(colours)};"
                 f"--dx:{rnd.randint(-90, 90)}px;animation-duration:{dur}s;animation-delay:-{rnd.randint(0, dur)}s")
        items.append(f'<div class="p {rnd.choice(shapes)}" style="{style}"></div>')
    return '<div class="particles">' + "".join(items) + "</div>"


def hero_html(name, tagline):
    return (f'<div class="hero"><div class="hero-text"><div class="hero-title">🥽 {html.escape(name)}</div>'
            f'<div class="hero-sub">{html.escape(tagline)}</div></div></div>')


def level_html(level, title, xp_line=None):
    i = min(max(level, 1), len(AVATARS))
    return (f'<div class="lvlrow"><div class="avatar av{i}"></div>'
            f'<div class="lvl">LV {level}<br>{html.escape(title)}</div></div>')


def trophy_html(text):
    return f'<div class="done"><div class="trophy"></div><div>{html.escape(text)}</div></div>'
