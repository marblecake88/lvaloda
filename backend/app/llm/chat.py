"""Grok chat calls for dialog + exam modes + Russian-hint helper."""

import json
import logging
import re

from app.config import get_settings
from app.llm.client import grok
from app.llm.prompts import (
    PICTURE_ANALYSIS_PROMPT,
    RUSSIAN_HINT_PROMPT,
    build_analysis_prompt,
    build_dialog_prompt,
    build_exam_prompt,
)
from app.llm.scenarios import Scenario

log = logging.getLogger(__name__)
_settings = get_settings()


# When grok loses the plot and starts regurgitating the system prompt instead
# of role-playing, its reply begins with one of these tokens. We detect and
# regenerate once with a corrective nudge.
_LEAK_PATTERNS = re.compile(
    r"^\s*("
    r"assistant\s*[:：]|"
    r"role\s*[:：]|"
    r"policy\s*[:：]|"
    r"student\s+level\s*[:：]|"
    r"lexicon|"
    r"first\s*,\s*the\s+policy|"
    r"scenario\s*[:：]|"
    r"rules\s*[:：]"
    r")",
    re.IGNORECASE,
)


def _looks_like_leak(text: str) -> bool:
    if not text:
        return False
    return bool(_LEAK_PATTERNS.match(text))


async def dialog_reply(
    scenario: Scenario,
    history: list[dict],
    *,
    known_vocab: list[str] | None = None,
    level_hint: str | None = None,
) -> str:
    system = build_dialog_prompt(
        scenario, known_vocab=known_vocab, level_hint=level_hint
    )
    messages = [{"role": "system", "content": system}, *history]
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=messages,
        temperature=0.8,
    )
    text = resp.choices[0].message.content or ""

    # Defensive: grok occasionally echoes the system prompt instead of role-playing.
    # Regenerate once with an explicit corrective nudge and without the hint sections.
    if _looks_like_leak(text):
        log.warning("dialog_reply: detected prompt leak, regenerating")
        minimal_system = (
            f"You are a friendly local Latvian in the scene '{scenario.title_lv}'. "
            f"{scenario.context} Reply ONLY in Latvian, 1-3 short sentences. "
            "Never output words like 'Assistant', 'Role', 'Policy', 'Student level'. "
            "Just speak as the character."
        )
        nudge = (
            "Your previous attempt accidentally printed meta-instructions. "
            "Respond in-character in Latvian only, 1-3 sentences."
        )
        messages2 = [
            {"role": "system", "content": minimal_system},
            *history,
            {"role": "user", "content": nudge} if history else {"role": "user", "content": "Sveiki!"},
        ]
        # Deduplicate if we just appended a synthetic user when there was no history.
        resp2 = await grok.chat.completions.create(
            model=_settings.xai_model,
            messages=messages2,
            temperature=0.9,
        )
        text = resp2.choices[0].message.content or text
    return text


async def exam_reply(
    scenario: Scenario,
    covered_angles: list[str],
    history: list[dict],
    *,
    known_vocab: list[str] | None = None,
    level_hint: str | None = None,
) -> str:
    messages = [
        {
            "role": "system",
            "content": build_exam_prompt(
                scenario,
                covered_angles,
                known_vocab=known_vocab,
                level_hint=level_hint,
            ),
        },
        *history,
    ]
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=messages,
        temperature=0.8,
    )
    return resp.choices[0].message.content or ""


async def exam_final_report(
    scenario: Scenario,
    covered_angles: list[str],
    history: list[dict],
    *,
    known_vocab: list[str] | None = None,
    level_hint: str | None = None,
) -> dict:
    """Send <<FINISH>> and parse the JSON report."""
    messages = [
        {
            "role": "system",
            "content": build_exam_prompt(
                scenario,
                covered_angles,
                known_vocab=known_vocab,
                level_hint=level_hint,
            ),
        },
        *history,
        {"role": "user", "content": "<<FINISH>>"},
    ]
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON report, falling back")
        return {
            "covered_angles": [],
            "fluency_score": 3,
            "unnatural_phrases": [],
            "missed_vocabulary": [],
            "summary_ru": raw[:500],
        }


async def analyze_dialog(scenario: Scenario, history: list[dict]) -> dict:
    """Run an end-of-session analysis: unnatural phrases + tips + summary."""
    messages = [
        {"role": "system", "content": build_analysis_prompt(scenario)},
        *history,
        {"role": "user", "content": "<<ANALYZE>>"},
    ]
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON analysis, falling back")
        return {
            "fluency_score": 3,
            "unnatural_phrases": [],
            "new_vocabulary": [],
            "strengths_ru": [],
            "tips_ru": [],
            "summary_ru": raw[:500],
        }


async def analyze_picture(image_url: str, history: list[dict]) -> dict:
    """Vision-enabled picture description review.

    We send the image + transcript of what the student said to Grok's
    multimodal endpoint and ask it to compare, correct, and teach.
    """
    # Flatten the dialog history into a text snippet so it fits as a single
    # user message alongside the image.
    transcript_lines: list[str] = []
    for m in history:
        role = "Ученик" if m["role"] == "user" else "Бот"
        transcript_lines.append(f"{role}: {m['content']}")
    transcript = "\n".join(transcript_lines) or "(разговора не было)"

    messages = [
        {"role": "system", "content": PICTURE_ANALYSIS_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Вот диалог ученика про эту картинку:\n\n"
                        + transcript
                        + "\n\nПроанализируй по правилам выше и верни JSON."
                    ),
                },
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
    ]

    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("picture analysis: non-JSON")
        return {
            "what_is_there_lv": "",
            "what_is_there_ru": raw[:500],
            "key_vocabulary": [],
            "user_accuracy_score": 3,
            "missed_elements_ru": [],
            "unnatural_phrases": [],
            "tips_ru": [],
            "summary_ru": "",
        }


async def russian_hint(text_lv: str) -> str:
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=[{"role": "user", "content": RUSSIAN_HINT_PROMPT.format(text=text_lv)}],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""
