"""Curated Latvian minimal pairs (short vs long vowels, palatalized vs plain).

Each entry targets one phonetic contrast that Russian speakers often miss.
Use `note_ru` to explain what to listen for.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MinimalPair:
    a: str
    b: str
    a_ru: str
    b_ru: str
    note_ru: str


PAIRS: list[MinimalPair] = [
    # Short vs long vowels — the classic Latvian trap.
    MinimalPair("maja", "māja", "(не слово)", "дом", "Долгое ā — тяни вдвое дольше."),
    MinimalPair("rīts", "rits", "утро", "(не слово)", "Долгое ī в начале."),
    MinimalPair("kakls", "kāklis", "шея", "(вариант)", "Протяжное ā меняет смысл."),
    MinimalPair("mute", "mūte", "рот", "(не слово)", "Долгое ū."),
    MinimalPair("zale", "zāle", "(не слово)", "зал / трава", "Долгое ā."),
    MinimalPair("tev", "tēv", "тебе", "(отец, сокр.)", "ē против e — заметь длину."),
    MinimalPair("pils", "pīle", "замок", "утка", "Короткое i vs долгое ī."),
    MinimalPair("salds", "sāls", "сладкий", "соль", "Короткое a vs долгое ā."),
    MinimalPair("sapņi", "sapnis", "сны (мн.ч.)", "сон", "ņ мягкое против n твёрдого."),
    MinimalPair("tu", "tū", "ты", "(не слово)", "Долгое ū."),
    MinimalPair("sile", "zile", "корыто", "синица", "s vs z в начале."),

    # Palatalized vs plain consonants.
    MinimalPair("kaļķi", "kalki", "известь", "кальки", "ļ мягкое, k после ļ → ķ."),
    MinimalPair("ņem", "nem", "возьми", "(не слово)", "ņ — мягкое н, язык к нёбу."),
    MinimalPair("ļauj", "lauj", "разреши", "(не слово)", "ļ — мягкое л."),
    MinimalPair("kāpj", "kāp", "лезет", "лезь! (пов.)", "Разные формы глагола."),
    MinimalPair("ģimene", "gimene", "семья", "(не слово)", "ģ — мягкое г, как в русском «день»."),
    MinimalPair("ķirbis", "kirbis", "тыква", "(не слово)", "ķ — мягкое к."),

    # Š vs s, ž vs z, č vs c.
    MinimalPair("šis", "sis", "этот", "(не слово)", "š — как «ш»."),
    MinimalPair("žurka", "zurka", "крыса", "(не слово)", "ž — как «ж»."),
    MinimalPair("čau", "cau", "привет/пока", "(не слово)", "č — как «ч»."),
    MinimalPair("šaut", "saut", "стрелять", "(не слово)", "š в начале."),

    # Common word pairs learners confuse.
    MinimalPair("labi", "labs", "хорошо", "хороший", "Наречие vs прилагательное."),
    MinimalPair("tēvs", "tēva", "отец (им.)", "отца (род.)", "Окончание падежа."),
    MinimalPair("māte", "māti", "мать (им.)", "мать (вин.)", "Окончание падежа."),
    MinimalPair("mājā", "mājas", "дома (лок.)", "дома (род.) / домá", "Разные падежи."),
    MinimalPair("pie", "pēc", "у / около", "после", "Похожие предлоги — разный смысл."),
    MinimalPair("runāt", "redzēt", "говорить", "видеть", "Два частых глагола."),
    MinimalPair("sakot", "sākot", "говоря (дееприч.)", "начиная", "Долгое ā меняет смысл."),

    # Tricky consonant clusters.
    MinimalPair("sveiki", "sviest", "привет", "бросить", "Разные начала."),
    MinimalPair("vīrs", "virs", "мужчина", "над (предлог)", "Длина ī."),
    MinimalPair("viens", "vēns", "один", "(не слово, для тренировки)", "ie vs ē."),

    # Loaned / hard pronunciations.
    MinimalPair("Rīga", "riga", "Рига", "(не слово)", "Долгое ī."),
    MinimalPair("Jūrmala", "Jurmala", "Юрмала", "(не слово)", "ū — тяни."),
    MinimalPair("paldies", "palidas", "спасибо", "(не слово)", "Правильная длина."),

    # Dialogue essentials.
    MinimalPair("jā", "ja", "да", "если", "ā долгое → «да»; короткое → «если»."),
    MinimalPair("nē", "ne", "нет", "не (частица)", "Долгое ē → «нет»."),
    MinimalPair("ko", "kā", "что (вин.)", "как", "Разные вопросительные."),
]
