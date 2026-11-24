import html
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup


LANGUAGE_ALIASES = {
    "python": "python3",
    "java": "java",
    "c": "c",
    "c++": "cpp",
    "javascript": "javascript",
}

INDENT_WIDTHS = {
    "python3": 4,
    "python": 4,
    "java": 4,
    "c": 4,
    "cpp": 4,
    "javascript": 4,  # Change to 2 if your source snippets use 2-space JS
}


def get_description(data: dict[str, Any]) -> str:
    content = data.get("content", "")
    soup = BeautifulSoup(content, "html.parser")
    paragraphs = []

    for p in soup.find_all("p", recursive=False):
        text = p.get_text(" ", strip=True)

        # Stop when reaching Examples or Constraints
        if re.match(r"^(Example\s+\d+|Constraints?)\s*:?", text, re.I):
            break

        # Clean up spacing around punctuation and superscripts (e.g., "i th" -> "ith", "height ." -> "height.")
        text = html.unescape(text)
        text = re.sub(r"\s+([.,;:!?])", r"\1", text)
        text = re.sub(r"\b(\w+)\s+(th|st|nd|rd)\b", r"\1\2", text)
        text = re.sub(r"\s+", " ", text).strip()

        if text:
            paragraphs.append(text)

    # Join paragraphs with a single space (or "\n\n" if you want paragraph breaks without mid-sentence newlines)
    return " ".join(paragraphs)


def get_examples(data: dict[str, Any]) -> list[dict[str, Any]]:
    content = data.get("content", "")
    soup = BeautifulSoup(content, "html.parser")
    examples: list[dict[str, Any]] = []

    for heading in soup.find_all(["strong", "b"]):
        heading_text = heading.get_text(" ", strip=True)
        if not re.match(r"Example\s+\d+\s*:", heading_text, re.I):
            continue

        parent = heading.find_parent("p")
        if not parent:
            continue

        image: str | None = None
        input_value = ""
        output_value = ""
        explanation = ""

        # Traverse sibling elements after the Example <p> tag
        for element in parent.find_next_siblings():
            # Stop if we reach the next Example or Constraints heading
            if element.name == "p" and element.find(["strong", "b"]):
                next_heading = element.find(["strong", "b"]).get_text(" ", strip=True)
                if re.match(r"(Example\s+\d+|Constraints)\s*:", next_heading, re.I):
                    break

            if element.name == "img":
                image = element.get("src")
            elif element.find("img"):  # In case <img> is wrapped in a <p> or <div>
                image = element.find("img").get("src")

            if element.name == "pre":
                pre_text = element.get_text("\n", strip=True)

                def extract(pattern: str, next_pattern: str) -> str:
                    match = re.search(
                        rf"{pattern}\s*:\s*(.*?)(?={next_pattern}\s*:|$)",
                        pre_text,
                        re.I | re.S,
                    )
                    return match.group(1).strip() if match else ""

                input_value = extract("Input", "Output")
                output_value = extract("Output", "Explanation")
                explanation = extract("Explanation", r"$^")
                break

        examples.append(
            {
                "example_number": len(examples) + 1,
                "input": input_value,
                "output": output_value,
                "explanation": explanation,
                "image": image,
            }
        )

    return examples


def get_constraints(data: dict[str, Any]) -> list[str]:
    content = data.get("content", "")
    soup = BeautifulSoup(content, "html.parser")

    constraints: list[str] = []

    for tag in soup.find_all(["strong", "b"]):
        if re.match(r"Constraints?\s*:?", tag.get_text(strip=True), re.I):

            parent = tag.find_parent("p")

            if parent:
                for element in parent.find_all_next():
                    if element.name in ["pre", "h1", "h2", "h3", "h4"]:
                        break

                    if element.name == "li":
                        value = element.get_text(" ", strip=True)
                        if value:
                            constraints.append(value)

                break

    return constraints


def get_similar_questions(data: dict[str, Any]) -> list[dict[str, Any]]:

    similar = data.get("similarQuestions", [])

    if isinstance(similar, str):
        try:
            similar = json.loads(similar)
        except json.JSONDecodeError:
            return []

    return [
        {
            "name": question.get("title"),
            "slug": question.get("titleSlug"),
            "difficulty": question.get("difficulty"),
        }
        for question in similar
        if isinstance(question, dict)
    ]


def get_topics(data: dict[str, Any]) -> list[str]:
    return [
        tag["name"]
        for tag in data.get("topicTags", [])
        if isinstance(tag, dict) and tag.get("name")
    ]


def get_hints(data: dict[str, Any]) -> list[str]:
    return data.get("hints", [])


def _convert_indentation_to_tabs(code: str, space_width: int = 4) -> str:
    if not code:
        return ""
    if space_width < 1:
        raise ValueError("space_width must be a positive integer.")

    converted_lines = []
    for line in code.splitlines():
        # Match leading spaces/tabs only at the start of the line
        match = re.match(r"^([ \t]+)(.*)", line)
        if match:
            leading_ws, rest = match.groups()
            # Normalize existing tabs to spaces first, then divide into tab levels
            total_spaces = leading_ws.replace("\t", " " * space_width)
            tab_count = len(total_spaces) // space_width
            remainder_spaces = len(total_spaces) % space_width
            converted_lines.append(("\t" * tab_count) + (" " * remainder_spaces) + rest)
        else:
            converted_lines.append(line)

    return "\n".join(converted_lines)


def get_code_template(data: dict[str, Any], language: str) -> dict[str, Any] | None:
    normalized = language.lower().strip()
    target_slug = LANGUAGE_ALIASES.get(normalized, normalized)

    for snippet in data.get("codeSnippets", []):
        if not isinstance(snippet, dict):
            continue
        language_slug = snippet.get("langSlug", "")
        if not isinstance(language_slug, str):
            continue
        slug = language_slug.lower()
        if slug == target_slug:
            space_width = INDENT_WIDTHS.get(slug, 4)
            code = snippet.get("code", "")
            if not isinstance(code, str):
                raise ValueError("LeetCode source returned a non-text code template.")
            formatted_code = _convert_indentation_to_tabs(code, space_width)

            return {
                "language": snippet.get("lang"),
                "language_slug": snippet.get("langSlug"),
                "code": formatted_code,
            }

    return None


def fetch_problem(problem_number: int, language: str = "java") -> dict[str, Any]:
    if type(problem_number) is not int or problem_number < 1:
        raise ValueError(
            "Problem number must be a positive integer within LeetCode's question range."
        )

    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        url = f"https://leetcode-api-pied.vercel.app/problem/{problem_number}"

        response = client.get(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; Didactics/1.0)",
            },
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("LeetCode source returned an invalid problem payload.")

        return {
            "name": data.get("title"),
            "difficulty": data.get("difficulty"),
            "description": get_description(data),
            "examples": get_examples(data),
            "constraints": get_constraints(data),
            "similar_questions": get_similar_questions(data),
            "topics": get_topics(data),
            "hints": get_hints(data),
            "code_template": get_code_template(data, language),
        }