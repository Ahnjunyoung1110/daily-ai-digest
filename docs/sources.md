# Sources

## RSS/API sources

Defined in `RSS_SOURCES` and API collector functions.

- OpenAI
- Google AI
- Hugging Face Blog
- GitHub Blog
- NVIDIA Developer
- AWS ML
- Microsoft Research
- LangChain (`https://blog.langchain.com/rss.xml`)
- Qwen
- arXiv cs.AI/cs.CL/cs.LG/stat.ML
- Simon Willison
- HN Algolia
- GitHub Search

## Reddit JSON/community sources

Defined in `REDDIT_SOURCES` and collected by `collect_reddit()`. Reddit RSS is no longer the production-preferred path because it lacks points/comments. The collector first tries `top.json?t=week`; if unauthenticated Reddit JSON returns 403, it falls back to RSS and score v2 normally drops those low-signal fallback items.

- Reddit LocalLLaMA
- Reddit MachineLearning

## HTML-only sources

Defined in `HTML_SOURCES` and `HTML_PARSERS`.

- Anthropic News: `https://www.anthropic.com/news`
  - Known fragile area: embedded `publishedOn` metadata and nav/card anchor false positives.
- Google DeepMind: `https://deepmind.google/blog/`
- Meta AI: `https://ai.meta.com/blog/`
- Mistral: `https://mistral.ai/news/`
- DeepSeek: `https://api-docs.deepseek.com/updates`
  - News URLs use `/news/newsYYMMDD`; date parser handles that format.
- HF Papers: `https://huggingface.co/papers`
  - Preferred parser reads Svelte `data-props` DailyPapers JSON and uses `submittedOnDailyAt` / `publishedAt`.

## Source taxonomy and scoring

`HIGH_PRIORITY_SOURCES` is kept only for compatibility. New scoring uses source-class registries in `sources.py`: `OFFICIAL_SOURCES`, `VENDOR_BLOG_SOURCES`, `COMMUNITY_SOURCES`, `RESEARCH_SOURCES`, `REPO_SOURCES`, and `INDIVIDUAL_EXPERT_SOURCES`. When adding Reddit/HN/GitHub/arXiv-like sources, add them to the correct class and choose a source-class threshold instead of treating them as official high-priority sources.

## Adding a source

1. Add to the correct registry: RSS/API vs Reddit/community vs HTML-only, and update the source taxonomy if the source class is new.
2. For HTML-only sources, add a parser and keep failure source-local.
3. Add date recovery if dates are outside the local card segment.
4. Run `--source "Exact Source Name" --include-stale`.
5. Inspect `meta.source_statuses`, `failed_sources`, `sources_date_issues`, and `unknown_date_candidates_total`.
