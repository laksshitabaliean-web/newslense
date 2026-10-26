"""
NewsLense backend -- scraping, fetching and analysis.

Outlets covered: BBC, CNN, Fox News, The Guardian, Reuters, Al Jazeera.
This file only defines functions/data -- nothing runs on import, so it's
safe for app.py (the Streamlit frontend) to `from newslense import ...`.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ddgs import DDGS
from newspaper import Article, Config
from textblob import TextBlob


# ---------------------------------------------------------------------------
# Step 1: find a real article URL per outlet for a given topic (parallel)
# ---------------------------------------------------------------------------

outlets = {
    "BBC": "bbc.co.uk",
    "CNN": "cnn.com",
    "Fox News": "foxnews.com",
    "The Guardian": "theguardian.com",
    "Reuters": "reuters.com",
    "Al Jazeera": "aljazeera.com",
}

ARTICLE_CONFIG = Config()
ARTICLE_CONFIG.request_timeout = 6  # don't let one slow/blocking site stall everything


def find_article_urls(topic, site, retries=2):
    """Search DuckDuckGo for a real article (not a homepage/hub page) on `site`."""
    query = f"{topic} site:{site}"
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            for r in results:
                url = r["href"]
                # skip homepages and topic/category hub pages
                if site in url and "/topics/" not in url and "/topic/" not in url:
                    if url.rstrip("/") not in [
                        f"https://www.{site}",
                        f"http://www.{site}",
                        f"https://{site}",
                        f"http://{site}",
                    ]:
                        return url
            return None
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {site}: {e}")
            time.sleep(1)
    return None


def find_all_urls(topic):
    """Returns {outlet_name: url} for every outlet a URL was found for.
    Runs all outlets concurrently instead of one after another, since this
    is purely network-bound work. An outlet missing from the result means
    it failed; app.py compares this against `outlets` to show that
    gracefully instead of crashing."""
    urls = {}
    with ThreadPoolExecutor(max_workers=len(outlets)) as executor:
        future_to_name = {
            executor.submit(find_article_urls, topic, domain): name
            for name, domain in outlets.items()
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                url = future.result()
            except Exception as e:
                print(f"Error searching {name}: {e}")
                url = None
            if url:
                urls[name] = url
            else:
                print(f"no results found for {name}")
    return urls


# ---------------------------------------------------------------------------
# Step 2: fetch the actual article text (also parallel)
# ---------------------------------------------------------------------------

def fetch_article_text(url):
    try:
        article = Article(url, config=ARTICLE_CONFIG)
        article.download()
        article.parse()
        return {"title": article.title, "text": article.text}
    except Exception as e:
        print(f"Error fetching article from {url}: {e}")
        return None


def fetch_all_articles(urls):
    """Returns {outlet_name: {title, text}} for every URL that was
    successfully scraped, fetched concurrently. A missing outlet means the
    fetch failed (e.g. Reuters/Fox News blocking scrapers with a 401/403)."""
    if not urls:
        return {}
    articles = {}
    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        future_to_name = {
            executor.submit(fetch_article_text, url): name
            for name, url in urls.items()
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                result = None
            if result and result["text"]:
                articles[name] = result
            else:
                print(f"Could not extract article text for {name}")
    return articles


# ---------------------------------------------------------------------------
# Step 3: analysis -- framing words, sentiment, charge score, highlighting
# ---------------------------------------------------------------------------

# One color per loaded term, used both for highlighting article text and
# for any chart legends in the UI. Matches the app's cyan/pink/neon palette.
FRAMING_COLORS = {
    "protesters": "#4fd8ff",
    "activists": "#ff3d8a",
    "rioters": "#ff5c5c",
    "demonstrators": "#7cf5c4",
    "extremists": "#ffb86c",
    "campaigners": "#c792ea",
}


def check_framing_words(text):
    text_lower = text.lower()
    framing_terms = {
        "protesters": text_lower.count("protester"),
        "activists": text_lower.count("activist"),
        "rioters": text_lower.count("rioter"),
        "demonstrators": text_lower.count("demonstrator"),
        "extremists": text_lower.count("extremist"),
        "campaigners": text_lower.count("campaigner"),
    }
    return {k: v for k, v in framing_terms.items() if v > 0}


def get_example_sentence(text, word):
    sentences = text.split(". ")
    for sentence in sentences:
        if word in sentence.lower():
            return sentence.strip() + "."
    return None


def compute_charge_score(framing_words, sentiment, word_count):
    """A single 0-100 'charged language' score, combining:
      - how densely loaded words appear (relative to article length)
      - how far sentiment strays from neutral
    This is a simple, transparent heuristic, not a scientific measure."""
    if word_count == 0:
        return 0
    total_mentions = sum(framing_words.values())
    density = total_mentions / word_count  # loaded words per word of text
    score = (density * 1200) + (abs(sentiment) * 40)
    return round(min(100, score))


def highlight_text(text, framing_words):
    """Returns the article text as HTML, with every framing word wrapped
    in a colored <mark> tag so it can be rendered with st.markdown(...,
    unsafe_allow_html=True)."""
    highlighted = text
    for word in framing_words:
        color = FRAMING_COLORS.get(word, "#ffffff")
        singular = word.rstrip("s")
        pattern = re.compile(rf"\b({re.escape(singular)}\w*)\b", re.IGNORECASE)
        highlighted = pattern.sub(
            rf"<mark style='background-color:{color}33;color:{color};"
            rf"font-weight:600;padding:0 3px;border-radius:4px;'>\1</mark>",
            highlighted,
        )
    # turn paragraph breaks into actual breaks for HTML rendering
    highlighted = highlighted.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return highlighted


def analyze_article(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    framing = check_framing_words(text)
    word_count = len(text.split())

    example_sentence = None
    top_word = None
    if framing:
        top_word = max(framing, key=framing.get)
        example_sentence = get_example_sentence(text, top_word.rstrip("s"))

    charge_score = compute_charge_score(framing, sentiment, word_count)

    return {
        "sentiment": sentiment,
        "word_count": word_count,
        "framing_words": framing,
        "example_sentence": example_sentence,
        "top_word": top_word,
        "charge_score": charge_score,
    }


def analyze_all(all_articles):
    analysis = {}
    for name, data in all_articles.items():
        result = analyze_article(data["text"])
        analysis[name] = {
            "title": data["title"],
            "text": data["text"],
            "sentiment": result["sentiment"],
            "word_count": result["word_count"],
            "framing_words": result["framing_words"],
            "example_sentence": result["example_sentence"],
            "top_word": result["top_word"],
            "charge_score": result["charge_score"],
        }
    return analysis


def aggregate_framing_words(results):
    """Sums framing-word counts across every outlet, for the word cloud."""
    totals = {}
    for data in results.values():
        for word, count in data["framing_words"].items():
            totals[word] = totals.get(word, 0) + count
    return totals


def generate_takeaway(results):
    """Returns plain text with <strong> HTML tags for emphasis (not
    markdown ** syntax) since this gets rendered via unsafe_allow_html."""
    totals = {name: data["charge_score"] for name, data in results.items()}
    if not any(totals.values()):
        return "No strong framing differences detected for this topic."
    most = max(totals, key=totals.get)
    least = min(totals, key=totals.get)
    if totals[most] == totals[least]:
        return "All outlets used similarly charged language for this story."

    return (
        f"<strong>{most}</strong> used the most charged language "
        f"(score {totals[most]}/100), while <strong>{least}</strong> "
        f"used the least (score {totals[least]}/100)."
    )


# ---------------------------------------------------------------------------
# Only runs when you execute this file directly (python3 newslense.py),
# never when app.py imports from it.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    topic = "climate protest london"
    found_urls = find_all_urls(topic)
    print(found_urls)

    all_articles = fetch_all_articles(found_urls)
    results = analyze_all(all_articles)

    for name, data in results.items():
        print(f"\n--- {name} ---")
        print(f"Title: {data['title']}")
        print(f"Sentiment: {data['sentiment']:.2f}")
        print(f"Word count: {data['word_count']}")
        print(f"Framing words: {data['framing_words']}")
        print(f"Charge score: {data['charge_score']}")

