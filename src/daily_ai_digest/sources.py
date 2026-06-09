from __future__ import annotations

import re

RSS_SOURCES = [
    ("OpenAI", "blog", "https://openai.com/news/rss.xml"),
    ("Google AI", "blog", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face", "blog", "https://huggingface.co/blog/feed.xml"),
    ("GitHub Blog", "blog", "https://github.blog/feed/"),
    ("NVIDIA Developer", "blog", "https://developer.nvidia.com/blog/feed/"),
    ("AWS ML", "blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("Microsoft Research", "blog", "https://www.microsoft.com/en-us/research/feed/"),
    # blog.langchain.dev/rss currently serves the Webflow HTML landing page;
    # the canonical Ghost RSS endpoint is on blog.langchain.com/rss.xml.
    ("LangChain", "blog", "https://blog.langchain.com/rss.xml"),
    ("Qwen", "blog", "https://qwenlm.github.io/blog/index.xml"),
    ("arXiv cs.AI", "paper", "https://rss.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "paper", "https://rss.arxiv.org/rss/cs.CL"),
    ("arXiv cs.LG", "paper", "https://rss.arxiv.org/rss/cs.LG"),
    ("arXiv stat.ML", "paper", "https://rss.arxiv.org/rss/stat.ML"),
    ("Simon Willison", "community", "https://simonwillison.net/atom/everything/"),
]

REDDIT_SOURCES = [
    ("Reddit LocalLLaMA", "community", "LocalLLaMA"),
    ("Reddit MachineLearning", "community", "MachineLearning"),
]

# Sources without stable official RSS feeds. These are intentionally kept in a
# separate registry because the parsers below are HTML-structure tolerant and
# should fail soft per source instead of affecting RSS/API collection.
HTML_SOURCES = [
    ("Anthropic News", "blog", "https://www.anthropic.com/news"),
    ("Google DeepMind", "blog", "https://deepmind.google/blog/"),
    ("Meta AI", "blog", "https://ai.meta.com/blog/"),
    ("Mistral", "blog", "https://mistral.ai/news/"),
    # The user-provided /news landing path currently returns 404; /updates is
    # the reachable official docs landing page that links to /news/newsNNNNNN.
    ("DeepSeek", "blog", "https://api-docs.deepseek.com/updates"),
    ("HF Papers", "paper", "https://huggingface.co/papers"),
]

DEBUG_HTML_SOURCES = {
    "Anthropic News",
    "Google DeepMind",
    "Meta AI",
    "Mistral",
    "DeepSeek",
    "HF Papers",
}

OFFICIAL_SOURCES = {
    "OpenAI", "Google AI", "Anthropic News", "Google DeepMind", "Meta AI",
    "Mistral", "DeepSeek", "Qwen",
}

VENDOR_BLOG_SOURCES = {
    "Hugging Face", "GitHub Blog", "NVIDIA Developer", "AWS ML",
    "Microsoft Research", "LangChain",
}

COMMUNITY_SOURCES = {"Reddit LocalLLaMA", "Reddit MachineLearning", "HN"}
RESEARCH_SOURCES = {"arXiv cs.AI", "arXiv cs.CL", "arXiv cs.LG", "arXiv stat.ML", "HF Papers"}
REPO_SOURCES = {"GitHub"}
INDIVIDUAL_EXPERT_SOURCES = {"Simon Willison"}

# Kept for backward compatibility with docs/tests that still refer to the old
# name. New score v2 code uses source_class() instead of this single bucket.
HIGH_PRIORITY_SOURCES = OFFICIAL_SOURCES | VENDOR_BLOG_SOURCES | {"HF Papers"}

SOURCE_CLASS_THRESHOLDS = {
    "official": 40,
    "vendor_blog": 45,
    "community": 55,
    "repo": 50,
    "research": 45,
    "expert": 40,
    "unknown": 50,
}

def source_class(source: str, typ: str | None = None) -> str:
    if source in OFFICIAL_SOURCES:
        return "official"
    if source in VENDOR_BLOG_SOURCES:
        return "vendor_blog"
    if source in COMMUNITY_SOURCES:
        return "community"
    if source in RESEARCH_SOURCES or typ == "paper":
        return "research"
    if source in REPO_SOURCES or typ == "repo":
        return "repo"
    if source in INDIVIDUAL_EXPERT_SOURCES:
        return "expert"
    return "unknown"

GITHUB_KEYWORDS = ["llm", "rag", "agent", "mcp", "inference"]
GITHUB_TOPICS = ["topic:llm", "topic:rag", "topic:ai-agent", "topic:mcp"]
AI_TERMS = re.compile(
    r"\b(llm|rag|agent|agents|mcp|inference|multimodal|evaluation|benchmark|alignment"
    r"|security|model|models|ai|ml|transformer|retrieval|fine[- ]?tuning|reasoning"
    r"|open[- ]?weights?|quantization|cuda|gpu|tokenizer|diffusion)\b",
    re.I,
)

# 점수 변별용 핵심 기술 주제어 — AI_TERMS처럼 광범하지 않고, IMPACT_TERMS와 겹치지 않음.
# 필터 게이트(output.py)는 여전히 AI_TERMS 사용.
RELEVANCE_TERMS = re.compile(
    r"\b(llm|rag|agent|agents|mcp|multimodal|inference|transformer|retrieval"
    r"|fine[- ]?tuning|reasoning|quantization|diffusion|tokenizer|alignment)\b",
    re.I,
)

# 사건/출시 신호어 — RELEVANCE_TERMS와 겹치는 단어(reasoning, multimodal, inference,
# agent, mcp, fine-tuning, quantization) 제거하여 이중 계산 방지.
IMPACT_TERMS = re.compile(
    r"\b(release|released|launch|launched|announce|announced|api|sdk|cli|framework|library"
    r"|server|benchmark|eval|leaderboard|open[- ]?source|open[- ]?weights?|pricing|safety"
    r"|paper)\b",
    re.I,
)
PROMO_TERMS = re.compile(r"\b(webinar|event|sponsored|customer story|case study|partner)\b", re.I)
LOW_VALUE_TERMS = re.compile(
    r"\b(help|beginner|noob|question|what do you use|what'?s your|sources for|reading group"
    r"|recommend|should i|how do i|anyone else|daily driver)\b",
    re.I,
)
