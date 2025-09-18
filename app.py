
import streamlit as st
import requests
import random
import html
from typing import Dict, Tuple, Optional

st.set_page_config(page_title="TriviaBot", page_icon="🤖", layout="wide")

# -------------------------------
# THEME & STYLES
# -------------------------------
PRIMARY_BG = "#0f172a"   # slate-900
CARD_BG    = "#111827"   # gray-900
TEXT_COL   = "#e5e7eb"   # gray-200
MUTED_COL  = "#94a3b8"   # slate-400
ACCENT     = "#f59e0b"   # amber-500
LINK_COL   = "#93c5fd"   # blue-300

CUSTOM_CSS = f"""
<style>
  .stApp {{ background: {PRIMARY_BG}; color: {TEXT_COL}; }}
  .app-title {{ font-size: clamp(28px, 3vw, 40px); font-weight: 800; margin: 0 0 8px; }}
  .subtitle {{ color: {MUTED_COL}; margin-bottom: 18px; }}
  .panel {{ background: {CARD_BG}; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; }}
  .question-card {{ background: {CARD_BG}; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; }}
  .badge {{ display: inline-block; font-size: 12px; padding: 4px 10px; border-radius: 999px; background: rgba(255,255,255,0.08); color: {MUTED_COL}; margin-left: 8px; }}
  .category {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
  .question-text {{ font-size: 20px; line-height: 1.5; margin-top: 6px; }}
  .answer-box {{ background: rgba(255,255,255,0.04); border: 1px dashed rgba(255,255,255,0.15); padding: 14px; border-radius: 12px; margin-top: 10px; }}
  .muted {{ color: {MUTED_COL}; }}
  a, .stMarkdown a {{ color: {LINK_COL}; }}
  .spacer-8 {{ height: 8px; }}
  .spacer-16 {{ height: 16px; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------
# DIFFICULTY
# -------------------------------
DIFF_LABELS = ["Baby Barbara", "Average Joe", "College Carl", "PhD Pat"]
DIFF_MAP = {
    "Baby Barbara": "easy",
    "Average Joe": "medium",
    "College Carl": "hard",
    "PhD Pat": "expert"  # map to 'hard' for APIs that top out at hard
}

def map_to_trivia_api(diff_label: str) -> str:
    d = DIFF_MAP.get(diff_label, "easy")
    return "hard" if d == "expert" else d

# -------------------------------
# HELPERS
# -------------------------------
def get_json(url: str, params: Optional[Dict] = None, timeout: int = 12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_opentdb_question(difficulty_api: str, category: int = None):
    params = {"amount": 1, "type": "multiple", "encode": "base64"}
    if difficulty_api in ("easy", "medium", "hard"):
        params["difficulty"] = difficulty_api
    if category:
        params["category"] = category
    data = get_json("https://opentdb.com/api.php", params=params)
    if not data or data.get("response_code") != 0:
        return None, None, None
    import base64
    item = data["results"][0]
    q = base64.b64decode(item["question"]).decode("utf-8", errors="ignore")
    a = base64.b64decode(item["correct_answer"]).decode("utf-8", errors="ignore")
    cat = base64.b64decode(item["category"]).decode("utf-8", errors="ignore")
    return html.unescape(q), html.unescape(a), cat

def fetch_restcountries_capital_question(diff_key: str):
    """Difficulty-aware capital questions using REST Countries."""
    data = get_json("https://restcountries.com/v3.1/all?fields=name,capital,cca2,region,population")
    if not data:
        return None, None, None
    countries = [c for c in data if isinstance(c.get("capital"), list) and c["capital"]]
    if not countries:
        return None, None, None

    # Easy whitelist of very familiar countries
    easy_whitelist = set([
        "United States", "Canada", "United Kingdom", "France", "Germany", "Italy", "Spain",
        "Japan", "Australia", "Brazil", "Mexico", "India", "China", "Russia", "South Africa",
        "Egypt", "Argentina", "Netherlands", "Sweden", "Norway", "Denmark", "Ireland"
    ])

    # Partition by population for difficulty
    def choose_easy():
        pool = [c for c in countries if c["name"].get("common") in easy_whitelist]
        if not pool:
            # fallback: populous countries > 20M
            pool = [c for c in countries if (c.get("population") or 0) >= 20_000_000]
        return random.choice(pool) if pool else random.choice(countries)

    def choose_medium():
        pool = [c for c in countries if 5_000_000 <= (c.get("population") or 0) < 20_000_000]
        if not pool:
            pool = countries
        return random.choice(pool)

    def choose_hard():
        # Less populous OR Oceania (often trickier capitals)
        pool = [c for c in countries if (c.get("population") or 0) < 5_000_000 or c.get("region") == "Oceania"]
        if not pool:
            pool = countries
        return random.choice(pool)

    def choose_expert():
        # Very small populations or remote regions (Caribbean, Oceania)
        pool = [c for c in countries if (c.get("population") or 0) < 1_000_000 or c.get("region") in ("Oceania", "Americas")]
        if not pool:
            pool = countries
        return random.choice(pool)

    if diff_key == "easy":
        c = choose_easy()
    elif diff_key == "medium":
        c = choose_medium()
    elif diff_key == "hard":
        c = choose_hard()
    else:  # expert
        c = choose_expert()

    country = c["name"].get("common", "this country")
    capital = c["capital"][0]
    q = f"What is the capital of {country}?"
    return q, capital, "Geography (Capitals)"

def fetch_wikipedia_fact_question(diff_key: str):
    """Difficulty-tuned fact questions; we verify topic exists via Wikipedia summary."""
    pools = {
        "easy": [
            ("Mitochondrion", "Science (Biology)", "What organelle is the 'powerhouse' of the cell?", "Mitochondrion"),
            ("Water", "Science", "What is the chemical formula for water?", "H₂O"),
            ("Abraham Lincoln", "History (US)", "Which U.S. president delivered the Gettysburg Address?", "Abraham Lincoln"),
        ],
        "medium": [
            ("Photosynthesis", "Science (Biology)", "In plants, what gas is taken in during photosynthesis?", "Carbon dioxide"),
            ("Magna Carta", "History (World)", "The Magna Carta was sealed under King John in which century?", "13th century"),
            ("Periodic table", "Science (Chemistry)", "Who arranged elements by atomic number in the modern periodic table? (Last name)", "Moseley"),
        ],
        "hard": [
            ("General relativity", "Science (Physics)", "Which scientist proposed general relativity? (Last name)", "Einstein"),
            ("Abyssinia", "History/Geography", "Which modern country was historically known as Abyssinia?", "Ethiopia"),
            ("Alexander von Humboldt", "History/Science", "Prussian naturalist called the 'father of modern geography'?", "Alexander von Humboldt"),
        ],
        "expert": [
            ("Yamoussoukro", "Geography/History", "Which country has Yamoussoukro as its political capital?", "Côte d'Ivoire"),
            ("Ngerulmud", "Geography", "Ngerulmud is the capital of which island nation?", "Palau"),
            ("Sri Jayawardenepura Kotte", "Geography", "What is Sri Lanka’s legislative capital city called?", "Sri Jayawardenepura Kotte"),
        ]
    }
    pool = pools.get(diff_key, pools["easy"])
    topic, cat, q, final_answer = random.choice(pool)
    resp = get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}")
    if not resp or resp.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None, None, None
    return q, final_answer, cat

MUSIC_SNIPPETS = [
    ("Amazing grace, how sweet the sound", "Amazing Grace", "Traditional"),
    ("Twinkle, twinkle, little star, how I wonder", "Twinkle, Twinkle, Little Star", "Traditional"),
    ("Happy birthday to you, happy birthday to you", "Happy Birthday to You", "Traditional"),
    ("You can call me queen bee, and baby I'll rule", "Royals", "Lorde"),
    ("Is this the real life, is this just fantasy", "Bohemian Rhapsody", "Queen"),
    ("Hello from the other side, I must have", "Hello", "Adele"),
    ("Cause baby you're a firework, come on, show 'em", "Firework", "Katy Perry"),
]

def get_music_lyrics_question():
    lyr, song, artist = random.choice(MUSIC_SNIPPETS)
    q = f"Music — Name That Song:\n“{lyr} …”  • Name the song and artist."
    a = f"{song} — {artist}"
    return q, a, "Music (Lyrics ≤10 words)"

def get_crossword_question(diff_key: str):
    easy_items = [
        ("Opposite of ‘yin’ (4).", "YANG"),
        ("French 'yes' (3).", "OUI"),
        ("Unit of electrical resistance (3).", "OHM"),
        ("Greek letter after alpha (4).", "BETA"),
        ("Ocean-warming pattern; ignore diacritics (6).", "ELNINO"),
    ]
    hard_items = [
        ("Shakespearean 'before' (3).", "ERE"),
        ("Prefix meaning 'earth' (3).", "GEO"),
        ("Church recess (4).", "APSE"),
        ("Long heroic poem (4).", "EPIC"),
        ("Tree resin (4).", "AMBER"),
    ]
    pool = easy_items if diff_key in ("easy", "medium") else hard_items
    clue, ans = random.choice(pool)
    return f"Crossword-style clue: {clue}", ans, "Crossword"

def pick_generator(difficulty_label: str):
    """Pick a generator aligned to difficulty; only changes on 'New Question' press."""
    diff_key = DIFF_MAP.get(difficulty_label, "easy")
    diff_api = map_to_trivia_api(difficulty_label)

    # Build difficulty-aligned pools
    if diff_key == "easy":
        generators = [
            lambda: fetch_opentdb_question("easy", None),
            lambda: fetch_restcountries_capital_question("easy"),
            lambda: fetch_wikipedia_fact_question("easy"),
            lambda: get_music_lyrics_question(),          # keep music for easy
            lambda: get_crossword_question("easy"),
        ]
    elif diff_key == "medium":
        generators = [
            lambda: fetch_opentdb_question("medium", None),
            lambda: fetch_restcountries_capital_question("medium"),
            lambda: fetch_wikipedia_fact_question("medium"),
            lambda: get_music_lyrics_question(),          # still ok on medium
            lambda: get_crossword_question("medium"),
        ]
    elif diff_key == "hard":
        generators = [
            lambda: fetch_opentdb_question("hard", None),
            lambda: fetch_restcountries_capital_question("hard"),
            lambda: fetch_wikipedia_fact_question("hard"),
            lambda: get_crossword_question("hard"),       # no music to avoid easy giveaways
        ]
    else:  # expert
        generators = [
            lambda: fetch_opentdb_question("hard", None),  # API max
            lambda: fetch_restcountries_capital_question("expert"),
            lambda: fetch_wikipedia_fact_question("expert"),
            lambda: get_crossword_question("expert"),
        ]

    random.shuffle(generators)
    for g in generators:
        q, a, c = g()
        if q and a:
            return q, a, c
    return ("Couldn't fetch a question right now. Check your internet and try again.", "—", "Error")

# -------------------------------
# STATE
# -------------------------------
if "qa" not in st.session_state:
    st.session_state.qa = None
if "revealed" not in st.session_state:
    st.session_state.revealed = False

# -------------------------------
# HEADER
# -------------------------------
top_l, top_r = st.columns([4, 2], gap="large")
with top_l:
    st.markdown("<div class='app-title'>TriviaBot</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>One question at a time. Choose difficulty and press New Question.</div>", unsafe_allow_html=True)

with top_r:
    with st.container():
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("**Settings**")
        difficulty = st.radio("Difficulty", DIFF_LABELS, index=0, help="Baby Barbara (easy) → PhD Pat (expert).")
        if st.button("🔁 New Question", use_container_width=True, type="primary"):
            st.session_state.qa = pick_generator(difficulty)
            st.session_state.revealed = False
        st.markdown("<div class='muted'>Sources: OpenTriviaDB, Wikipedia REST, REST Countries. Lyrics are public-domain or ≤10 words.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Initialize first question once
if st.session_state.qa is None:
    st.session_state.qa = pick_generator("Baby Barbara")

q, a, cat = st.session_state.qa if st.session_state.qa else ("", "", "")

st.markdown("<div class='spacer-8'></div>", unsafe_allow_html=True)

# -------------------------------
# QUESTION CARD
# -------------------------------
st.markdown("<div class='question-card'>", unsafe_allow_html=True)
st.markdown(f"<div class='category'>{html.escape(cat)} <span class='badge'>{html.escape(difficulty)}</span></div>", unsafe_allow_html=True)
st.markdown(f"<div class='question-text'>{html.escape(q).replace('\\n','<br>')}</div>", unsafe_allow_html=True)

if st.button("👀 Reveal Answer", key="reveal_btn"):
    st.session_state.revealed = True

if st.session_state.revealed:
    st.markdown("<div class='answer-box'>", unsafe_allow_html=True)
    st.markdown(f"**Answer:** {html.escape(a)}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='spacer-16'></div>", unsafe_allow_html=True)
st.caption("Difficulty now directly controls generators: easy = familiar/populous capitals + easier facts; expert = obscure capitals and tougher facts, with OpenTriviaDB at its 'hard' ceiling.")
