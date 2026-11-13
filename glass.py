"""Glassmorphism stylesheet for ARticulate: frosted, translucent panels floating over the
magenta-purple particle video. Kept in its own module so `build_css()` in art.py stays readable."""
from pathlib import Path

# NOTE: never put backdrop-filter / filter / transform on .block-container or any ancestor of
# the fixed background layers (.bgvid, .particles) -- those properties make an element the
# containing block for fixed-position descendants, which would pin the video to the panel
# instead of the viewport.
GLASS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

/* ============================== glass tokens ============================== */
:root {
  --ink: #F5F2FF;
  --ink-dim: rgba(233, 226, 255, .74);
  --accent: #FF3CAC;
  --accent-2: #7C4DFF;
  --accent-3: #16B7FF;
  --accent-4: #3DDC84;
  --glass-tint: rgba(26, 16, 60, .42);
  --glass-tint-solid: rgba(22, 13, 52, .78);
  --glass-hi: rgba(255, 255, 255, .17);
  --glass-lo: rgba(255, 255, 255, .04);
  --glass-edge: rgba(255, 255, 255, .26);
  --glass-edge-soft: rgba(255, 255, 255, .13);
  --glass-blur: blur(18px) saturate(165%);
  --glass-radius: 18px;
  --glass-shadow: 0 16px 44px rgba(5, 2, 18, .5),
                  inset 0 1px 0 rgba(255, 255, 255, .32),
                  inset 0 -1px 0 rgba(255, 255, 255, .05);
  --glass-sheen: linear-gradient(160deg, var(--glass-hi) 0%, var(--glass-lo) 46%, rgba(255, 255, 255, .02) 100%);
}

/* ============================== app shell ============================== */
.stApp { background:
  radial-gradient(circle at 8% 0%, rgba(124, 77, 255, .40) 0, transparent 38%),
  radial-gradient(circle at 95% 8%, rgba(0, 200, 255, .26) 0, transparent 40%),
  radial-gradient(circle at 60% 105%, rgba(255, 60, 172, .26) 0, transparent 45%), #06031a; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .stMain { background: transparent !important; }

/* the frosted app bar */
header[data-testid="stHeader"] {
  background: linear-gradient(180deg, rgba(18, 10, 44, .55), rgba(18, 10, 44, .22)) !important;
  backdrop-filter: blur(20px) saturate(150%); -webkit-backdrop-filter: blur(20px) saturate(150%);
  border-bottom: 1px solid var(--glass-edge-soft); }

/* the main content stage: translucent pane so text stays legible over the video
   (tint only -- no backdrop-filter here, see the note at the top of this file) */
[data-testid="stMainBlockContainer"], .block-container {
  position: relative; z-index: 1;
  margin: 4rem auto 2.2rem; padding: 1.8rem 1.9rem 2.6rem;   /* 4rem clears the fixed app bar */
  background: linear-gradient(165deg, rgba(255, 255, 255, .055), rgba(255, 255, 255, .012) 60%, rgba(255, 255, 255, .03));
  border: 1px solid var(--glass-edge-soft); border-radius: 26px;
  box-shadow: 0 24px 60px rgba(4, 2, 14, .45), inset 0 1px 0 rgba(255, 255, 255, .18); }

/* ============================== sidebar ============================== */
section[data-testid="stSidebar"] {
  /* 30% transparent / 70% opaque. The two layers stack, so the sheen is not free:
     1 - (1 - .65) * (1 - .14) = .699. Just setting the base to .70 would land at ~74% opaque. */
  background: linear-gradient(180deg, rgba(124, 77, 255, .14) 0%, rgba(28, 30, 96, .14) 52%, rgba(10, 58, 92, .14) 100%), rgba(12, 8, 34, .65) !important;
  backdrop-filter: blur(24px) saturate(150%); -webkit-backdrop-filter: blur(24px) saturate(150%);
  border-right: 1px solid var(--glass-edge-soft);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, .06); }
[data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"], section[data-testid="stSidebar"] > div:first-child {
  background: transparent !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: var(--ink) !important; }

/* ============================== typography ============================== */
h1, h2, h3, h4 { color: var(--ink); letter-spacing: .2px; }
h3 { background: linear-gradient(90deg, #ff9ff3, #7cf9ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
p, li, [data-testid="stMarkdownContainer"] { color: var(--ink); }
[data-testid="stCaptionContainer"], .stCaption, caption, small { color: var(--ink-dim) !important; }
[data-testid="stMarkdownContainer"] p { text-shadow: 0 1px 10px rgba(5, 2, 18, .45); }

/* ============================== frosted surfaces ============================== */
.quest, .hero-text,
[data-testid="stMetric"], [data-testid="stForm"], [data-testid="stExpander"] details,
[data-testid="stDataFrame"], [data-testid="stFileUploaderDropzone"], [data-testid="stAudioInput"] section {
  background: var(--glass-sheen), var(--glass-tint) !important;
  backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-edge) !important;
  border-radius: var(--glass-radius) !important;
  box-shadow: var(--glass-shadow) !important; }

/* the hero banner keeps its artwork, but sits in a glass frame */
.hero { position: relative; border-radius: 22px; overflow: hidden; min-height: 190px; display: flex; align-items: center;
        padding: 1.1rem 1.2rem; margin: .2rem 0 1.1rem; background-size: cover; background-position: center;
        background-image: url(__HERO__);
        border: 1px solid var(--glass-edge); box-shadow: 0 20px 50px rgba(20, 8, 60, .55), inset 0 1px 0 rgba(255, 255, 255, .28); }
.hero::before { content: ""; position: absolute; inset: 0;
                background: linear-gradient(100deg, rgba(8, 4, 26, .62) 0%, rgba(8, 4, 26, .12) 62%, rgba(8, 4, 26, .05) 100%); }
.hero-text { position: relative; max-width: 60%; padding: .9rem 1.2rem; border-radius: 18px; }
.hero-title { font-family: 'Press Start 2P', monospace; font-size: clamp(1.1rem, 3.4vw, 2.1rem); color: #fff;
              text-shadow: 0 0 18px rgba(124, 249, 255, .85), 3px 3px 0 #ff3cac; line-height: 1.35; }
.hero-sub { margin-top: .7rem; font-size: clamp(.85rem, 1.6vw, 1.05rem); color: #fff; text-shadow: 0 1px 6px rgba(0, 0, 0, .6); }

/* the question card: frosted panel with a rainbow glass rim */
.quest { position: relative; padding: 1.1rem 1.35rem; margin: .5rem 0 .7rem; font-size: 1.2rem; color: var(--ink); }
.quest::after { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1.5px; pointer-events: none;
                background: linear-gradient(135deg, var(--accent), var(--accent-2) 45%, var(--accent-3) 78%, var(--accent-4));
                -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
                -webkit-mask-composite: xor; mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
                mask-composite: exclude; opacity: .85; }
.quest .tag { font-family: 'Press Start 2P', monospace; font-size: .65rem; color: #ffe66d; margin-bottom: .6rem; letter-spacing: 1px; }

/* level row + level tiles */
.lvlrow { display: flex; align-items: center; gap: .7rem; margin: .4rem 0; }
.avatar { width: 56px; height: 56px; flex: none; background-size: contain; background-repeat: no-repeat; background-position: center; }
.lvl { font-family: 'Press Start 2P', monospace; font-size: .75rem; color: #ffe66d; line-height: 1.5; }
.done { display: flex; align-items: center; gap: .7rem; margin: 1rem 0 .3rem; font-size: 1.6rem; font-weight: 700; color: var(--ink); }
.trophy { width: 52px; height: 52px; background-size: contain; background-repeat: no-repeat; background-image: url(__TROPHY__); }
.grade { font-family: 'Press Start 2P', monospace; font-size: 2.6rem; text-align: center; line-height: 1.3; }
.grade-S { color: #ffe66d; text-shadow: 0 0 16px #ffe66d; } .grade-A { color: #3ddc84; text-shadow: 0 0 12px #3ddc84; }
.grade-B { color: #7cf9ff; text-shadow: 0 0 12px #7cf9ff; } .grade-C { color: #ffa726; } .grade-D { color: #ff5252; }
.gcap { text-align: center; font-size: .75rem; opacity: .78; }
[data-testid="stMetric"] { padding: .85rem 1rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: var(--ink-dim) !important; }
[data-testid="stMetricValue"] { color: #7cf9ff; }

/* ============================== form widgets ============================== */
div[data-baseweb="input"], div[data-baseweb="textarea"],
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea,
div[data-baseweb="select"] > div {
  background: rgba(255, 255, 255, .07) !important;
  color: var(--ink) !important;
  border: 1px solid rgba(255, 255, 255, .20) !important;
  border-radius: 12px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), inset 0 -12px 24px rgba(255, 255, 255, .02) !important;
  backdrop-filter: blur(12px) saturate(150%); -webkit-backdrop-filter: blur(12px) saturate(150%); }
div[data-baseweb="select"] > div { background: rgba(255, 255, 255, .07) !important; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
  border-color: rgba(0, 229, 255, .75) !important;
  box-shadow: 0 0 0 3px rgba(0, 229, 255, .20), inset 0 1px 0 rgba(255, 255, 255, .2) !important; }
input::placeholder, textarea::placeholder { color: rgba(226, 220, 255, .55) !important; }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, label p { color: var(--ink) !important; font-weight: 600; }

/* dropdown menus float above everything: denser glass so options stay readable */
div[data-baseweb="popover"] div[role="listbox"], div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] > div > div {
  background: linear-gradient(160deg, rgba(255, 255, 255, .12), rgba(255, 255, 255, .03)), var(--glass-tint-solid) !important;
  backdrop-filter: blur(22px) saturate(160%); -webkit-backdrop-filter: blur(22px) saturate(160%);
  border: 1px solid var(--glass-edge) !important; border-radius: 14px !important;
  box-shadow: 0 26px 54px rgba(4, 2, 14, .6) !important; }
div[data-baseweb="popover"] li[role="option"]:hover,
div[data-baseweb="popover"] li[aria-selected="true"] { background: rgba(255, 255, 255, .13) !important; }

/* toggles, checkboxes, radios keep their native control but sit on the glass */
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label, [data-testid="stToggle"] label,
[data-baseweb="checkbox"] div[role="checkbox"] + div, [role="radiogroup"] label div { color: var(--ink) !important; }
[data-baseweb="checkbox"] div[role="checkbox"] { background: rgba(255, 255, 255, .10) !important;
  border-color: rgba(255, 255, 255, .38) !important; border-radius: 7px; }

/* sliders + progress read as thin glass rails */
[data-testid="stSlider"] div[role="slider"] { background: #fff !important; box-shadow: 0 0 0 4px rgba(124, 77, 255, .35) !important; }
[data-testid="stProgress"] > div > div { background: rgba(255, 255, 255, .12) !important; border-radius: 999px; }
[data-testid="stProgress"] div[role="progressbar"] > div {
  background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3)) !important; border-radius: 999px; }

/* ============================== buttons ============================== */
div.stButton > button, div.stDownloadButton > button, [data-testid="stFormSubmitButton"] > button,
button[data-testid^="stBaseButton"] {
  background: var(--glass-sheen), rgba(124, 77, 255, .38) !important;
  color: #fff !important; border: 1px solid rgba(255, 255, 255, .30) !important;
  border-radius: 14px !important; font-weight: 700; letter-spacing: .2px;
  backdrop-filter: blur(14px) saturate(155%); -webkit-backdrop-filter: blur(14px) saturate(155%);
  box-shadow: 0 10px 26px rgba(7, 3, 24, .45), inset 0 1px 0 rgba(255, 255, 255, .38) !important;
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease, border-color .16s ease; }
div.stButton > button:hover, div.stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover,
button[data-testid^="stBaseButton"]:hover {
  background: var(--glass-sheen), linear-gradient(135deg, rgba(255, 60, 172, .62), rgba(124, 77, 255, .62)) !important;
  border-color: rgba(255, 255, 255, .45) !important; color: #fff !important;
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(255, 60, 172, .32), inset 0 1px 0 rgba(255, 255, 255, .45) !important; }
div.stButton > button:active, button[data-testid^="stBaseButton"]:active { transform: translateY(0); box-shadow: 0 6px 16px rgba(7, 3, 24, .5) !important; }
div.stButton > button:focus-visible, button[data-testid^="stBaseButton"]:focus-visible {
  outline: 2px solid rgba(0, 229, 255, .8); outline-offset: 2px; }

/* ============================== panels & data ============================== */
[data-testid="stExpander"] details { overflow: hidden; }
[data-testid="stExpander"] summary { background: transparent !important; border-radius: 16px; color: var(--ink) !important; }
[data-testid="stExpander"] summary:hover { background: rgba(255, 255, 255, .07) !important; }
[data-testid="stExpander"] details > div { border-top: 1px solid rgba(255, 255, 255, .12); }

[data-testid="stForm"] { padding: 1.1rem 1.2rem !important; }

[data-testid="stDataFrame"] { padding: .35rem; overflow: hidden; }

[data-testid="stFileUploaderDropzone"] { border-style: dashed !important; }
[data-testid="stFileUploaderDropzone"] button { background: rgba(255, 255, 255, .10) !important; }

[data-testid="stAlert"] {
  background: var(--glass-sheen), rgba(30, 20, 68, .5) !important;
  backdrop-filter: blur(14px) saturate(150%); -webkit-backdrop-filter: blur(14px) saturate(150%);
  border: 1px solid var(--glass-edge) !important; border-radius: 14px !important;
  box-shadow: var(--glass-shadow) !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div { color: var(--ink) !important; }

[data-testid="stToast"], [data-testid="stNotification"] {
  background: var(--glass-sheen), var(--glass-tint-solid) !important;
  backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid var(--glass-edge) !important; border-radius: 14px !important;
  box-shadow: 0 22px 46px rgba(4, 2, 14, .55) !important; }

/* tabs as a glass segmented control */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: rgba(255, 255, 255, .07) !important; border: 1px solid var(--glass-edge-soft);
  border-radius: 14px; padding: 4px; gap: 4px;
  backdrop-filter: blur(12px) saturate(150%); -webkit-backdrop-filter: blur(12px) saturate(150%); }
[data-baseweb="tab"] { border-radius: 10px !important; color: var(--ink-dim) !important; }
[data-baseweb="tab"][aria-selected="true"] { background: rgba(255, 255, 255, .16) !important; color: #fff !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* ============================== background layers ============================== */
/* loop video, back to front: CSS glow fallback (-4), video (-3), scrim (-2), particles (-1) */
.bgloop { position: fixed; inset: 0; z-index: -4; pointer-events: none; overflow: hidden; }
.bgloop .glow { position: absolute; border-radius: 50%; filter: blur(50px); opacity: .55;
                animation: bgDrift 8s ease-in-out infinite; will-change: transform; }
.bgloop .g1 { width: 46vmax; height: 46vmax; left: -6vmax; top: 6vmax; animation-delay: -1s;
              background: radial-gradient(circle, #b14bff, rgba(177, 75, 255, 0) 70%); }
.bgloop .g2 { width: 40vmax; height: 40vmax; right: -5vmax; top: 30vmax; animation-delay: -4s;
              background: radial-gradient(circle, #ff3cac, rgba(255, 60, 172, 0) 70%); }
.bgloop .g3 { width: 52vmax; height: 52vmax; left: 26vmax; bottom: -20vmax; animation-delay: -6s;
              background: radial-gradient(circle, #7c4dff, rgba(124, 77, 255, 0) 72%); }
@keyframes bgDrift {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50%      { transform: translate3d(4vmax, -3vmax, 0) scale(1.18); }
}
.bgvid { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: -3;
         pointer-events: none; opacity: .9; filter: saturate(1.15); background: transparent; }
.bgscrim { position: fixed; inset: 0; z-index: -2; pointer-events: none;
           background: radial-gradient(ellipse at 50% 38%, rgba(10, 6, 32, .08) 0%, rgba(10, 6, 32, .68) 78%),
                       linear-gradient(180deg, rgba(10, 6, 32, .30), rgba(10, 6, 32, .52)); }

/* floating particles: behind the page content but above the video */
.particles { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.p { position: absolute; top: 0; left: 0; opacity: 0; animation-timing-function: linear; animation-iteration-count: infinite;
     will-change: transform, opacity; }
.p-dot { border-radius: 50%; background: var(--c); box-shadow: 0 0 12px var(--c); animation-name: floatUp; }
@keyframes floatUp {
  0%   { transform: translate3d(0, 105vh, 0) rotate(0deg); opacity: 0; }
  12%  { opacity: var(--o, .8); } 88% { opacity: var(--o, .8); }
  100% { transform: translate3d(var(--dx), -15vh, 0) rotate(360deg); opacity: 0; }
}

/* ============================== graceful degradation ============================== */
@supports not ((backdrop-filter: blur(4px)) or (-webkit-backdrop-filter: blur(4px))) {
  .quest, .hero-text, [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stExpander"] details,
  [data-testid="stDataFrame"], [data-testid="stFileUploaderDropzone"], [data-testid="stAlert"],
  section[data-testid="stSidebar"], header[data-testid="stHeader"], button[data-testid^="stBaseButton"] {
    background: linear-gradient(160deg, rgba(255, 255, 255, .12), rgba(255, 255, 255, .04)), rgba(20, 12, 48, .9) !important; }
}
@media (prefers-reduced-transparency: reduce) {
  .quest, .hero-text, [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stExpander"] details,
  [data-testid="stAlert"], section[data-testid="stSidebar"], header[data-testid="stHeader"] {
    backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(18, 11, 44, .93) !important; }
}
@media (prefers-reduced-motion: reduce) {
  .particles { display: none; } .bgvid { display: none; } .bgloop .glow { animation: none; }
  div.stButton > button, button[data-testid^="stBaseButton"] { transition: none; }
}
@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1.2rem 1rem 2rem; border-radius: 20px; margin: 3.6rem .4rem 1.4rem; }
  .hero { min-height: 150px; padding: .8rem; } .hero-text { max-width: 100%; padding: .7rem .9rem; }
  /* blur is the expensive part -- soften it on phones */
  .quest, .hero-text, [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stExpander"] details,
  [data-testid="stAlert"], header[data-testid="stHeader"] { backdrop-filter: blur(10px) saturate(150%); -webkit-backdrop-filter: blur(10px) saturate(150%); }
  section[data-testid="stSidebar"] { backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%); }
}
</style>
"""


def glass_css(hero_uri: str, trophy_uri: str) -> str:
    """Fill in the two generated data-URIs and return the finished <style> block."""
    return GLASS_CSS.replace("__HERO__", hero_uri).replace("__TROPHY__", trophy_uri)
