"""
NewsLense -- Streamlit frontend.

Run with:  streamlit run app.py
"""

import json
import os

import streamlit as st
import streamlit.components.v1 as components

from newslense import (
    FRAMING_COLORS,
    aggregate_framing_words,
    analyze_all,
    fetch_all_articles,
    find_all_urls,
    generate_takeaway,
    highlight_text,
    outlets,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="NewsLense",
    page_icon="logo.png" if os.path.exists("logo.png") else None,
    layout="wide",
)

CYAN = "#4fd8ff"
PINK = "#ff3d8a"

# ---------------------------------------------------------------------------
# Global styling (CSS only -- safe inside st.markdown). Drifting background
# blobs, card/chip entrance + hover motion, mobile breakpoint.
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(16px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes gradientShift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        @keyframes floatLogo {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-6px); }}
        }}
        @keyframes pulseBorder {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(79,216,255,0.0), 0 0 0 0 rgba(255,61,138,0.0); }}
            50% {{ box-shadow: 0 0 18px 1px rgba(79,216,255,0.18), 0 0 18px 1px rgba(255,61,138,0.12); }}
        }}
        @keyframes blobDrift1 {{
            0%, 100% {{ transform: translate(0px, 0px) scale(1); }}
            50% {{ transform: translate(60px, 40px) scale(1.15); }}
        }}
        @keyframes blobDrift2 {{
            0%, 100% {{ transform: translate(0px, 0px) scale(1); }}
            50% {{ transform: translate(-50px, -30px) scale(1.1); }}
        }}

        .stApp {{
            background: #07070b;
            color: #f2f2f6;
        }}
        .nl-blob {{
            position: fixed;
            border-radius: 50%;
            filter: blur(90px);
            opacity: 0.22;
            z-index: 0;
            pointer-events: none;
        }}
        .nl-blob-cyan {{
            top: -120px; left: -100px; width: 420px; height: 420px;
            background: {CYAN};
            animation: blobDrift1 14s ease-in-out infinite;
        }}
        .nl-blob-pink {{
            bottom: -140px; right: -100px; width: 460px; height: 460px;
            background: {PINK};
            animation: blobDrift2 16s ease-in-out infinite;
        }}

        [data-testid="stMarkdownContainer"] a.anchor-link {{ display: none !important; }}

        .nl-logo-wrap {{ animation: floatLogo 4s ease-in-out infinite; position: relative; z-index: 1; }}

        .nl-title {{
            font-size: 3.8rem !important;
            font-weight: 800 !important;
            background: linear-gradient(90deg, {CYAN}, #f2f2f6 45%, {PINK}, {CYAN});
            background-size: 300% 100%;
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin: 0;
            animation: gradientShift 6s ease-in-out infinite;
            position: relative;
            z-index: 1;
        }}

        .nl-section-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: #e8e8ee;
            margin: 10px 0 14px 0;
            position: relative;
            z-index: 1;
        }}
        .nl-section-title::before {{
            content: "";
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: linear-gradient(90deg, {CYAN}, {PINK});
            margin-right: 8px;
        }}

        .nl-takeaway {{
            background: linear-gradient(90deg, rgba(79,216,255,0.12), rgba(255,61,138,0.12));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 16px 20px;
            font-size: 1.05rem;
            margin-bottom: 20px;
            animation: fadeInUp 0.5s ease both, pulseBorder 3.5s ease-in-out infinite;
            position: relative;
            z-index: 1;
        }}
        .nl-takeaway strong {{
            background: linear-gradient(90deg, {CYAN}, {PINK});
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}

        .nl-quiet-note {{
            color: #767680;
            font-size: 0.8rem;
            margin: -8px 0 18px 2px;
            position: relative;
            z-index: 1;
        }}

        .nl-cache-note {{
            display: inline-block;
            font-size: 0.78rem;
            color: {CYAN};
            border: 1px solid rgba(79,216,255,0.3);
            border-radius: 999px;
            padding: 3px 12px;
            margin-bottom: 16px;
            position: relative;
            z-index: 1;
        }}

        .nl-headline-strip {{
            display: flex;
            gap: 14px;
            overflow-x: auto;
            padding-bottom: 6px;
            margin-bottom: 26px;
            position: relative;
            z-index: 1;
        }}
        .nl-headline-chip {{
            flex: 0 0 auto;
            min-width: 220px;
            max-width: 260px;
            background: #101017;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px 14px;
            animation: fadeInUp 0.5s ease both;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .nl-headline-chip:hover {{ transform: translateY(-3px); border-color: rgba(255,61,138,0.4); }}
        .nl-headline-outlet {{
            font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase;
            color: {CYAN}; font-weight: 700; margin-bottom: 6px;
        }}
        .nl-headline-text {{ font-size: 0.92rem; color: #e8e8ee; line-height: 1.3; }}

        .nl-article-box {{
            max-height: 340px;
            overflow-y: auto;
            background: #0b0b10;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 14px;
            font-size: 0.88rem;
            line-height: 1.55;
            color: #cfcfd8;
        }}

        div.stButton > button {{
            background: linear-gradient(90deg, {CYAN}, {PINK});
            color: #05050a;
            font-weight: 700;
            border: none;
            border-radius: 10px;
            padding: 0.55em 1.6em;
            transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
        }}
        div.stButton > button:hover {{
            opacity: 0.92; color: #05050a; transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(255,61,138,0.25);
        }}
        div.stButton > button:active {{ transform: translateY(0px) scale(0.98); }}

        section[data-testid="stSidebar"] {{
            background: #0a0a0f;
            border-right: 1px solid rgba(255,255,255,0.06);
            width: 340px !important;
        }}
        section[data-testid="stSidebar"] > div:first-child {{
            width: 340px !important;
        }}

        @media (max-width: 768px) {{
            .nl-title {{ font-size: 2.6rem !important; }}
            .nl-headline-chip {{ min-width: 170px; max-width: 190px; padding: 10px 12px; }}
            .nl-article-box {{ max-height: 220px; font-size: 0.82rem; }}
            .nl-takeaway {{ font-size: 0.92rem; padding: 12px 14px; }}
            div.stButton > button {{ width: 100%; }}
        }}
    </style>
    <div class="nl-blob nl-blob-cyan"></div>
    <div class="nl-blob nl-blob-pink"></div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero: typewriter explainer + a permanent live mini demo, as one isolated
# HTML/JS component (Streamlit strips <script> from normal markdown, so
# anything that needs real JavaScript has to run inside components.html).
# ---------------------------------------------------------------------------

HERO_HTML = """
<div id="nl-hero-root">
  <style>
    body { margin: 0; background: transparent; font-family: -apple-system, Segoe UI, Roboto, sans-serif; }
    .hero-wrap { padding: 4px 2px 10px 2px; }
    .hero-line {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f2f2f6;
        min-height: 1.6em;
        margin-bottom: 14px;
    }
    .hero-cursor { display: inline-block; width: 2px; background: #4fd8ff; margin-left: 2px; animation: blink 0.8s step-end infinite; }
    @keyframes blink { 50% { opacity: 0; } }

    .demo-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .demo-card {
        flex: 1 1 220px;
        background: #101017;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 12px 14px;
    }
    .demo-outlet { font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase; color: #9a9aa8; font-weight: 700; margin-bottom: 6px; }
    .demo-text { font-size: 0.92rem; color: #dcdce2; line-height: 1.4; }
    .demo-word {
        padding: 1px 5px;
        border-radius: 4px;
        font-weight: 700;
        animation: pulseWord 2.4s ease-in-out infinite;
    }
    .word-a { background: rgba(79,216,255,0.18); color: #4fd8ff; }
    .word-b { background: rgba(255,61,138,0.18); color: #ff3d8a; }
    @keyframes pulseWord {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,255,255,0); }
        50% { box-shadow: 0 0 10px 1px rgba(255,255,255,0.15); }
    }
    .demo-caption { font-size: 0.78rem; color: #6f6f79; margin-top: 10px; }
  </style>

  <div class="hero-wrap">
    <div class="hero-line" id="typewriter"><span id="tw-text"></span><span class="hero-cursor">&nbsp;</span></div>

    <div class="demo-row">
      <div class="demo-card">
        <div class="demo-outlet">Outlet A</div>
        <div class="demo-text">Hundreds of <span class="demo-word word-a">activists</span> gathered outside Parliament to demand climate action.</div>
      </div>
      <div class="demo-card">
        <div class="demo-outlet">Outlet B</div>
        <div class="demo-text">Hundreds of <span class="demo-word word-b">protesters</span> blocked traffic outside Parliament for hours.</div>
      </div>
    </div>
    <div class="demo-caption">Same event. Same day. Two different words doing two different jobs. NewsLense finds pairs like this automatically, across real outlets, for any topic you give it.</div>
  </div>

  <script>
    const phrases = [
      "Same story, told six different ways.",
      "One outlet says \\"activists.\\" Another says \\"protesters.\\"",
      "NewsLense reads real coverage and shows you the difference.",
      "You decide what it means. We just show the words."
    ];
    let phraseIndex = 0;
    let charIndex = 0;
    let deleting = false;
    const el = document.getElementById("tw-text");

    function tick() {
      const current = phrases[phraseIndex];
      if (!deleting) {
        charIndex++;
        el.textContent = current.slice(0, charIndex);
        if (charIndex === current.length) {
          deleting = true;
          setTimeout(tick, 1400);
          return;
        }
      } else {
        charIndex--;
        el.textContent = current.slice(0, charIndex);
        if (charIndex === 0) {
          deleting = false;
          phraseIndex = (phraseIndex + 1) % phrases.length;
        }
      }
      setTimeout(tick, deleting ? 25 : 38);
    }
    tick();
  </script>
</div>
"""

components.html(HERO_HTML, height=230, scrolling=False)

# ---------------------------------------------------------------------------
# Caching so demo topics don't depend on live scraping every time
# ---------------------------------------------------------------------------

CACHE_DIR = "cache"


def save_cache(topic, found_urls, all_articles, results):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe_name = topic.strip().lower().replace(" ", "_")
    with open(f"{CACHE_DIR}/{safe_name}.json", "w") as f:
        json.dump(
            {"topic": topic, "urls": found_urls, "articles": all_articles, "results": results},
            f,
        )


def load_cache(topic):
    safe_name = topic.strip().lower().replace(" ", "_")
    path = f"{CACHE_DIR}/{safe_name}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def list_cached_topics():
    if not os.path.exists(CACHE_DIR):
        return []
    names = []
    for fname in sorted(os.listdir(CACHE_DIR)):
        if fname.endswith(".json"):
            try:
                with open(f"{CACHE_DIR}/{fname}") as f:
                    names.append(json.load(f)["topic"])
            except Exception:
                pass
    return names


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    if os.path.exists("logo.png"):
        st.markdown('<div class="nl-logo-wrap">', unsafe_allow_html=True)
        st.image("logo.png", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="nl-section-title">Recent topics</div>', unsafe_allow_html=True)
    cached_topics = list_cached_topics()
    if cached_topics:
        for t in cached_topics:
            if st.button(t, key=f"recent-{t}", use_container_width=True):
                st.session_state["topic_input"] = t
    else:
        st.caption("Nothing analyzed yet. Your searches will appear here.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.markdown('<div class="nl-logo-wrap">', unsafe_allow_html=True)
        st.image("logo.png", width=120)
        st.markdown("</div>", unsafe_allow_html=True)
with col_title:
    st.markdown('<p class="nl-title">NewsLense</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

topic = st.text_input(
    "Enter a news topic",
    value=st.session_state.get("topic_input", "climate protest london"),
    key="topic_input",
)

analyze_clicked = st.button("Analyze")

# ---------------------------------------------------------------------------
# Run / load analysis
# ---------------------------------------------------------------------------

if analyze_clicked or "last_results" in st.session_state:
    if analyze_clicked:
        cached = load_cache(topic)
        if cached:
            found_urls = cached["urls"]
            results = cached["results"]
            st.session_state["from_cache"] = True
        else:
            with st.spinner(f"Searching {len(outlets)} outlets at once for coverage of \"{topic}\"..."):
                found_urls = find_all_urls(topic)
            with st.spinner(f"Found {len(found_urls)} articles. Reading them..."):
                all_articles = fetch_all_articles(found_urls)
            with st.spinner("Comparing word choice, framing and tone..."):
                results = analyze_all(all_articles)
            save_cache(topic, found_urls, all_articles, results)
            st.session_state["from_cache"] = False

        st.session_state["last_results"] = results
        st.session_state["last_urls"] = found_urls
        st.session_state["last_topic"] = topic
    else:
        results = st.session_state["last_results"]
        found_urls = st.session_state["last_urls"]
        topic = st.session_state["last_topic"]

    if st.session_state.get("from_cache"):
        st.markdown('<span class="nl-cache-note">Loaded from cache, instantly</span>', unsafe_allow_html=True)

    # Quiet note about outlets that failed -- small and muted, not a big banner
    missing = [name for name in outlets if name not in found_urls]
    failed_fetch = [name for name in found_urls if name not in results]
    unavailable = missing + failed_fetch
    if unavailable:
        st.markdown(
            f'<div class="nl-quiet-note">{len(results)} of {len(outlets)} outlets shown '
            f"&middot; {', '.join(unavailable)} blocked this request.</div>",
            unsafe_allow_html=True,
        )

    if not results:
        st.error("No outlets could be analyzed for this topic. Try a more specific or recent topic.")
        st.stop()

    # --- Takeaway ------------------------------------------------------
    st.markdown(f'<div class="nl-takeaway">{generate_takeaway(results)}</div>', unsafe_allow_html=True)

    # --- Word cloud of loaded words across all outlets -------------------
    combined_words = aggregate_framing_words(results)
    if combined_words:
        try:
            from io import BytesIO

            from wordcloud import WordCloud

            def color_func(word, **kwargs):
                return FRAMING_COLORS.get(word, "#f2f2f6")

            wc = WordCloud(
                width=1000,
                height=260,
                background_color=None,
                mode="RGBA",
                color_func=color_func,
                prefer_horizontal=1.0,
            ).generate_from_frequencies(combined_words)

            buf = BytesIO()
            wc.to_image().save(buf, format="PNG")
            st.markdown('<div class="nl-section-title">Loaded words across all outlets</div>', unsafe_allow_html=True)
            st.image(buf.getvalue(), use_container_width=True)
        except ImportError:
            pass  # wordcloud not installed -- skip gracefully, rest of app still works

    # --- Animated charge-score chart --------------------------------------
    try:
        import plotly.graph_objects as go

        names = list(results.keys())
        scores = [results[n]["charge_score"] for n in names]

        fig = go.Figure(
            go.Bar(
                x=scores,
                y=names,
                orientation="h",
                marker=dict(
                    color=scores,
                    colorscale=[[0, CYAN], [1, PINK]],
                    line=dict(width=0),
                ),
                text=[f"{s}/100" for s in scores],
                textposition="outside",
                textfont=dict(color="#f2f2f6"),
            )
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8e8ee"),
            margin=dict(l=10, r=10, t=10, b=10),
            height=70 + 55 * len(names),
            xaxis=dict(range=[0, 100], showgrid=False, title="Charge score"),
            yaxis=dict(autorange="reversed"),
            transition=dict(duration=500, easing="cubic-in-out"),
        )
        st.markdown('<div class="nl-section-title">Charge score comparison</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except ImportError:
        pass  # plotly not installed -- skip gracefully

    # --- Headline strip ------------------------------------------------------
    st.markdown('<div class="nl-section-title">Headlines, side by side</div>', unsafe_allow_html=True)
    chips = "".join(
        f'<div class="nl-headline-chip">'
        f'<div class="nl-headline-outlet">{name}</div>'
        f'<div class="nl-headline-text">{data["title"]}</div>'
        f"</div>"
        for name, data in results.items()
    )
    st.markdown(f'<div class="nl-headline-strip">{chips}</div>', unsafe_allow_html=True)

    # --- Per-outlet animated cards (count-up score + fill bar), one
    # isolated component since this needs real JS -----------------------
    st.markdown('<div class="nl-section-title">Full comparison</div>', unsafe_allow_html=True)

    card_payload = []
    for name, data in results.items():
        card_payload.append(
            {
                "name": name,
                "score": data["charge_score"],
                "sentiment": round(data["sentiment"], 2),
                "framing": data["framing_words"],
                "quote": data.get("example_sentence") or "",
            }
        )

    CARDS_HTML = """
    <div id="nl-cards-root">
      <style>
        body { margin: 0; background: transparent; font-family: -apple-system, Segoe UI, Roboto, sans-serif; }
        .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
        .nl-card {
            background: linear-gradient(180deg, #121219 0%, #0c0c12 100%);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.35);
            opacity: 0;
            transform: translateY(14px);
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
            animation: cardIn 0.5s ease forwards;
            box-sizing: border-box;
        }
        .nl-card:hover { transform: translateY(-4px); border-color: rgba(79,216,255,0.35); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        @keyframes cardIn { to { opacity: 1; transform: translateY(0); } }
        .nl-card-name { font-size: 1.1rem; font-weight: 800; color: #f5f5f9; margin-bottom: 10px; }
        .nl-score-track { background: #1a1a24; border-radius: 8px; overflow: hidden; height: 12px; margin: 8px 0 4px 0; }
        .nl-score-fill {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, #4fd8ff, #ff3d8a);
            transition: width 1.1s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .nl-score-label { font-size: 0.82rem; color: #9a9aa8; margin-bottom: 12px; }
        .nl-score-label strong { color: #f2f2f6; }
        .nl-framing-pill {
            display: inline-block; font-size: 0.78rem; padding: 3px 10px; border-radius: 999px;
            margin: 2px 4px 2px 0; border: 1px solid rgba(255,255,255,0.12); color: #e8e8ee;
        }
        .nl-no-framing { color: #7a7a86; font-size: 0.82rem; }
        .nl-example-quote {
            border-left: 3px solid #ff3d8a; padding: 8px 14px; margin-top: 10px;
            font-style: italic; color: #c9c9d4; font-size: 0.86rem;
        }
      </style>
      <div class="cards-grid" id="cards-grid"></div>
      <script>
        const CARD_DATA = __CARD_DATA__;
        const grid = document.getElementById("cards-grid");

        CARD_DATA.forEach((card, i) => {
          const div = document.createElement("div");
          div.className = "nl-card";
          div.style.animationDelay = (i * 0.08) + "s";

          let pillsHtml = "";
          const words = Object.entries(card.framing);
          if (words.length > 0) {
            pillsHtml = words.map(([w, c]) => `<span class="nl-framing-pill">${w}: ${c}x</span>`).join("");
          } else {
            pillsHtml = `<span class="nl-no-framing">No tracked framing words detected.</span>`;
          }

          let quoteHtml = "";
          if (card.quote) {
            quoteHtml = `<div class="nl-example-quote">"${card.quote}"</div>`;
          }

          div.innerHTML = `
            <div class="nl-card-name">${card.name}</div>
            <div class="nl-score-track"><div class="nl-score-fill" id="fill-${i}"></div></div>
            <div class="nl-score-label">Charge score: <strong id="num-${i}">0</strong>/100 &middot; Sentiment: ${card.sentiment}</div>
            ${pillsHtml}
            ${quoteHtml}
          `;
          grid.appendChild(div);

          setTimeout(() => {
            document.getElementById("fill-" + i).style.width = card.score + "%";
            const numEl = document.getElementById("num-" + i);
            let current = 0;
            const target = card.score;
            const duration = 900;
            const start = performance.now();
            function step(now) {
              const progress = Math.min((now - start) / duration, 1);
              current = Math.round(progress * target);
              numEl.textContent = current;
              if (progress < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
          }, 120 + i * 80);
        });
      </script>
    </div>
    """.replace("__CARD_DATA__", json.dumps(card_payload))

    card_rows = (len(card_payload) + 2) // 3
    components.html(CARDS_HTML, height=260 * max(card_rows, 1) + 40, scrolling=True)

    # --- Full article text, per outlet (native Streamlit expanders so
    # they stay properly interactive) ------------------------------------
    for name, data in results.items():
        with st.expander(f"Read full article from {name} (highlighted)"):
            highlighted = highlight_text(data["text"], data["framing_words"])
            st.markdown(f'<div class="nl-article-box">{highlighted}</div>', unsafe_allow_html=True)