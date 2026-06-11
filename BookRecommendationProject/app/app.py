import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import requests
import plotly.express as px
import ast

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("E-MoXion 📚🧠")

# =========================
# DATA
# =========================
df_final = pd.read_csv("../books.csv")

os.makedirs("data", exist_ok=True)
PATH = "data/journal.csv"

if not os.path.exists(PATH):
    pd.DataFrame(columns=[
        "date", "emotion", "text", "book", "reflection",
        "change", "note", "book_scores"
    ]).to_csv(PATH, index=False)

journal = pd.read_csv(PATH)

# =========================
# EMOTION MAP
# =========================
emotion_map = {
    "sad": ["happy", "joy", "uplifting"],
    "anxious": ["calm", "peace", "relax"],
    "low energy": ["motivation", "energy"],
    "angry": ["peace", "forgiveness"],
    "lost": ["clarity", "purpose"],
    "stressed": ["calm", "balance"],
    "neutral": ["self help", "growth"]
}

def map_emotion(text):
    text = str(text).lower()
    for k, v in emotion_map.items():
        if any(w in text for w in v):
            return k
    return "neutral"

# =========================
# BOOK COVER
# =========================
@st.cache_data
def get_book_cover(row):
    title = str(row.get("title", "")).strip()

    try:
        res = requests.get(
            "https://openlibrary.org/search.json",
            params={"title": title},
            timeout=5
        )
        data = res.json()
        docs = data.get("docs", [])
        if docs and docs[0].get("cover_i"):
            return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-M.jpg"
    except:
        pass

    return "https://via.placeholder.com/120x180?text=No+Cover"

# =========================
# GARDNER MODEL
# =========================
def book_to_gardner(row):
    text = (
        str(row.get("title", "")) + " " +
        str(row.get("description", "")) + " " +
        str(row.get("subjects", "")).lower()
    )

    return {
        "Linguistic": 2 if any(k in text for k in ["writing", "language", "story", "book"]) else 0,
        "Logical-Mathematical": 2 if any(k in text for k in ["logic", "strategy", "problem", "analysis"]) else 0,
        "Spatial": 2 if any(k in text for k in ["design", "visual", "space"]) else 0,
        "Bodily-Kinesthetic": 2 if any(k in text for k in ["habit", "practice", "action", "exercise"]) else 0,
        "Musical": 2 if any(k in text for k in ["music", "sound", "rhythm"]) else 0,
        "Interpersonal": 2 if any(k in text for k in ["communication", "leadership", "relationship"]) else 0,
        "Intrapersonal": 2 if any(k in text for k in ["psychology", "self", "mindfulness", "emotion"]) else 0,
    }

# =========================
# CLIFTON MODEL
# =========================
def book_to_strengths(row):
    text = (
        str(row.get("title", "")) + " " +
        str(row.get("description", "")) + " " +
        str(row.get("subjects", "")).lower()
    )

    return {
        "Achiever": 2 if any(k in text for k in ["success", "productivity", "habit"]) else 0,
        "Strategic Thinking": 2 if any(k in text for k in ["strategy", "thinking", "decision"]) else 0,
        "Communication": 2 if any(k in text for k in ["communication", "writing", "speaking"]) else 0,
        "Empathy": 2 if any(k in text for k in ["emotion", "relationship", "psychology"]) else 0,
        "Learning": 2 if any(k in text for k in ["learning", "knowledge", "education"]) else 0,
    }

# =========================
# RECOMMENDER
# =========================
def recommend_books(df, emotion, page=1, page_size=10):
    df = df.copy()

    text = (
        df["title"].fillna("") + " " +
        df["description"].fillna("") + " " +
        df["subjects"].astype(str)
    ).str.lower()

    keywords = emotion_map.get(emotion, [])

    df["score"] = text.apply(lambda t: sum(k in t for k in keywords))
    df = df[df["score"] > 0].sort_values("score", ascending=False)

    start = (page - 1) * page_size
    end = start + page_size

    return df.iloc[start:end]

# =========================
# SESSION STATE
# =========================
if "selected_day" not in st.session_state:
    st.session_state.selected_day = datetime.now().strftime("%Y-%m-%d")

# =========================
# CALENDAR
# =========================
st.subheader("Calendar")

today = datetime.now()
days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

cols = st.columns(7)

for i, d in enumerate(days):
    if cols[i].button(d[-2:], key=f"day_{d}"):
        st.session_state.selected_day = d

st.write(f"📅 Selected: {st.session_state.selected_day}")

note = st.text_area("Add note for this day")

# =========================
# LAYOUT
# =========================
left, right = st.columns([1.2, 2.8])

# =========================
# LEFT PANEL
# =========================
with left:

    st.subheader("Emotion Panel")

    emotion_text = st.text_area("How do you feel today?", height=120)

    emotion = st.selectbox(
        "Emotion",
        options=list(emotion_map.keys()),
        index=list(emotion_map.keys()).index(map_emotion(emotion_text))
    )

    selected_book = st.selectbox(
        "What did you read?",
        options=df_final["title"].dropna().unique()
    )

    book_row = df_final[df_final["title"] == selected_book].iloc[0]

    gardner_scores = book_to_gardner(book_row)

    st.markdown("### 📘 Book Preview")
    col1, col2 = st.columns([1, 3])

    with col1:
        st.image(get_book_cover(book_row), width=120)

    with col2:
        st.write(str(book_row["description"])[:250])

    st.markdown("### 🧠 Gardner Impact")
    for k, v in gardner_scores.items():
        st.write(f"{k}: +{v}")

    reflection = st.text_area("Reflection")
    change = st.text_area("Change")

    if st.button("Save Entry"):

        new = {
            "date": st.session_state.selected_day,
            "emotion": emotion,
            "text": emotion_text,
            "book": selected_book,
            "reflection": reflection,
            "change": change,
            "note": note,
            "book_scores": str(gardner_scores)
        }

        journal = pd.concat([journal, pd.DataFrame([new])], ignore_index=True)
        journal.to_csv(PATH, index=False)

        st.success("Saved successfully")

# =========================
# RIGHT PANEL
# =========================
with right:

    st.subheader("Recommended Books")

    recs = recommend_books(df_final, emotion)

    for _, row in recs.iterrows():
        c1, c2 = st.columns([1, 4])

        with c1:
            st.image(get_book_cover(row), width=80)

        with c2:
            st.markdown(f"### {row['title']}")
            st.write(str(row["description"])[:180])

# =========================
# DASHBOARD
# =========================
st.markdown("---")
st.header("📊 Gardner + Strengths Profile")

def build_dashboard(journal_df):

    gardner = {
        "Linguistic": 0,
        "Logical-Mathematical": 0,
        "Spatial": 0,
        "Bodily-Kinesthetic": 0,
        "Musical": 0,
        "Interpersonal": 0,
        "Intrapersonal": 0
    }

    strengths = {
        "Achiever": 0,
        "Strategic Thinking": 0,
        "Communication": 0,
        "Empathy": 0,
        "Learning": 0
    }

    for _, row in journal_df.iterrows():
        try:
            scores = ast.literal_eval(row.get("book_scores", "{}"))
            for k in gardner:
                gardner[k] += scores.get(k, 0)
        except:
            pass

    for _, row in df_final.iterrows():
        g = book_to_gardner(row)
        s = book_to_strengths(row)

        for k in gardner:
            gardner[k] += g[k]

        for k in strengths:
            strengths[k] += s[k]

    return gardner, strengths

g, s = build_dashboard(journal)

st.subheader("🧠 Gardner Intelligences")

fig1 = px.pie(names=list(g.keys()), values=list(g.values()),
              title="Cognitive Intelligence (Gardner)")

st.plotly_chart(fig1, use_container_width=True)

st.subheader("💪 Clifton Strengths")

fig2 = px.bar(x=list(s.keys()), y=list(s.values()),
              title="Strength Profile")

st.plotly_chart(fig2, use_container_width=True)