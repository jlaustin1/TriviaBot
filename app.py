
import streamlit as st
import requests
import random
import html
from typing import Dict, Tuple

st.set_page_config(page_title="TriviaBot", page_icon="🤖", layout="wide")

# -------------------------------
# THEME & STYLES (Gestalt: hierarchy, proximity, similarity)
# -------------------------------
PRIMARY_BG = "#0f172a"   # slate-900
CARD_BG    = "#111827"   # gray-900
TEXT_COL   = "#e5e7eb"   # gray-200
MUTED_COL  = "#94a3b8"   # slate-400
ACCENT     = "#f59e0b"   # amber-500
LINK_COL   = "#93c5fd"   # blue-300
OK_COL     = "#22c55e"   # green-500

CUSTOM_CSS = f"""
<style>
  .stApp {{
    background: {PRIMARY_BG};
    color: {TEXT_COL};
  }}
  .app-title {{
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 800;
    letter-spacing: 0.2px;
    margin: 0 0 8px 0;
  }}
  .subtitle {{
    color: {MUTED_COL};
    margin-bottom: 18px;
  }}
  .panel {{
    background: {CARD_BG};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 16px 16px;
  }}
  .question-card {{
    background: {CARD_BG};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px;
  }}
  .badge {{
    display: inline-block;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    color: {MUTED_COL};
    margin-left: 8px;
  }}
  .category {{
    font-size: 22px;      /* larger category font */
    font-weight: 700;
    margin-bottom: 6px;
  }}
  .question-text {{
    font-size: 20px;
    line-height: 1.5;
    margin-top: 6px;
  }}
  .answer-box {{
    background: rgba(255,255,255,0.04);
    border: 1px dashed rgba(255,255,255,0.15);
    padding: 14px;
    border-radius: 12px;
    margin-top: 10px;
  }}
  .muted {{ color: {MUTED_COL}; }}
  a, .stMarkdown a {{ color: {LINK_COL}; }}
  .spacer-8 {{ height: 8px; }}
  .spacer-12 {{ height: 12px; }}
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
    "PhD Pat": "expert"  # map to hard for APIs lacking expert
}

def map_to_trivia_api(diff_label: str) -> str:
    d = DIFF_MAP.get(diff_label, "easy")
    return "hard" if d == "expert" else d

# -------------------------------
# HELPERS
# -------------------------------
def get_json(url: str, params: Dict = None, timeout: int = 12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_opentdb_question(difficulty: str, category: int = None):
    params = {"amount": 1, "type": "multiple", "encode": "base64"}
    if difficulty in ("easy", "medium", "hard"):
        params["difficulty"] = difficulty
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

def fetch_restcountries_capital_question():
    data = get_json("https://restcountries.com/v3.1/all?fields=name,capital,cca2,region,population")
    if not data:
        return None, None, None
    choices = [c for c in data if isinstance(c.get("capital"), list) and c["capital"]]
    c = random.choice(choices)
    country = c["name"].get("common", "this country")
    capital = c["capital"][0]
    q = f"What is the capital of {country}?"
    return q, capital, "Geography (Capitals)"

def fetch_wikipedia_fact_question(diff_key: str):
    pools = {
        "easy": [
            ("Mitochondrion", "Science (Biology)", "What cell organelle is often called the 'powerhouse' of the cell?", "Mitochondrion"),
            ("Water", "Science", "What is the chemical formula for water?", "H₂O"),
            ("Abraham Lincoln", "History (US)", "Which U.S. president delivered the Gettysburg Address?", "Abraham Lincoln"),
        ],
        "medium": [
            ("Photosynthesis", "Science (Biology)", "In plants, what gas is taken in during photosynthesis?", "Carbon dioxide"),
            ("Magna Carta", "History (World)", "The Magna Carta was sealed under King John in which century?", "13th century"),
            ("Periodic table", "Science (Chemistry)", "Who arranged elements by atomic number in the modern periodic table? (Last name)", "Moseley"),
        ],
        "hard": [
            ("General relativity", "Science (Physics)", "Which scientist proposed the theory of general relativity? (Last name)", "Einstein"),
            ("Abyssinia", "History/Geography", "Which modern country was historically known as Abyssinia?", "Ethiopia"),
            ("Alexander von Humboldt", "History/Science", "Which Prussian naturalist is called the 'father of modern geography'?", "Alexander von Humboldt"),
        ],
    }
    pool = pools["hard"] if diff_key == "expert" else pools.get(diff_key, pools["easy"])
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
    items = [
        ("Opposite of ‘yin’ (4).", "YANG"),
        ("French 'yes' (3).", "OUI"),
        ("Unit of electrical resistance (3).", "OHM"),
        ("Greek letter after alpha (4).", "BETA"),
        ("Ocean-warming pattern; ignore diacritics (6).", "ELNINO"),
    ]
    if diff_key in ("hard", "expert"):
        items += [
            ("Shakespearean 'before' (3).", "ERE"),
            ("Prefix meaning 'earth' (3).", "GEO"),
        ]
    clue, ans = random.choice(items)
    return f"Crossword-style clue: {clue}", ans, "Crossword"

def pick_generator(difficulty_label: str):
    """Choose a generator. Only change the question when the NEW QUESTION button is pressed."""
    diff_api = map_to_trivia_api(difficulty_label)
    # Compose generators (Gestalt principle: consistency of structure)
    if diff_api == "easy":
        generators = [
            lambda: fetch_opentdb_question("easy", None),
            lambda: fetch_restcountries_capital_question(),
            lambda: get_music_lyrics_question(),
            lambda: get_crossword_question("easy"),
        ]
    elif diff_api == "medium":
        generators = [
            lambda: fetch_opentdb_question("medium", None),
            lambda: fetch_restcountries_capital_question(),
            lambda: fetch_wikipedia_fact_question("medium"),
            lambda: get_music_lyrics_question(),
            lambda: get_crossword_question("medium"),
        ]
    else:  # hard/expert
        key = "expert" if difficulty_label == "PhD Pat" else "hard"
        generators = [
            lambda: fetch_opentdb_question(diff_api, None),
            lambda: fetch_restcountries_capital_question(),
            lambda: fetch_wikipedia_fact_question(key),
            lambda: get_music_lyrics_question(),
            lambda: get_crossword_question(key),
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
    st.markdown("<div class='subtitle'>One question at a time. Refresh for a new one when you're ready.</div>", unsafe_allow_html=True)

with top_r:
    with st.container():
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("**Settings**")
        difficulty = st.radio("Difficulty", ["Baby Barbara", "Average Joe", "College Carl", "PhD Pat"], index=0, help="Baby Barbara (easy) → PhD Pat (expert).")
        # Single primary CTA: New Question (only one exists in the UI)
        if st.button("🔁 New Question", use_container_width=True, type="primary"):
            st.session_state.qa = pick_generator(difficulty)
            st.session_state.revealed = False
        st.markdown("<div class='muted'>Web sources used at runtime: OpenTriviaDB, Wikipedia REST, REST Countries.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Initialize first question only once (do NOT change on reveal)
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

# Single reveal button – does not generate a new question
if st.button("👀 Reveal Answer", key="reveal_btn"):
    st.session_state.revealed = True

# Answer area – revealed only when requested
if st.session_state.revealed:
    st.markdown("<div class='answer-box'>", unsafe_allow_html=True)
    st.markdown(f"**Answer:** {html.escape(a)}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='spacer-16'></div>", unsafe_allow_html=True)
st.caption("Tip: Keep the question and answer grouped (proximity), a single primary action (New Question) to reduce confusion, and clear hierarchy with a larger category label.")

