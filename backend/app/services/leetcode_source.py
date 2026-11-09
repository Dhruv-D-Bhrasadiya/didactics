"""LeetCode problem source adapter with normalization and safe HTML handling."""
from __future__ import annotations

import html
import json
import time
from html.parser import HTMLParser
from typing import Any

import httpx

INDEX_URL = "https://leetcode.com/api/problems/all/"
GRAPHQL_URL = "https://leetcode.com/graphql"
QUESTION_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId questionFrontendId title titleSlug content difficulty isPaidOnly
    topicTags { name slug }
    sampleTestCase metaData stats
  }
}
"""
CACHE_TTL_SECONDS = 300
_cache: dict[int, tuple[float, dict[str, Any]]] = {}


class ProblemNotFound(Exception):
    pass


class ProblemSourceUnavailable(Exception):
    pass


class ProblemRateLimited(Exception):
    pass


class PremiumProblem(Exception):
    pass


class _SafeHTML(HTMLParser):
    """Allowlist sanitizer: removes attributes, scripts, styles and embedded objects."""
    ALLOWED = {
        "p", "br", "strong", "b", "em", "i", "code", "pre", "ul", "ol",
        "li", "sup", "sub", "span", "div", "blockquote", "h1", "h2",
        "h3", "h4", "table", "thead", "tbody", "tr", "th", "td",
    }
    BLOCKED = {"script", "style", "iframe", "object", "svg", "math"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.stack: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.BLOCKED:
            self.blocked_depth += 1
        elif not self.blocked_depth and tag in self.ALLOWED:
            self.output.append(f"<{tag}>")
            if tag != "br":
                self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.BLOCKED and self.blocked_depth:
            self.blocked_depth -= 1
        elif not self.blocked_depth and tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.output.append(f"</{current}>")
                if current == tag:
                    break

    def handle_data(self, data):
        if not self.blocked_depth:
            self.output.append(html.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.output.append(f"</{self.stack.pop()}>")
        return "".join(self.output)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.pre_parts: list[str] = []
        self.pre_blocks: list[str] = []
        self.pre_depth = 0
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.blocked_depth += 1
        if self.blocked_depth:
            return
        if tag == "pre":
            self.pre_depth += 1
            self.pre_parts = []
        if tag in {"p", "div", "li", "br", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.blocked_depth:
            self.blocked_depth -= 1
        if self.blocked_depth:
            return
        if tag == "pre" and self.pre_depth:
            self.pre_depth -= 1
            self.pre_blocks.append("".join(self.pre_parts).strip())
        if tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.blocked_depth:
            return
        self.parts.append(data)
        if self.pre_depth:
            self.pre_parts.append(data)


def _sanitize_statement(source_html: str) -> tuple[str, str, list[str]]:
    safe = _SafeHTML()
    safe.feed(source_html or "")
    extractor = _TextExtractor()
    extractor.feed(source_html or "")
    plain = "\n".join(
        line.strip()
        for line in "".join(extractor.parts).splitlines()
        if line.strip()
    )
    examples = [block for block in extractor.pre_blocks if block]
    return safe.result(), plain, examples


def normalize_question(problem_number: int, question: dict[str, Any]) -> dict[str, Any]:
    title = str(question.get("title") or "").strip()
    slug = str(question.get("titleSlug") or "").strip()
    if not title or not slug:
        raise ProblemSourceUnavailable("LeetCode returned incomplete problem details.")

    statement_html, statement_text, examples = _sanitize_statement(
        str(question.get("content") or "")
    )
    tags = [
        str(tag["name"]).strip()
        for tag in question.get("topicTags") or []
        if isinstance(tag, dict) and tag.get("name")
    ]
    lines = [line.strip() for line in statement_text.splitlines() if line.strip()]
    constraints: list[str] = []
    for index, line in enumerate(lines):
        if line.lower().rstrip(":") == "constraints":
            for candidate in lines[index + 1:]:
                if candidate.lower().startswith(("follow-up", "follow up", "hints:")):
                    break
                if candidate.strip():
                    constraints.append(candidate.lstrip("•- ").strip())
            break

    def parse_json_field(value):
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    return {
        "problem_number": problem_number,
        "question_id": str(question.get("questionId") or ""),
        "title": title,
        "slug": slug,
        "difficulty": str(question.get("difficulty") or "Unknown").title(),
        "is_premium": bool(question.get("isPaidOnly", False)),
        "topic_tags": tags,
        "statement_html": statement_html,
        "statement_text": statement_text,
        "examples": examples,
        "sample_test_case": str(question.get("sampleTestCase") or "").strip(),
        "constraints": constraints,
        "metadata": parse_json_field(question.get("metaData")),
        "stats": parse_json_field(question.get("stats")),
        "canonical_url": f"https://leetcode.com/problems/{slug}/",
        "source": "LeetCode",
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


async def fetch_problem(problem_number: int) -> dict[str, Any]:
    cached = _cache.get(problem_number)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Didactics/1.0; problem lookup)",
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(18.0, connect=8.0),
            follow_redirects=True,
            headers=headers,
        ) as client:
            index_response = await client.get(INDEX_URL)
            if index_response.status_code == 429:
                raise ProblemRateLimited()
            if index_response.status_code in {401, 403}:
                raise ProblemSourceUnavailable("LeetCode blocked the public problem-index request.")
            index_response.raise_for_status()
            index = index_response.json()

            slug = None
            for item in index.get("stat_status_pairs", []):
                stat = item.get("stat") or {}
                if str(stat.get("question_id", "")) == str(problem_number):
                    slug = stat.get("question__title_slug")
                    break
            if not slug:
                raise ProblemNotFound()

            details_response = await client.post(
                GRAPHQL_URL,
                json={"query": QUESTION_QUERY, "variables": {"titleSlug": slug}},
            )
            if details_response.status_code == 429:
                raise ProblemRateLimited()
            if details_response.status_code in {401, 403}:
                raise ProblemSourceUnavailable("LeetCode blocked the problem-details request.")
            details_response.raise_for_status()
            payload = details_response.json()
    except (ProblemNotFound, ProblemRateLimited, ProblemSourceUnavailable):
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise ProblemRateLimited() from exc
        raise ProblemSourceUnavailable(
            f"LeetCode returned HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise ProblemSourceUnavailable(
            "Could not retrieve valid data from LeetCode."
        ) from exc

    question = (payload.get("data") or {}).get("question")
    if not question:
        if payload.get("errors"):
            raise ProblemSourceUnavailable("LeetCode returned a GraphQL error.")
        raise ProblemNotFound()
    if question.get("isPaidOnly") and not question.get("content"):
        raise PremiumProblem()

    normalized = normalize_question(problem_number, question)
    if not normalized["statement_text"]:
        raise ProblemSourceUnavailable("LeetCode returned an empty problem statement.")
    _cache[problem_number] = (time.monotonic() + CACHE_TTL_SECONDS, normalized)
    return normalized
