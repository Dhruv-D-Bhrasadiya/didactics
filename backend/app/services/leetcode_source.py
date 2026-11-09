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


def _resolve_slug(index_payload: dict[str, Any], problem_number: int) -> str | None:
    """Match the user-visible frontend ID, not LeetCode's internal database ID."""
    wanted = str(problem_number)
    for item in index_payload.get("stat_status_pairs", []):
        stat = item.get("stat") or {}
        frontend_id = stat.get("frontend_question_id")
        if str(frontend_id if frontend_id is not None else stat.get("question_id", "")) == wanted:
            return stat.get("question__title_slug")
    return None


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

    # LeetCode operates separate public hosts. Try the primary .com host first,
    # then the .cn host when the primary host is blocked or unavailable.
    sources = [
        ("https://leetcode.com/api/problems/all/", "https://leetcode.com/graphql", "https://leetcode.com/"),
        ("https://leetcode.cn/api/problems/all/", "https://leetcode.cn/graphql", "https://leetcode.cn/"),
    ]
    last_error = "LeetCode did not return a usable problem response."
    valid_index_seen = False
    slug = None
    payload = None

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=10.0),
            follow_redirects=True,
        ) as client:
            for index_url, graphql_url, origin in sources:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Origin": origin.rstrip("/"),
                    "Referer": origin,
                }
                try:
                    index_response = await client.get(index_url, headers=headers)
                    if index_response.status_code == 429:
                        raise ProblemRateLimited()
                    if index_response.status_code in {401, 403} or index_response.status_code >= 500:
                        last_error = (
                            f"LeetCode problem index at {index_url} returned "
                            f"HTTP {index_response.status_code}."
                        )
                        continue
                    index_response.raise_for_status()
                    index = index_response.json()
                    if not isinstance(index, dict) or not isinstance(index.get("stat_status_pairs"), list):
                        last_error = f"LeetCode returned an unexpected problem-index format from {index_url}."
                        continue
                    valid_index_seen = True
                    slug = _resolve_slug(index, problem_number)
                    if not slug:
                        continue

                    details_response = await client.post(
                        graphql_url,
                        json={
                            "operationName": "questionData",
                            "query": QUESTION_QUERY,
                            "variables": {"titleSlug": slug},
                        },
                        headers=headers,
                    )
                    if details_response.status_code == 429:
                        raise ProblemRateLimited()
                    if details_response.status_code in {401, 403} or details_response.status_code >= 500:
                        last_error = (
                            f"LeetCode problem details at {graphql_url} returned "
                            f"HTTP {details_response.status_code}."
                        )
                        payload = None
                        continue
                    details_response.raise_for_status()
                    payload = details_response.json()
                    if not isinstance(payload, dict):
                        last_error = f"LeetCode returned an unexpected GraphQL response from {graphql_url}."
                        payload = None
                        continue
                    question = (payload.get("data") or {}).get("question")
                    if question:
                        break
                    if payload.get("errors"):
                        last_error = f"LeetCode GraphQL error: {payload['errors'][0].get('message', 'unknown error')}"
                    else:
                        last_error = "LeetCode returned no question details."
                    payload = None
                except ProblemRateLimited:
                    raise
                except httpx.HTTPStatusError as exc:
                    last_error = (
                        f"LeetCode request to {exc.request.url} returned "
                        f"HTTP {exc.response.status_code}."
                    )
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    last_error = f"Could not retrieve data from {origin}: {type(exc).__name__}: {exc}"

    except ProblemRateLimited:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise ProblemSourceUnavailable(
            f"Could not connect to LeetCode. Check your internet connection or network restrictions. ({type(exc).__name__})"
        ) from exc

    if not valid_index_seen:
        raise ProblemSourceUnavailable(last_error)
    if not slug:
        raise ProblemNotFound()
    if not payload:
        raise ProblemSourceUnavailable(last_error)

    question = (payload.get("data") or {}).get("question")
    if not question:
        raise ProblemNotFound()
    if question.get("isPaidOnly") and not question.get("content"):
        raise PremiumProblem()

    normalized = normalize_question(problem_number, question)
    if not normalized["statement_text"]:
        raise ProblemSourceUnavailable("LeetCode returned an empty problem statement.")
    _cache[problem_number] = (time.monotonic() + CACHE_TTL_SECONDS, normalized)
    return normalized
