"""Catalog of scenarios (daily life) and exam topics."""

from dataclasses import dataclass


@dataclass
class Scenario:
    key: str
    title_lv: str
    title_ru: str
    kind: str  # "exam" | "daily"
    context: str  # Short rolling context for the system prompt


EXAM_TOPICS: list[Scenario] = [
    Scenario("gimene", "Ģimene un draugi", "Семья и друзья", "exam",
             "Ты расспрашиваешь ученика о его семье, родителях, братьях/сёстрах, друзьях, отношениях, семейных традициях."),
    Scenario("dzivesvieta", "Mana dzīvesvieta", "Моё жильё, район, соседи", "exam",
             "Беседа о квартире/доме ученика, районе, Риге/городе проживания, соседях, что нравится/не нравится."),
    Scenario("ikdiena", "Mana ikdiena", "Мой распорядок дня", "exam",
             "Расспрос о типичном дне: утро, работа, ужин, выходные, хобби в будни."),
    Scenario("darbs", "Darbs un studijas", "Работа и учёба", "exam",
             "Работа/профессия ученика, чем занимается, что нравится, коллеги, учёба в прошлом, планы."),
    Scenario("brivais_laiks", "Brīvais laiks un hobiji", "Досуг и хобби", "exam",
             "Хобби, спорт, фильмы, книги, что делаешь на выходных, с кем проводишь свободное время."),
    Scenario("celojumi", "Ceļojumi, Latvijas vietas", "Путешествия, места в Латвии", "exam",
             "Путешествия, любимые места в Латвии (Рига, Юрмала, Лиепая, Сигулда и др.), что посоветовал бы показать туристу."),
    Scenario("edins", "Ēdiens un iepirkšanās", "Еда и покупки", "exam",
             "Любимая еда, латвийская кухня, где покупаешь продукты, готовишь ли дома, рестораны/кафе."),
    Scenario("veseliba", "Veselība, pie ārsta", "Здоровье, у врача", "exam",
             "Здоровый образ жизни, спорт, поход к врачу, аптека, как описать симптомы."),
    Scenario("laikapstakli", "Laikapstākļi, gadalaiki", "Погода, времена года", "exam",
             "Погода сегодня, любимое время года, климат в Латвии, сравнение с другими странами."),
    Scenario("svetki", "Latvijas svētki un tradīcijas", "Праздники и традиции Латвии", "exam",
             "Jāņi, Līgo, Ziemassvētki, Lieldienas, 18. novembris, народные традиции, как празднуешь."),
    Scenario("transports", "Sabiedriskais transports", "Общественный транспорт", "exam",
             "Как добираешься по городу, автобус/троллейбус/машина, плюсы-минусы каждого, проблемы общ. транспорта в Риге."),
    Scenario("jaunumi", "Jaunumi, aktuāli notikumi", "Новости, актуальные события", "exam",
             "Что происходит в Латвии/мире, откуда берёшь новости, что думаешь об актуальных событиях."),
    Scenario("planii", "Mani plāni un viedoklis", "Мои планы и мнения", "exam",
             "Планы на ближайший год, мечты, мнение по общим темам (экология, технологии, образование)."),
]

DAILY_SITUATIONS: list[Scenario] = [
    Scenario("kafejnica", "Kafejnīca / restorāns", "Кафе / ресторан", "daily",
             "Ты официант в латышском кафе. Встречаешь ученика, предлагаешь меню, принимаешь заказ, советуешь блюдо."),
    Scenario("veikals", "Veikals, tirgus", "Магазин, рынок", "daily",
             "Ты продавец в продуктовом магазине / на рынке. Помогаешь ученику найти товар, обсуждаете цены и свежесть."),
    Scenario("cels", "Ceļa jautāšana", "Как пройти / транспорт", "daily",
             "Ты прохожий в Риге. Ученик спрашивает дорогу, автобусную остановку, как добраться до места."),
    Scenario("telefons", "Pa telefonu", "По телефону", "daily",
             "Ты регистратор (поликлиника / автосервис / парикмахерская). Ученик звонит записаться на приём."),
    Scenario("kaimini", "Small talk ar kaimiņiem", "Small talk с соседями", "daily",
             "Ты сосед ученика, встретились в лифте/у подъезда. Лёгкий разговор о погоде, выходных, новостях дома."),
    Scenario("brivais_cats", "Brīvais čats", "Свободный разговор", "daily",
             "Ты дружелюбный собеседник. Тему задаёт ученик — поддерживай её."),
]

HIDDEN_SCENARIOS: list[Scenario] = [
    Scenario(
        "picture_desc",
        "Apraksti attēlu",
        "Описание картинки",
        "daily",
        "Ты — партнёр для практики описания изображений. Ученик видит картинку, "
        "но ты её НЕ видишь. Твоя задача — задавать уточняющие вопросы: кто на "
        "картинке, что делают, какое настроение, цвета, место, время года, что "
        "могло произойти до/после. Поощряй развёрнутые ответы. Будь дружелюбным.",
    ),
]

ALL_SCENARIOS = {s.key: s for s in EXAM_TOPICS + DAILY_SITUATIONS + HIDDEN_SCENARIOS}


def get_scenario(key: str) -> Scenario | None:
    return ALL_SCENARIOS.get(key)
