"""Picture-description mode with Grok-based image generation + long-term cache.

Scenes are tuned for language practice (realistic, describable, clear details).
Generated images are persisted to the GeneratedPicture table so the user can
browse and reuse past pictures without re-paying for generation.
"""

import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.llm.client import grok

log = logging.getLogger(__name__)
_settings = get_settings()


@dataclass
class LearningScene:
    key: str
    topic_lv: str
    topic_ru: str
    prompt_lv: str
    image_prompt: str


SCENES: list[LearningScene] = [
    LearningScene(
        "cafe",
        "Kafejnīcā",
        "В кафе",
        "Paskaties uz attēlu. Kas notiek kafejnīcā? Cik cilvēku un ko viņi dzer?",
        "Realistic photograph of a cozy cafe interior, 2-3 customers at wooden "
        "tables drinking coffee and eating pastries, one barista behind the "
        "counter, warm daylight, clear scene with visible details: cups, "
        "pastries, chairs, window. Natural lighting, not crowded.",
    ),
    LearningScene(
        "kitchen",
        "Virtuvē",
        "На кухне",
        "Kas gatavo ēdienu? Kādas sastāvdaļas tu redzi uz galda?",
        "Clean realistic photograph of a home kitchen: a person chopping "
        "vegetables on a wooden cutting board, tomatoes, onions, carrots and "
        "bread visible on the counter, a pot on the stove, daylight through a "
        "window. Friendly, uncluttered, educational style.",
    ),
    LearningScene(
        "market",
        "Tirgū",
        "На рынке",
        "Ko pārdod šajā tirgū? Kādas krāsas un produktus tu redzi?",
        "Open-air farmers market stall with a smiling vendor arranging fresh "
        "vegetables and fruits in wooden crates: red apples, yellow bananas, "
        "tomatoes, green cucumbers, bread, flowers in a bucket. One customer "
        "chooses produce. Bright daytime, clear colors, uncluttered.",
    ),
    LearningScene(
        "family",
        "Ģimene pie galda",
        "Семья за столом",
        "Ko dara ģimene? Kas uz galda, un kāds ir viņu noskaņojums?",
        "Warm photograph of a family of 3-4 having dinner at a wooden table: "
        "parents and children, soup and bread on the table, glasses of water, "
        "everyone smiling and talking, soft evening light. Simple realistic "
        "scene, homey atmosphere.",
    ),
    LearningScene(
        "classroom",
        "Klasē",
        "В классе",
        "Kas notiek klasē? Ko dara skolotājs un skolēni?",
        "Realistic classroom photograph: a teacher writing on a whiteboard, "
        "5-6 students sitting at desks with notebooks and pencils, a world "
        "map on the wall, daylight from windows. Calm, educational, visible "
        "details.",
    ),
    LearningScene(
        "doctor",
        "Pie ārsta",
        "У врача",
        "Ko dara ārsts un pacients? Kas atrodas telpā?",
        "Realistic photograph of a doctor in a white coat talking with a "
        "seated patient in a modern clinic office: stethoscope, clipboard, a "
        "medical cabinet in the background, bright daylight. Friendly, clearly "
        "visible faces and objects.",
    ),
    LearningScene(
        "shop",
        "Veikalā",
        "В магазине",
        "Ko cilvēki pērk? Kas uz plauktiem?",
        "Realistic photograph inside a small grocery store: shelves with "
        "bread, milk cartons, canned goods, vegetables; a customer with a "
        "basket choosing items, a cashier at the counter. Clear lighting, "
        "educational detail.",
    ),
    LearningScene(
        "park",
        "Parkā",
        "В парке",
        "Ko dara cilvēki parkā? Kāds laiks un gadalaiks?",
        "Realistic photograph of a city park on a sunny afternoon: a family "
        "with children playing with a dog on a grass lawn, two people jogging "
        "on a path, an elderly couple sitting on a bench with a newspaper. "
        "Green trees, blue sky, clear details.",
    ),
    LearningScene(
        "office",
        "Darbā birojā",
        "На работе в офисе",
        "Ko cilvēki dara darbā? Ar ko viņi strādā?",
        "Realistic photograph of a small modern office: 3 people sitting at "
        "desks with laptops, one standing near a whiteboard with colored "
        "sticky notes, coffee cups and papers visible, large window with city "
        "view. Bright daylight, collaborative atmosphere.",
    ),
    LearningScene(
        "station",
        "Dzelzceļa stacijā",
        "На вокзале",
        "Kur cilvēki dodas? Ko viņi nes līdzi?",
        "Realistic photograph of a train station platform: 4-5 passengers "
        "with suitcases and backpacks waiting next to a train, a big clock on "
        "the wall, station sign visible. Daylight, clear scene with many "
        "describable details.",
    ),
    LearningScene(
        "rain",
        "Uz ielas lietū",
        "На улице в дождь",
        "Kāds laiks? Ko dara cilvēki?",
        "Realistic photograph of a European city street on a rainy autumn "
        "day: people walking with colorful umbrellas, wet cobblestones "
        "reflecting light, a cafe with steamy windows, fallen yellow leaves "
        "on the ground. Moody, atmospheric.",
    ),
    LearningScene(
        "beach",
        "Pludmalē vasarā",
        "На пляже летом",
        "Ko dara cilvēki pludmalē? Kāds laiks?",
        "Realistic photograph of a sunny beach: 3-4 people on colorful "
        "towels, one child building a sandcastle, two adults playing with a "
        "beach ball, blue sea with gentle waves, clear sky, seagulls. Bright, "
        "happy, clearly visible details.",
    ),
    LearningScene(
        "gym",
        "Sporta zālē",
        "В спортзале",
        "Ko cilvēki dara sporta zālē? Kādi sporta rīki?",
        "Realistic photograph of a modern gym: one person lifting dumbbells, "
        "another on a treadmill, a third stretching on a mat; mirrors, "
        "barbells, water bottles visible. Bright overhead lighting, clear "
        "detail.",
    ),
    LearningScene(
        "festival",
        "Svētkos",
        "На празднике",
        "Kādi svētki? Ko dara cilvēki?",
        "Realistic photograph of an outdoor festival at dusk: groups of "
        "people dancing and laughing, string lights overhead, food stalls in "
        "the background, colorful banners, a live band on a small stage. "
        "Warm golden light.",
    ),
    LearningScene(
        "library",
        "Bibliotēkā",
        "В библиотеке",
        "Kas notiek bibliotēkā? Ko dara cilvēki?",
        "Realistic photograph of a warm library interior: tall wooden "
        "bookshelves, a person reading at a wooden table with a laptop and "
        "stacked books, another browsing a shelf, soft yellow lamp light, "
        "cozy atmosphere.",
    ),
]


def scene_by_key(key: str) -> LearningScene | None:
    for s in SCENES:
        if s.key == key:
            return s
    return None


async def generate_image_b64(prompt: str) -> str:
    """Generate image via Grok's image endpoint. Accepts either b64 or URL
    responses from the SDK (field depends on model)."""
    try:
        resp = await grok.images.generate(
            model=_settings.xai_image_model,
            prompt=prompt,
            n=1,
        )
    except Exception:
        log.exception("Grok image generation failed")
        raise

    item = resp.data[0]

    b64 = getattr(item, "b64_json", None)
    if b64:
        return b64

    url = getattr(item, "url", None)
    if url:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return base64.b64encode(r.content).decode()

    raise RuntimeError("image provider returned neither b64 nor URL")
