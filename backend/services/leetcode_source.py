import html
import json
import re
import os
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

PATH = Path("output")
if not PATH:
    os.mkdir(PATH)
    print("Output Directory does not exits")
    print("Creating directory")
else:
    print("Output Directory exits")
    
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

LANGUAGE_EXTENSIONS = {
    "python3": ".py",
    "python": ".py",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp",
    "javascript": ".js",
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


def get_code_template(
    data: dict[str, Any],
    language: str,
    save_dir: str | Path | None = None,
) -> dict[str, Any] | None:
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
            saved_path: str | None = None

            if save_dir is not None:
                directory = Path(save_dir)
                directory.mkdir(parents=True, exist_ok=True)

                # Build filename using problem ID & slug (e.g., 0001_two_sum.java)
                problem_id = str(data.get("questionFrontendId", "problem")).zfill(4)
                title_slug = data.get("titleSlug", "solution").replace("-", "_")
                ext = LANGUAGE_EXTENSIONS.get(slug, f".{slug}")

                file_path = directory / f"{problem_id}_{title_slug}{ext}"
                file_path.write_text(formatted_code + "\n", encoding="utf-8")
                saved_path = str(file_path)

            return {
                "language": snippet.get("lang"),
                "language_slug": snippet.get("langSlug"),
                "code": formatted_code,
                "saved_path": saved_path,
            }
    return None


def save_problem_markdown(
    problem_data: dict[str, Any],
    raw_data: dict[str, Any],
    save_dir: str | Path,
) -> str:
    directory = Path(save_dir)
    directory.mkdir(parents=True, exist_ok=True)

    problem_id = str(raw_data.get("questionFrontendId", "problem")).zfill(4)
    title_slug = raw_data.get("titleSlug", "problem").replace("-", "_")
    md_path = directory / f"{problem_id}_{title_slug}.md"

    lines: list[str] = []

    # 1. Name & Difficulty
    name = problem_data.get("name") or "Untitled Problem"
    difficulty = problem_data.get("difficulty") or "Unknown"
    lines.append(f"# {raw_data.get('questionFrontendId', '')}. {name}".strip())
    lines.append(f"\n**Difficulty:** {difficulty}\n")

    # 2. Description
    lines.append("## Description\n")
    lines.append(f"{problem_data.get('description', '')}\n")

    # 3. Examples
    examples = problem_data.get("examples", [])
    if examples:
        lines.append("## Examples\n")
        for ex in examples:
            lines.append(f"### Example {ex['example_number']}\n")
            if ex.get("image"):
                lines.append(f"![Example {ex['example_number']}]({ex['image']})\n")
            lines.append("```text")
            lines.append(f"Input: {ex.get('input', '')}")
            lines.append(f"Output: {ex.get('output', '')}")
            if ex.get("explanation"):
                lines.append(f"Explanation: {ex['explanation']}")
            lines.append("```\n")

    # 4. Constraints
    constraints = problem_data.get("constraints", [])
    if constraints:
        lines.append("## Constraints\n")
        for item in constraints:
            lines.append(f"- `{item}`")
        lines.append("")

    # 5. Similar Questions
    similar = problem_data.get("similar_questions", [])
    if similar:
        lines.append("## Similar Questions\n")
        for q in similar:
            q_name = q.get("name", "")
            q_slug = q.get("slug", "")
            q_diff = q.get("difficulty", "")
            url = f"https://leetcode.com{q_slug}/" if q_slug else ""
            if url:
                lines.append(f"- [{q_name}]({url}) ({q_diff})")
            else:
                lines.append(f"- {q_name} ({q_diff})")
        lines.append("")

    # 6. Topics
    topics = problem_data.get("topics", [])
    if topics:
        lines.append("## Topics\n")
        lines.append(", ".join(f"`{t}`" for t in topics) + "\n")

    # 7. Hints
    hints = problem_data.get("hints", [])
    if hints:
        lines.append("## Hints\n")
        for idx, hint in enumerate(hints, start=1):
            clean_hint = BeautifulSoup(hint, "html.parser").get_text(" ", strip=True)
            lines.append(f"### Hint {idx}\n")
            lines.append(f"{clean_hint}\n")

    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(md_path)


def fetch_problem(
    problem_number: int,
    language: str = "java",
    save_dir: str | Path | None = None,
) -> dict[str, Any]:
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

        result = {
            "name": data.get("title"),
            "difficulty": data.get("difficulty"),
            "description": get_description(data),
            "examples": get_examples(data),
            "constraints": get_constraints(data),
            "similar_questions": get_similar_questions(data),
            "topics": get_topics(data),
            "hints": get_hints(data),
            "code_template": get_code_template(data, language, save_dir=save_dir),
            "markdown_path": None,
        }

        if save_dir is not None:
            result["markdown_path"] = save_problem_markdown(result, data, save_dir)

        return result