import json
import os
import re

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_model = None


def get_model():
    global _model
    if _model is not None:
        return _model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel(MODEL_NAME)
    return _model

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape_internshala(career_interest):
    slug = career_interest.strip().lower().replace(" ", "-")
    urls = [
        f"https://internshala.com/internships/{slug}-internship/",
        f"https://internshala.com/internships/keyword-{slug}/",
        "https://internshala.com/internships/",
    ]

    last_error = None
    for base_url in urls:
        try:
            internships = _parse_internshala_page(base_url)
            if internships:
                return internships[:10]
        except Exception as e:
            last_error = e

    raise Exception(
        last_error
        or "No internships found for that keyword. Try something like "
        "'web development', 'data science', or 'marketing'."
    )


def _parse_internshala_page(base_url):
    response = requests.get(base_url, headers=HEADERS, timeout=15)

    if response.status_code != 200:
        raise Exception(
            f"Internshala scraping failed (status {response.status_code}). "
            "Try a different career keyword."
        )

    soup = BeautifulSoup(response.content, "html.parser")
    internships = []
    seen_urls = set()

    for a_tag in soup.select("a.job-title-href"):
        href = a_tag.get("href")
        title = a_tag.get_text(strip=True)
        if not href or not title:
            continue

        full_url = href if href.startswith("http") else f"https://internshala.com{href}"
        if full_url in seen_urls:
            continue

        seen_urls.add(full_url)
        internships.append({"title": title, "url": full_url})

    if not internships:
        raise Exception(
            "No internships found for that keyword. Try something like "
            "'web development', 'data science', or 'marketing'."
        )

    return internships


def _extract_json_block(text):
    for opener, closer in [("[", "]"), ("{", "}")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for index, char in enumerate(text[start:], start):
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
    return text


def _sanitize_json_text(text):
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        looks_like_json = (
            stripped[0] in "[{]}"
            or stripped.startswith('"')
            or stripped.startswith("- ")
            or ":" in stripped
            or stripped.endswith(",")
            or stripped in {"true", "false", "null"}
            or stripped[0].isdigit()
        )
        if looks_like_json:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def clean_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text.strip())

    candidates = [text, _extract_json_block(text), _sanitize_json_text(text)]
    seen = set()
    last_error = None

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return [parsed]
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError as error:
            last_error = error
            continue

    raise ValueError(
        "Could not read the AI response. Please try your search again."
    ) from last_error


def parse_with_gemini(prompt):
    last_error = None
    current_prompt = prompt

    for attempt in range(2):
        try:
            response = get_model().generate_content(
                current_prompt,
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception as e:
            message = str(e)
            if "API_KEY_INVALID" in message or "API key not valid" in message:
                raise ValueError(
                    "Your Gemini API key is invalid. Open .env and paste a fresh key from "
                    "https://aistudio.google.com/apikey"
                ) from e
            if "429" in message or "quota" in message.lower():
                raise ValueError(
                    "Gemini rate limit hit for this model. Wait a minute and try again, "
                    "or set GEMINI_MODEL=gemini-2.5-flash in your .env file."
                ) from e
            raise

        print("Gemini raw response:\n", response.text)
        try:
            return clean_response(response.text)
        except ValueError as e:
            last_error = e
            current_prompt = (
                f"{prompt}\n\n"
                "Return ONLY a valid JSON array. Do not include any extra words, "
                "comments, or text outside the JSON."
            )

    raise last_error


def process_query(data):
    if data["type"] == "career_interest":
        internships = scrape_internshala(data["careerInterest"])
        prompt = (
            f"Given the following internships:\n{json.dumps(internships, indent=2)}\n"
            "Return a JSON array. Each item must have: title, url, skills (array of 5 strings), "
            "and free_resources (array of URL strings to free learning resources)."
        )
        return parse_with_gemini(prompt)

    if data["type"] == "skills_and_hobbies":
        prompt = (
            f"Given the user's skills: {data['skills']} and hobbies: {data['hobbies']}, "
            "Suggest 5 suitable career paths as a JSON array. Each item must have: title, "
            "skills (array of 5 strings), and free_resources (array of URL strings). "
            "Omit url if not applicable."
        )
        return parse_with_gemini(prompt)

    raise ValueError("Unknown query type")
