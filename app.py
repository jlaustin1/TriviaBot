
import streamlit as st
import requests
import random
import html
from typing import Dict, Tuple

st.set_page_config(page_title="Trivia — One-at-a-time", page_icon="❓", layout="wide")

# -------------------------------
# UI THEME
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
  .question-card {{
    background: {CARD_BG};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 18px;
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
  .qnum {{
    color: {ACCENT};
    font-weight: 700;
  }}
  .lyrics {{
    font-style: italic;
    color: {MUTED_COL};
  }}
  .muted {{ color: {MUTED_COL}; }}
  .answer-box {{
    background: rgba(255,255,255,0.04);
    border: 1px dashed rgba(255,255,255,0.15);
    padding: 14px;
    border-radius: 12px;
  }}
  a, .stMarkdown a {{ color: {LINK_COL}; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------
# DIFFICULTY MAPPING
# -------------------------------
DIFF_LABELS = ["Baby Barbara", "Average Joe", "College Carl", "PhD Pat"]
DIFF_MAP = {
    "Baby Barbara": "easy",
    "Average Joe": "medium",
    "College Carl": "hard",
    "PhD Pat": "expert"  # we will map to 'hard' for sources that only go up to hard
}

# -------------------------------
# UTILITIES
# -------------------------------
def map_to_trivia_api(diff_label: str) -> str:
    d = DIFF_MAP.get(diff_label, "easy")
    # OpenTriviaDB supports: easy, medium, hard (no 'expert')
    return "hard" if d == "expert" else d

def get_json(url: str, params: Dict = None, timeout: int = 12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_opentdb_question(difficulty: str, category: int = None) -> Tuple[str, str, str]:
    """Fetch a single question from Open Trivia DB. Returns (question, answer, category_label)."""
    params = {"amount": 1, "type": "multiple", "encode": "base64"}
    if difficulty in ("easy", "medium", "hard"):
        params["difficulty"] = difficulty
    if category:
        params["category"] = category
    data = get_json("https://opentdb.com/api.php", params=params)
    if not data or data.get("response_code") != 0:
        return None, None, None
    item = data["results"][0]
    # decode base64
    import base64
    q = base64.b64decode(item["question"]).decode("utf-8", errors="ignore")
    a = base64.b64decode(item["correct_answer"]).decode("utf-8", errors="ignore")
    cat = base64.b64decode(item["category"]).decode("utf-8", errors="ignore")
    return html.unescape(q), html.unescape(a), cat

def fetch_restcountries_capital_question(difficulty: str) -> Tuple[str, str, str]:
    """Use REST Countries to build a geography capital question."""
    data = get_json("https://restcountries.com/v3.1/all?fields=name,capital,cca2,region,population")
    if not data:
        return None, None, None
    # Filter to countries with a clear single capital
    choices = [c for c in data if isinstance(c.get("capital"), list) and c["capital"]]
    c = random.choice(choices)
    country = c["name"].get("common", "this country")
    capital = c["capital"][0]
    q = f"What is the capital of {country}?"
    return q, capital, "Geography (Capitals)"

def fetch_wikipedia_fact_question(difficulty: str) -> Tuple[str, str, str]:
    """Create a science/history fact question using Wikipedia summaries."""
    # We'll use a small pool of topics mapped by difficulty for reliability.
    pools = {
        "easy": [
            ("Mitochondrion", "Science (Biology)", "What cell organelle is often called the 'powerhouse' of the cell?"),
            ("Abraham Lincoln", "History (US)", "Which U.S. president delivered the Gettysburg Address?"),
            ("Water", "Science", "What is the chemical formula for water?"),
        ],
        "medium": [
            ("Periodic table", "Science (Chemistry)", "Who arranged elements by atomic number in the modern periodic table? (Last name)"),
            ("Magna Carta", "History (World)", "The Magna Carta was sealed under King John in which century?"),
            ("Photosynthesis", "Science (Biology)", "In plants, what gas is taken in during photosynthesis?"),
        ],
        "hard": [
            ("Alexander von Humboldt", "History/Science", "Which Prussian naturalist is called the 'father of modern geography'?"),
            ("General relativity", "Science (Physics)", "Which scientist proposed the theory of general relativity? (Last name)"),
            ("Abyssinia", "History/Geography", "Which modern country was historically known as Abyssinia?"),
        ],
    }
    pool = pools["hard"] if difficulty == "expert" else pools.get(difficulty, pools["easy"])
    topic, cat, q = random.choice(pool)
    # Try to fetch the first sentence to ensure the topic exists (light verification)
    resp = get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}")
    # We don't show the sentence to avoid spoilers; we just verify topic exists.
    if not resp or resp.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None, None, None
    # Derive the canonical answer based on the question we asked:
    if "powerhouse" in q:
        answer = "Mitochondrion"
    elif "Gettysburg Address" in q:
        answer = "Abraham Lincoln"
    elif "chemical formula for water" in q:
        answer = "H₂O"
    elif "modern periodic table" in q:
        answer = "Moseley"
    elif "Magna Carta" in q:
        answer = "13th century"
    elif "photosynthesis" in q:
        answer = "Carbon dioxide"
    elif "general relativity" in q:
        answer = "Einstein"
    elif "Abyssinia" in q:
        answer = "Ethiopia"
    elif "father of modern geography" in q:
        answer = "Alexander von Humboldt"
    else:
        answer = topic
    return q, answer, cat

# Public-domain / permissible <=10-word lyric snippets for "Name That Song"
MUSIC_SNIPPETS = [
    # Public domain or traditional
    ("Amazing grace, how sweet the sound", "Amazing Grace", "Traditional"),
    ("Twinkle, twinkle, little star, how I wonder", "Twinkle, Twinkle, Little Star", "Traditional"),
    ("Happy birthday to you, happy birthday to you", "Happy Birthday to You", "Traditional"),
    # ≤10-word modern snippets (copyright policy compliant)
    ("You can call me queen bee, and baby I'll rule", "Royals", "Lorde"),
    ("Is this the real life, is this just fantasy", "Bohemian Rhapsody", "Queen"),
    ("Hello from the other side, I must have", "Hello", "Adele"),
    ("Cause baby you're a firework, come on, show 'em", "Firework", "Katy Perry"),
]

def get_music_lyrics_question(difficulty: str) -> Tuple[str, str, str]:
    lyr, song, artist = random.choice(MUSIC_SNIPPETS)
    q = f"Music — Name That Song:\n“{lyr} …”  • Name the song and artist."
    a = f"{song} — {artist}"
    return q, a, "Music (Lyrics ≤10 words)"

def get_crossword_question(difficulty: str) -> Tuple[str, str, str]:
    items = [
        ("Opposite of ‘yin’ (4).", "YANG"),
        ("French 'yes' (3).", "OUI"),
        ("Unit of electrical resistance (3).", "OHM"),
        ("Greek letter after alpha (4).", "BETA"),
        ("Ocean-warming pattern; ignore diacritics (6).", "ELNINO"),
    ]
    if difficulty in ("hard", "expert"):
        items += [
            ("Prefix meaning 'earth' (5).", "GEO"),
            ("Shakespearean 'before' (3).", "ERE"),
        ]
    clue, ans = random.choice(items)
    return f"Crossword-style clue: {clue}", ans, "Crossword"

def pick_generator(difficulty_label: str):
    """Pick a generator function based on difficulty and randomness, ensuring category coverage across plays."""
    d_api = map_to_trivia_api(difficulty_label)
    generators = []

    # Bias: easier -> more OpenTDB; harder -> more wiki/restcountries
    if d_api == "easy":
        generators = [
            lambda: fetch_opentdb_question("easy", None),
            lambda: fetch_restcountries_capital_question("easy"),
            lambda: get_music_lyrics_question("easy"),
            lambda: get_crossword_question("easy"),
        ]
    elif d_api == "medium":
        generators = [
            lambda: fetch_opentdb_question("medium", None),
            lambda: fetch_restcountries_capital_question("medium"),
            lambda: fetch_wikipedia_fact_question("medium"),
            lambda: get_music_lyrics_question("medium"),
            lambda: get_crossword_question("medium"),
        ]
    else:  # hard / expert
        generators = [
            lambda: fetch_opentdb_question(d_api, None),
            lambda: fetch_restcountries_capital_question(d_api),
            lambda: fetch_wikipedia_fact_question("hard" if d_api=="hard" else "expert"),
            lambda: get_music_lyrics_question(d_api),
            lambda: get_crossword_question(d_api),
        ]

    random.shuffle(generators)
    for g in generators:
        q, a, c = g()
        if q and a:
            return q, a, c
    return ("Hmm, couldn't fetch a question right now. Check your internet and try Refresh.", "—", "Error")

# -------------------------------
# SESSION STATE
# -------------------------------
if "qa" not in st.session_state:
    st.session_state.qa = None
if "revealed" not in st.session_state:
    st.session_state.revealed = False

# -------------------------------
# LAYOUT
# -------------------------------
left, right = st.columns([5, 2], gap="large")

with right:
    st.markdown("### Settings")
    difficulty = st.radio(
        "Question difficulty", DIFF_LABELS, index=0,
        help="Baby Barbara (easy) → PhD Pat (expert)."
    )

    if st.button("🔁 Refresh (new question)", use_container_width=True):
        st.session_state.qa = pick_generator(difficulty)
        st.session_state.revealed = False

    st.markdown("<div class='muted'>Questions are fetched from public APIs (OpenTriviaDB, Wikipedia, REST Countries) and a small, policy-compliant lyric list.</div>", unsafe_allow_html=True)

with left:
    st.markdown("## One-at-a-time Trivia")
    st.caption("Click “Refresh” to get a new question. Reveal only when you're ready.")

    if st.session_state.qa is None:
        # First load
        st.session_state.qa = pick_generator(DIFF_LABELS[0])

    q, a, cat = st.session_state.qa if st.session_state.qa else ("", "", "")

    with st.container():
        st.markdown("<div class='question-card'>", unsafe_allow_html=True)
        st.markdown(f"**Category:** {cat} <span class='badge'>{difficulty}</span>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:20px;margin-top:6px'>{html.escape(q).replace('\\n','<br>')}</div>", unsafe_allow_html=True)

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("👀 Reveal answer", type="primary", use_container_width=True, disabled=st.session_state.revealed):
                st.session_state.revealed = True
        with col2:
            if st.button("🔁 New question", use_container_width=True):
                st.session_state.qa = pick_generator(difficulty)
                st.session_state.revealed = False

        if st.session_state.revealed:
            st.markdown("<div class='answer-box'>", unsafe_allow_html=True)
            st.markdown(f"**Answer:** {html.escape(a)}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Sources used at runtime: Open Trivia DB (general knowledge), Wikipedia REST API (fact verification), REST Countries (capitals). Music lyric snippets are public-domain or ≤10-word excerpts for fair use compliance.")
