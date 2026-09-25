#!/usr/bin/env python3
"""Generate the static Обод site."""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PHONE_1 = "+7 495 128 40 15"
PHONE_2 = "+7 926 410 33 18"
TEL_1 = "+74951284015"
TEL_2 = "+79264103318"
ADDRESS = "Москва, Южнопортовая ул., 15, стр. 2"
HOURS = "Ежедневно с 10:00 до 21:00"

SERVICES = [
    ("uslugi/avto.html", "Покраска авто дисков", "Литые и кованые комплекты: пескоструй, грунт, цвет и лак в печи."),
    ("uslugi/moto.html", "Покраска мото дисков", "Мотоциклетные диски и спицы. Аккуратно с тонким ободом и ниппелем."),
    ("uslugi/remont.html", "Ремонт и правка дисков", "Убираем восьмёрку, вмятины и трещины до покраски, а не вместо неё."),
    ("uslugi/shiny.html", "Шиномонтажные работы", "Разбортовка, балансировка и сборка комплекта, пока диски в цеху."),
    ("uslugi/akva.html", "Аквабластинг", "Мягкая очистка водой и абразивом, если песок слишком агрессивен."),
    ("uslugi/supporta.html", "Покраска суппортов", "Термостойкая краска на суппорта: цвет в тон дискам или контрастом."),
    ("uslugi/protochka.html", "Алмазная проточка", "Ровная зеркальная полка обода, затем порошок или лак по желанию."),
    ("uslugi/prochee.html", "Другие услуги", "Насадки, кронштейны, мелкая сталь и детали, которым нужна печь."),
    ("uslugi/aksessuary.html", "Аксессуары", "Кольца, заглушки, колпачки и болты — подберём под посадочное место."),
]

PAINT = [
    (13, 9600), (14, 9600), (15, 9800), (16, 10400), (17, 11600), (18, 12800),
    (19, 14000), (20, 15400), (21, 16600), (22, 18200), (23, 19600), (24, 21000),
]
REPAIR = [
    (13, 1400), (14, 1500), (15, 1600), (16, 1800), (17, 2000), (18, 2300),
    (19, 2600), (20, 3000), (21, 3400), (22, 3900), (23, 4400), (24, 4900),
]

WORKS = [
    ("silver", "Серебро", "Audi A6 · R18", "#d5d7dc", "#f2f2f2", "#2b2b2b", True),
    ("black-gloss", "Чёрный глянец", "BMW X5 · R20", "#161616", "#0e0e0e", "#000", True),
    ("black-matte", "Чёрный мат", "Volkswagen Tiguan · R18", "#2a2a2a", "#1f1f1f", "#111", False),
    ("graphite-gloss", "Графит глянец", "Mercedes E · R19", "#4d535a", "#6a7178", "#1a1c1f", True),
    ("graphite-matte", "Графит мат", "Toyota Camry · R17", "#5e656c", "#727980", "#222", False),
    ("color", "Красный", "Mazda 3 · R18", "#e10305", "#ff4d4f", "#4a0001", True),
    ("color", "Синий", "Subaru WRX · R18", "#1d4e89", "#3d74b5", "#0c2038", True),
    ("color", "Бронза", "Lexus RX · R20", "#8d6236", "#c4925a", "#2c1c0e", True),
    ("silver", "Полированный обод", "Porsche Cayenne · R21", "#ececec", "#fff", "#3a3a3a", True),
    ("black-gloss", "Чёрный с красным кантом", "Skoda Octavia · R17", "#101010", "#1a1a1a", "#5a0000", True),
    ("color", "Белый глянец", "Mini Cooper · R17", "#f4f4f4", "#fff", "#cfcfcf", True),
    ("graphite-matte", "Тёмная бронза мат", "Land Cruiser · R20", "#6b5344", "#8a7362", "#241910", False),
]

REVIEWS = [
    ("Алексей", "Kia K5 · чёрный глянец R17", "Привёз диски с паутинкой по кромке. После песка и покраски полка стала ровной, цвет без шагрени. Забрал на следующий день."),
    ("Марина", "BMW 3 · графит мат R18", "Нужен был спокойный мат, без «пластика». Попали в оттенок с образца. На мойке покрытие не помутнело."),
    ("Игорь", "Volkswagen Tiguan · правка и серебро", "Один диск пришёл восьмёркой после ямы. Сначала выправили, потом покрасили весь комплект, чтобы не отличался."),
    ("Ольга", "Mazda CX-5 · красные суппорта", "Диски оставили графитом, суппорта выкрасили в красный. Смотрится собранно, запах краски выветрился до выдачи."),
    ("Денис", "Мотодиск · чёрный мат", "Красили задний диск мотоцикла. Спицы не залили, ниппель живой. По сроку уложились в обещанное окно."),
    ("Сергей", "Toyota Camry · R16", "Считал, что порошок только для больших радиусов. На R16 цена комплекта была понятна сразу, без доплат на кассе."),
]

STEPS = [
    ("01", "Приём в работу", "Смотрим геометрию, трещины и старое покрытие. Говорим, что войдёт в цену, а что лучше править отдельно."),
    ("02", "Пескоструйная обработка", "Снимаем лак, окислы и рыхлую краску до металла. Так порошок держится, а не лежит на чужом слое."),
    ("03", "Подготовка диска", "Убираем сколы и острые кромки. Если не хватает металла, наплавляем участок до шлифовки."),
    ("04", "Термообработка поверхности", "Выгоняем масло из пор и обезжириваем. Без этого грунт отходит пятнами уже в первую зиму."),
    ("05", "Грунтовый слой", "Кладём порошковый грунт и запекаем. Он закрывает металл и выравнивает мелкую риску."),
    ("06", "Полимеризация краски", "Наносим цвет и держим диск в печи, пока порошок не станет единой плёнкой."),
    ("07", "Финишный слой", "Глянцевый или матовый лак — по образцу. Мат не покрываем глянцем «для прочности»."),
    ("08", "Контрольный осмотр", "Проверяем кромку, посадочную плоскость и отверстия. Отдаём диск чистым, без дроби в вентиляции."),
]

PERKS = [
    ("01", "Один цех", "Песок, правка, покраска и шиномонтаж происходят у нас. Диск не ездит между подрядчиками."),
    ("02", "Срок", "Экспресс-окно — 10 часов на комплект без сложного ремонта. Если нужна наплавка, срок называем на приёме."),
    ("03", "Материалы", "Порошок и лак с нормальной температурой полимеризации, не баллон из магазина."),
    ("04", "Люди", "Диски ведут маляры, которые каждый день красят обода, а не кузов «между делом»."),
    ("05", "Повторные визиты", "Постоянным клиентам фиксируем скидку и на партнёрский шиномонтаж, если резину удобнее менять рядом."),
    ("06", "Гарантия 3 года", "На порошковое покрытие при обычной эксплуатации. Гарантия не про сколы от бордюра и реагента на голом металле."),
]


def money(value):
    return f"{value:,}".replace(",", " ") + " ₽"


def wheel():
    spokes = []
    for i in range(5):
        for delta in (-9, 9):
            angle = i * 72 + delta
            spokes.append(
                f'<polygon points="100,30 112,90 100,78 88,90" fill="var(--spoke,#e6e6e6)" transform="rotate({angle} 100 100)"/>'
            )
    lugs = []
    for i in range(5):
        rad = math.radians(i * 72 - 90)
        x = 100 + 15 * math.cos(rad)
        y = 100 + 15 * math.sin(rad)
        lugs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#b5b5b5"/>')
    spokes_svg = "".join(spokes)
    lugs_svg = "".join(lugs)
    return f'''<svg class="wheel" viewBox="0 0 200 200" aria-hidden="true">
      <circle cx="100" cy="100" r="98" fill="var(--lip,#111)"/>
      <circle cx="100" cy="100" r="90" fill="var(--rim,#cfcfcf)"/>
      <circle cx="100" cy="100" r="79" fill="#141414"/>
      {spokes_svg}
      <circle cx="100" cy="100" r="92" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1.5"/>
      <circle cx="100" cy="100" r="23" fill="#0e0e0e"/>
      {lugs_svg}
      <circle cx="100" cy="100" r="5.5" fill="var(--cap,#e10305)"/>
    </svg>'''


def work_card(item):
    cat, title, caption, rim, spoke, lip, gloss = item
    gloss_html = '<span class="work__gloss"></span>' if gloss else ""
    return f'''<figure class="work" data-cat="{cat}" style="--rim:{rim};--spoke:{spoke};--lip:{lip}">
      <div class="work__shot">{wheel()}{gloss_html}</div>
      <figcaption><strong>{title}</strong><span>{caption}</span></figcaption>
    </figure>'''


def price_tables(rows, first_label, row_label):
    chunks = [rows[:6], rows[6:]]
    blocks = [price_table(chunk, first_label, row_label) for chunk in chunks if chunk]
    return '<div style="display:grid;gap:12px;">' + "".join(blocks) + "</div>"


def price_table(rows, first_label, row_label):
    head = "".join(f"<th>R{size}</th>" for size, _ in rows)
    body = "".join(f"<td>{money(price)}</td>" for _, price in rows)
    return f'''<div class="table-wrap"><table>
      <thead><tr><th>{first_label}</th>{head}</tr></thead>
      <tbody><tr><td>{row_label}</td>{body}</tr></tbody>
    </table></div>'''


def options_sizes():
    return "".join(f'<option value="{size}">R{size} — {money(price)} за 4 диска</option>' for size, price in PAINT)


def calc_box():
    return f'''<form class="calc" data-calc data-lead>
      <div>
        <h3 class="calc__title">Калькулятор комплекта</h3>
        <p class="lead" style="color:#5c5c5c;margin:8px 0 16px;">Цена за четыре диска одного диаметра. Скидка 10% считается сразу.</p>
        <label class="field"><span>Диаметр</span>
          <select data-size name="size">{options_sizes()}</select>
        </label>
        <label class="check"><input type="checkbox" data-discount checked> Посчитать со скидкой 10%</label>
        <div class="total">
          <small>Без скидки <span data-base>9 600 ₽</span></small>
          <strong data-total>8 640 ₽</strong>
          <small>за комплект из 4 дисков</small>
        </div>
      </div>
      <div>
        <div class="form-ok">Заявка принята. Перезвоним и подтвердим окно и цвет.</div>
        <label class="field"><span>Имя</span><input name="name" autocomplete="name" required></label>
        <label class="field"><span>Телефон</span><input name="phone" data-phone inputmode="tel" autocomplete="tel" required></label>
        <label class="check"><input type="checkbox" name="agree" required> Согласен с <a href="privacy.html">политикой конфиденциальности</a></label>
        <p class="form-error" role="alert"></p>
        <button class="btn btn--block" type="submit">Оставить заявку</button>
      </div>
    </form>'''


def shell(prefix, title, description, active, body):
    def url(path):
        return prefix + path

    service_links = "".join(
        f'<li><a href="{url(href)}">{label}</a></li>' for href, label, _ in SERVICES
    )
    footer_services = "".join(
        f'<a href="{url(href)}">{label}</a>' for href, label, _ in SERVICES
    )

    def active_attr(key):
        return ' class="is-active"' if active == key else ""

    modal_privacy = url("privacy.html")
    service_options = "".join(
        f'<option>{label}</option>' for _, label, _ in SERVICES
    )
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="icon" href="{url("img/favicon.svg")}" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{url("css/styles.css")}">
</head>
<body>
  <a class="skip" href="#main">К содержанию</a>
  <header class="header">
    <div class="container header__row">
      <a class="logo" href="{url("index.html")}"><span class="logo__mark" aria-hidden="true"></span>ОБОД</a>
      <button class="burger" id="burger" type="button" aria-label="Открыть меню" aria-expanded="false"><span></span><span></span><span></span></button>
      <nav class="nav" id="nav">
        <ul class="nav__list">
          <li class="nav__item nav__item--sub">
            <a{active_attr("services")} href="{url("uslugi/avto.html")}">Услуги</a>
            <ul class="nav__sub">{service_links}</ul>
          </li>
          <li><a{active_attr("ceny")} href="{url("ceny.html")}">Цены</a></li>
          <li><a{active_attr("raboty")} href="{url("raboty.html")}">Наши работы</a></li>
          <li><a{active_attr("otzyvy")} href="{url("otzyvy.html")}">Отзывы</a></li>
          <li><a{active_attr("kontakty")} href="{url("kontakty.html")}">Контакты</a></li>
          <li><a{active_attr("about")} href="{url("o-kompanii.html")}">О компании</a></li>
        </ul>
        <div class="nav__phones">
          <a href="tel:{TEL_1}">{PHONE_1}</a>
          <a href="tel:{TEL_2}">{PHONE_2}</a>
        </div>
      </nav>
      <div class="header__side">
        <div class="phones">
          <a href="tel:{TEL_1}">{PHONE_1}</a>
          <a href="tel:{TEL_2}">{PHONE_2}</a>
        </div>
        <button class="btn btn--sm" type="button" data-modal="modal-book">Записаться</button>
      </div>
    </div>
  </header>
  <main id="main">
    {body}
  </main>
  <footer class="footer">
    <div class="container footer__grid">
      <div>
        <h2>ОБОД</h2>
        <p>Порошковая покраска дисков в Москве. Пескоструй, печь, правка и выдача в одном цехе.</p>
        <p style="margin-top:12px;"><a href="tel:{TEL_1}">{PHONE_1}</a><a href="tel:{TEL_2}">{PHONE_2}</a></p>
        <p style="margin-top:8px;">{ADDRESS}<br>{HOURS}</p>
      </div>
      <div>
        <h2>Услуги</h2>
        {footer_services}
      </div>
      <div>
        <h2>Клиенту</h2>
        <a href="{url("ceny.html")}">Цены и калькулятор</a>
        <a href="{url("raboty.html")}">Наши работы</a>
        <a href="{url("otzyvy.html")}">Отзывы</a>
        <a href="{url("kontakty.html")}">Как добраться</a>
        <a href="{url("o-kompanii.html")}">О компании</a>
        <a href="{url("privacy.html")}">Политика конфиденциальности</a>
      </div>
    </div>
    <div class="container footer__bottom">
      <span>© 2016–2026 Обод</span>
      <span>Порошковая покраска дисков</span>
    </div>
  </footer>
  <button class="btn float-call" type="button" data-modal="modal-call">Есть вопросы?</button>
  <div class="modal" id="modal-book" role="dialog" aria-modal="true" aria-labelledby="book-title">
    <div class="modal__card">
      <button class="modal__x" type="button" data-close aria-label="Закрыть">×</button>
      <h2 id="book-title">Запись в цех</h2>
      <p class="lead">Оставьте имя и телефон. Перезвоним, уточним диаметр и подберём свободное окно.</p>
      <form data-lead>
        <div class="form-ok">Заявка принята. Мы свяжемся с вами.</div>
        <label class="field"><span>Имя</span><input name="name" autocomplete="name" required></label>
        <label class="field"><span>Телефон</span><input name="phone" data-phone inputmode="tel" autocomplete="tel" required></label>
        <label class="field"><span>Услуга</span><select name="service">{service_options}</select></label>
        <label class="check"><input type="checkbox" name="agree" required> Согласен с <a href="{modal_privacy}">политикой конфиденциальности</a></label>
        <p class="form-error" role="alert"></p>
        <button class="btn btn--block" type="submit">Отправить заявку</button>
      </form>
    </div>
  </div>
  <div class="modal" id="modal-discount" role="dialog" aria-modal="true" aria-labelledby="discount-title">
    <div class="modal__card">
      <button class="modal__x" type="button" data-close aria-label="Закрыть">×</button>
      <h2 id="discount-title">Скидка 10%</h2>
      <p class="lead">Закрепим скидку на покраску комплекта, если запишетесь по этой заявке.</p>
      <form data-lead>
        <div class="form-ok">Скидка отмечена. Перезвоним и назовём итог по вашему радиусу.</div>
        <label class="field"><span>Имя</span><input name="name" autocomplete="name" required></label>
        <label class="field"><span>Телефон</span><input name="phone" data-phone inputmode="tel" autocomplete="tel" required></label>
        <label class="check"><input type="checkbox" name="agree" required> Согласен с <a href="{modal_privacy}">политикой конфиденциальности</a></label>
        <p class="form-error" role="alert"></p>
        <button class="btn btn--block" type="submit">Получить скидку</button>
      </form>
    </div>
  </div>
  <div class="modal" id="modal-call" role="dialog" aria-modal="true" aria-labelledby="call-title">
    <div class="modal__card">
      <button class="modal__x" type="button" data-close aria-label="Закрыть">×</button>
      <h2 id="call-title">Мы перезвоним</h2>
      <p class="lead">Короткий вопрос по сроку, цвету или ремонту — оставьте номер.</p>
      <form data-lead>
        <div class="form-ok">Номер получили. Перезвоним в рабочее время.</div>
        <label class="field"><span>Телефон</span><input name="phone" data-phone inputmode="tel" autocomplete="tel" required></label>
        <input type="hidden" name="name" value="Звонок">
        <label class="check"><input type="checkbox" name="agree" required> Согласен с <a href="{modal_privacy}">политикой конфиденциальности</a></label>
        <p class="form-error" role="alert"></p>
        <button class="btn btn--block" type="submit">Жду звонка</button>
      </form>
    </div>
  </div>
  <div class="cookie" id="cookie">
    <p>Сайт запоминает только факт, что вы закрыли это уведомление. Заявки с форм на сервер не отправляются.</p>
    <button class="btn btn--sm" id="cookie-ok" type="button">Понятно</button>
  </div>
  <script src="{url("js/main.js")}"></script>
</body>
</html>
'''


def page_hero(crumbs, title, lead):
    return f'''<section class="page-hero"><div class="container">
      <p class="crumbs">{crumbs}</p>
      <h1>{title}</h1>
      <p>{lead}</p>
    </div></section>'''


def index_page():
    cards = "".join(
        f'''<a class="card" href="{href}">
          <div class="card__icon">{wheel()}</div>
          <h3>{title}</h3>
          <p>{text}</p>
          <span class="card__more">Подробнее</span>
        </a>'''
        for href, title, text in SERVICES
    )
    kinds = [
        ("Литые диски", "#d0d0d0", "#eee", "#222"),
        ("Кованые диски", "#b7b7b7", "#dedede", "#111"),
        ("Штампованные", "#8d9399", "#b0b6bc", "#222"),
        ("Диски мотоцикла", "#1b1b1b", "#111", "#000"),
        ("Суппорта", "#e10305", "#ff5a5c", "#4a0000"),
        ("Выхлопные насадки", "#c6a15b", "#ead7ae", "#3a2a12"),
        ("Силовые бампера", "#333", "#4a4a4a", "#111"),
        ("Колпачки", "#f7f7f7", "#fff", "#ddd"),
    ]
    kinds_html = "".join(
        f'''<article class="kind" style="--rim:{rim};--spoke:{spoke};--lip:{lip}">{wheel()}<strong>{name}</strong></article>'''
        for name, rim, spoke, lip in kinds
    )
    perks = "".join(
        f'''<article class="perk"><div class="perk__n">{num}</div><h3>{title}</h3><p>{text}</p></article>'''
        for num, title, text in PERKS
    )
    steps = "".join(
        f'''<li><div class="steps__n">{num}</div><div><h3>{title}</h3><p>{text}</p></div></li>'''
        for num, title, text in STEPS
    )
    works = "".join(work_card(item) for item in WORKS[:8])
    reviews = "".join(
        f'''<article class="review"><div class="stars" aria-label="5 из 5">★★★★★</div><p>{text}</p><div class="review__who">{name}</div><div class="review__car">{car}</div></article>'''
        for name, car, text in REVIEWS[:3]
    )
    filters = '''
      <div class="filters">
        <button class="filter is-active" type="button" data-filter="all">Все</button>
        <button class="filter" type="button" data-filter="silver">Серебро</button>
        <button class="filter" type="button" data-filter="black-gloss">Чёрный глянец</button>
        <button class="filter" type="button" data-filter="black-matte">Чёрный мат</button>
        <button class="filter" type="button" data-filter="graphite-gloss">Графит глянец</button>
        <button class="filter" type="button" data-filter="graphite-matte">Графит мат</button>
        <button class="filter" type="button" data-filter="color">Цветные</button>
      </div>'''
    return f'''
    <section class="hero">
      <div class="container hero__grid">
        <div>
          <p class="eyebrow">Москва · цех с 2016 года</p>
          <h1>Порошковая<br>покраска <span>дисков</span></h1>
          <p class="hero__lead">Возвращаем ободу ровный цвет и плотную плёнку: пескоструй, грунт, печь и лак. Экспресс на комплект — 10 часов, гарантия на покраску — 3 года.</p>
          <ul class="ticks">
            <li>Работаем с 2016 года</li>
            <li>Экспресс-покраска за 10 часов</li>
            <li>Гарантия на покрытие — 3 года</li>
            <li>Цех в ЮВАО, Южнопортовая улица</li>
          </ul>
          <div class="hero__actions">
            <a class="btn" href="ceny.html">Рассчитать стоимость</a>
            <button class="btn btn--ghost" type="button" data-modal="modal-discount">Скидка 10%</button>
          </div>
        </div>
        <div class="stage" style="--rim:#141414;--spoke:#0d0d0d;--lip:#000">
          {wheel()}
          <span class="work__gloss"></span>
          <p class="stage__cap">Чёрный глянец · R19</p>
        </div>
      </div>
    </section>
    <section class="promo">
      <div class="container promo__row">
        <div>
          <strong>Скидка 10% на покраску дисков</strong>
          <p>Оставьте номер — закрепим цену комплекта и свободное окно.</p>
        </div>
        <button class="btn btn--light" type="button" data-modal="modal-discount">Получить скидку</button>
      </div>
    </section>
    <section class="section" id="services">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Услуги</p>
            <h2>Что делаем с колесом</h2>
          </div>
          <p class="section__note">Основная работа — порошок. Рядом правка, проточка, суппорта и резина, чтобы не собирать маршрут по городу.</p>
        </div>
        <div class="cards">{cards}</div>
      </div>
    </section>
    <section class="section section--gray">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Цех</p>
            <h2>Что мы красим</h2>
          </div>
        </div>
        <div class="kinds">{kinds_html}</div>
      </div>
    </section>
    <section class="section">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Почему Обод</p>
            <h2>Преимущества</h2>
          </div>
        </div>
        <div class="perks">{perks}</div>
        <p class="fine">Гарантия 3 года не распространяется на штампованные диски, выхлопные насадки и силовые бампера: у этих деталей другой режим нагрева и ударов.</p>
      </div>
    </section>
    <section class="section section--black">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Как проходит заказ</p>
            <h2>Этапы работы</h2>
          </div>
        </div>
        <ol class="steps">{steps}</ol>
      </div>
    </section>
    <section class="section section--gray" id="price">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Прайс</p>
            <h2>Стоимость покраски</h2>
          </div>
          <a class="btn" href="ceny.html">Все цены</a>
        </div>
        {price_table(PAINT[:6], "Покраска", "Комплект из 4 дисков")}
        <p class="note-box">Редкий цвет и лак — доплата от 2 000 до 4 000 ₽. Если диск уже был в порошке, подготовка комплекта дороже на 3 500 ₽. Полная таблица до R24 — на странице цен.</p>
        <div style="height:24px"></div>
        {calc_box()}
      </div>
    </section>
    <section class="section" id="works">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Портфолио</p>
            <h2>Наши работы</h2>
          </div>
          <a class="btn" href="raboty.html">Смотреть все</a>
        </div>
        {filters}
        <div class="works">{works}</div>
      </div>
    </section>
    <section class="section section--gray" id="reviews">
      <div class="container">
        <div class="section__head">
          <div>
            <p class="eyebrow">Клиенты</p>
            <h2>Отзывы</h2>
          </div>
          <a class="btn" href="otzyvy.html">Все отзывы</a>
        </div>
        <div class="reviews">{reviews}</div>
      </div>
    </section>
    <section class="section" id="contacts">
      <div class="container contact-grid">
        <div class="contact-card">
          <p class="eyebrow">Цех</p>
          <h2>Как нас найти</h2>
          <div class="contact-list">
            <div><div>Адрес</div><strong>{ADDRESS}</strong></div>
            <div><div>Телефон</div><a href="tel:{TEL_1}">{PHONE_1}</a><br><a href="tel:{TEL_2}">{PHONE_2}</a></div>
            <div><div>Время</div><strong>{HOURS}</strong></div>
          </div>
          <button class="btn" type="button" data-modal="modal-book">Записаться</button>
        </div>
        <iframe class="map" title="Карта: цех Обод на Южнопортовой" src="https://www.openstreetmap.org/export/embed.html?bbox=37.665%2C55.693%2C37.705%2C55.715&amp;layer=mapnik&amp;marker=55.704%2C37.685"></iframe>
      </div>
    </section>
    '''


def ceny_page():
    other = '''
      <div class="table-wrap"><table>
        <thead><tr><th>Услуга</th><th>Цена</th></tr></thead>
        <tbody>
          <tr><td>Покраска мотодиска, от</td><td>8 000 ₽</td></tr>
          <tr><td>Покраска суппортов, ось</td><td>6 000 ₽</td></tr>
          <tr><td>Алмазная проточка полки, диск</td><td>2 800 ₽</td></tr>
          <tr><td>Аквабластинг, диск</td><td>1 600 ₽</td></tr>
          <tr><td>Шиномонтаж легкового колеса, от</td><td>700 ₽</td></tr>
          <tr><td>Металлические колпачки, комплект</td><td>4 000–6 000 ₽</td></tr>
          <tr><td>Поводки дворников</td><td>от 2 500 ₽</td></tr>
        </tbody>
      </table></div>'''
    faq = '''
      <div class="faq">
        <details open><summary>Что входит в цену комплекта?</summary><p>Снятие старого покрытия, пескоструй, обезжиривание, порошковый грунт, цвет и лак с полимеризацией. Шиномонтаж и правка считаются отдельно.</p></details>
        <details><summary>Как быстро готово?</summary><p>Комплект без ремонта — за 10 часов в экспресс-окне. Наплавка и проточка сдвигают выдачу, срок называем после осмотра.</p></details>
        <details><summary>Можно привезти свой образец цвета?</summary><p>Да. Редкие оттенки и лаки идут с доплатой от 2 000 до 4 000 ₽ за комплект.</p></details>
        <details><summary>Диски уже красились порошком. Это проблема?</summary><p>Старый порошок снимается дольше. За ранее окрашенный комплект доплата 3 500 ₽.</p></details>
        <details><summary>Нужно снимать резину?</summary><p>Для покраски обод должен быть голым. Можем снять и поставить шину у себя.</p></details>
      </div>'''
    body = page_hero(
        '<a href="index.html">Главная</a> / Цены',
        "Цены на покраску",
        "Сумма за четыре диска зависит от диаметра. Калькулятор сразу показывает скидку 10%.",
    )
    body += f'''
    <section class="section"><div class="container">
      <h2 style="margin-bottom:16px;">Покраска автомобиля, комплект</h2>
      {price_tables(PAINT, "Покраска", "4 диска")}
      <p class="note-box">Редкий цвет — от 2 000 до 4 000 ₽. Диски, которые уже были в порошке, — плюс 3 500 ₽ за комплект.</p>
      <div style="height:28px"></div>
      {calc_box()}
      <h2 style="margin:40px 0 16px;">Правка одного диска</h2>
      {price_tables(REPAIR, "Правка", "1 диск")}
      <h2 style="margin:40px 0 16px;">Другие работы</h2>
      {other}
      <h2 style="margin:40px 0 16px;">Вопросы по цене</h2>
      {faq}
    </div></section>'''
    return body


def works_page():
    filters = '''
      <div class="filters">
        <button class="filter is-active" type="button" data-filter="all">Все</button>
        <button class="filter" type="button" data-filter="silver">Серебро</button>
        <button class="filter" type="button" data-filter="black-gloss">Чёрный глянец</button>
        <button class="filter" type="button" data-filter="black-matte">Чёрный мат</button>
        <button class="filter" type="button" data-filter="graphite-gloss">Графит глянец</button>
        <button class="filter" type="button" data-filter="graphite-matte">Графит мат</button>
        <button class="filter" type="button" data-filter="color">Цветные</button>
      </div>'''
    cards = "".join(work_card(item) for item in WORKS)
    body = page_hero(
        '<a href="index.html">Главная</a> / Наши работы',
        "Наши работы",
        "Серебро, чёрный, графит и цвет. На карточке — финиш и радиус, который чаще всего так красим.",
    )
    body += f'<section class="section"><div class="container">{filters}<div class="works">{cards}</div></div></section>'
    return body


def reviews_page():
    cards = "".join(
        f'''<article class="review"><div class="stars" aria-label="5 из 5">★★★★★</div><p>{text}</p><div class="review__who">{name}</div><div class="review__car">{car}</div></article>'''
        for name, car, text in REVIEWS
    )
    body = page_hero(
        '<a href="index.html">Главная</a> / Отзывы',
        "Отзывы",
        "Короткие заметки клиентов после выдачи. Это не виджет карт: тексты собраны по разговорам в цехе.",
    )
    body += f'<section class="section"><div class="container"><div class="reviews">{cards}</div></div></section>'
    return body


def contacts_page():
    body = page_hero(
        '<a href="index.html">Главная</a> / Контакты',
        "Контакты",
        "Приезжайте с дисками или пришлите фото повреждений — скажем, нужна ли правка до покраски.",
    )
    body += f'''
    <section class="section"><div class="container split">
      <div>
        <div class="contact-list">
          <div><div>Адрес</div><strong>{ADDRESS}</strong></div>
          <div><div>Телефоны</div><a href="tel:{TEL_1}">{PHONE_1}</a><br><a href="tel:{TEL_2}">{PHONE_2}</a></div>
          <div><div>Часы</div><strong>{HOURS}</strong></div>
        </div>
        <form data-lead>
          <div class="form-ok">Сообщение принято. Ответим звонком в рабочее время.</div>
          <label class="field"><span>Имя</span><input name="name" required></label>
          <label class="field"><span>Телефон</span><input name="phone" data-phone inputmode="tel" required></label>
          <label class="field"><span>Вопрос</span><textarea name="message" placeholder="Диаметр, цвет, есть ли вмятина"></textarea></label>
          <label class="check"><input type="checkbox" name="agree" required> Согласен с <a href="privacy.html">политикой конфиденциальности</a></label>
          <p class="form-error" role="alert"></p>
          <button class="btn" type="submit">Отправить</button>
        </form>
      </div>
      <iframe class="map" title="Карта проезда" src="https://www.openstreetmap.org/export/embed.html?bbox=37.665%2C55.693%2C37.705%2C55.715&amp;layer=mapnik&amp;marker=55.704%2C37.685"></iframe>
    </div></section>'''
    return body


def about_page():
    perks = "".join(
        f'''<article class="perk"><div class="perk__n">{num}</div><h3>{title}</h3><p>{text}</p></article>'''
        for num, title, text in PERKS
    )
    body = page_hero(
        '<a href="index.html">Главная</a> / О компании',
        "О компании",
        "«Обод» с 2016 года красит и восстанавливает диски. В цех приезжают и городские седаны, и большие кроссоверы.",
    )
    body += f'''
    <section class="section"><div class="container prose">
      <p>Мы берём колесо целиком: смотрим геометрию, снимаем старую краску, правим металл, если он уехал, и только потом кладём порошок. Так цвет не маскирует трещину, а сидит на подготовленной поверхности.</p>
      <p>Печь, камера и пост правки стоят в одном помещении на Южнопортовой. Не отдаём диски «знакомому маляру» и не красим из баллона, когда клиент просил порошок.</p>
      <h2>Что решаем</h2>
      <ul>
        <li>вернуть целый вид ободу со сколами и облезшим лаком;</li>
        <li>закрыть металл плотным слоем, который держит мойку и зиму;</li>
        <li>собрать комплект в одном цвете, даже если один диск меняли;</li>
        <li>сделать спокойный мат, глянец или редкий оттенок по образцу.</li>
      </ul>
    </div></section>
    <section class="section section--gray"><div class="container"><h2 style="margin-bottom:20px;">Как устроена работа</h2><div class="perks">{perks}</div>
      <p class="fine">Гарантия 3 года не действует на штампованные диски, выхлопные насадки и силовые бампера.</p>
    </div></section>'''
    return body


def privacy_page():
    body = page_hero(
        '<a href="index.html">Главная</a> / Политика',
        "Политика конфиденциальности",
        "Какие данные вы оставляете в формах и что с ними происходит на этой версии сайта.",
    )
    body += '''
    <section class="section"><div class="container prose">
      <p>Оператор: цех «Обод», Москва, Южнопортовая ул., 15, стр. 2, телефоны +7 495 128 40 15 и +7 926 410 33 18.</p>
      <h2>Какие данные</h2>
      <p>В формах есть имя, телефон и необязательный комментарий: диаметр, цвет, вопрос. Эти поля нужны, чтобы перезвонить по заявке на покраску или ремонт.</p>
      <h2>Куда они попадают</h2>
      <p>Сейчас сайт статический. После нажатия «Отправить» данные не уходят на сервер и не сохраняются у нас: вы видите подтверждение на экране. Когда подключим почту или CRM, те же поля будут передаваться только для связи по услуге и не для рассылок.</p>
      <h2>Куки</h2>
      <p>В браузере хранится одна отметка, что уведомление о данных закрыто. Рекламных счётчиков на сайте нет.</p>
      <h2>Срок и отзыв</h2>
      <p>Если данные начнут приниматься на сервер, мы будем хранить заявку, пока не закроем вопрос по записи, и удалим её по звонку на номера цеха.</p>
    </div></section>'''
    return body


SERVICE_PAGES = {
    "uslugi/avto.html": (
        "Покраска автомобильных дисков в Москве | Обод",
        "Порошковая покраска литых и кованых дисков: пескоструй, печь, лак, цены за комплект.",
        "Покраска автомобильных дисков",
        "Красим литые и кованые диски порошком. Покрытие держит кромку лучше баллона и не облазит хлопьями после первой зимы.",
        '''<p>Порошок наносится электростатикой и запекается. Плёнка получается одной толщины на полке и у спиц, без подтёков, которые остаются от жидкой краски на сложном рельефе.</p>
        <h2>За счёт чего держится</h2>
        <ul>
          <li>прочная плёнка после полимеризации, а не мягкий слой из баллона;</li>
          <li>цвет и лак из каталога: глянец, мат, графит, серебро и отдельные оттенки;</li>
          <li>грунт закрывает металл, поэтому скол не сразу становится рыжим очагом;</li>
          <li>внешний вид комплекта собирается заново, даже если диски красились в разное время.</li>
        </ul>
        <p>На приёме смотрим, не увёл ли диск геометрию. Красить кривой обод ровным цветом можно, ездить на нём — нет. Правку предложим до печи.</p>''',
        "paint",
    ),
    "uslugi/moto.html": (
        "Покраска мото дисков | Обод",
        "Порошковая покраска мотоциклетных дисков и спицованных колёс.",
        "Ремонт и покраска мото дисков",
        "Мотообод тоньше автомобильного, поэтому песок и температуру подбираем отдельно, чтобы не повести спицы.",
        '''<p>Красим литые мотодиски и аккуратно готовим спицованные колёса: закрываем ниппель, не заливаем отверстия под спицы и не оставляем дробь внутри обода.</p>
        <p>Если на кромке есть залом после бордюра или ямы, сначала правка, потом цвет. Цена покраски мотодиска начинается от 8 000 ₽ и зависит от конструкции.</p>''',
        "note",
    ),
    "uslugi/remont.html": (
        "Ремонт и правка дисков | Обод",
        "Правка геометрии, сварка трещин и подготовка диска к покраске.",
        "Ремонт и правка дисков",
        "Снимаем радиальные и осевые биения, завариваем трещины там, где это ещё имеет смысл, и только потом красим.",
        '''<p>Диск на стенде показывает, где восьмёрка. Катаем полку, убираем вмятину проката и проверяем посадку на ступицу. Трещину у спицы не прячем краской: либо ремонт со сваркой, либо честный отказ, если диск уже не стоит возвращать на машину.</p>
        <p>Цена ниже — за один диск, не за комплект. Покраска после правки считается по таблице радиусов.</p>''',
        "repair",
    ),
    "uslugi/shiny.html": (
        "Шиномонтаж при покраске | Обод",
        "Снятие и установка шин, балансировка, пока диски в цехе покраски.",
        "Шиномонтажные работы",
        "Чтобы покрасить обод, резина должна быть снята. Делаем это у себя и собираем колесо обратно.",
        '''<p>Разбортовка, мойка посадочной полки, монтаж и балансировка. Удобно сдавать машину комплектом: утром колёса, вечером собранные и в цвете, если не нужна долгая правка.</p>
        <p>Легковое колесо — от 700 ₽ за сторону цикла «снял / поставил». Точную сумму говорим по профилю шины.</p>''',
        "note",
    ),
    "uslugi/akva.html": (
        "Аквабластинг дисков | Обод",
        "Мягкая очистка дисков водой и абразивом перед покраской или полировкой.",
        "Аквабластинг",
        "Вода с мелким абразивом снимает налёт и старый лак бережнее сухого песка. Нужен на полированных полках и тонких кромках.",
        '''<p>После аквабластинга поверхность матовая и чистая, без глубокой рытвины. Дальше можно красить порошком или оставить полку под проточку.</p>
        <p>Один диск — от 1 600 ₽. Если слой старого порошка толстый, честнее идти в пескоструй: вода будет снимать его слишком долго.</p>''',
        "note",
    ),
    "uslugi/supporta.html": (
        "Покраска суппортов | Обод",
        "Термостойкая покраска тормозных суппортов в цвет дисков или контрастом.",
        "Покраска суппортов",
        "Суппорт греется сильнее диска, поэтому берём термостойкий состав и не обещаем на него трёхлетнюю гарантию порошка.",
        '''<p>Снимаем колодки по согласованию, чистим корпус, закрываем резьбу и пыльники. Цвет — красный, жёлтый, чёрный или в тон новому диску.</p>
        <p>Ось — от 6 000 ₽. На машине суппорт не красим «вокруг диска»: только снятый, иначе пыль останется в краске.</p>''',
        "note",
    ),
    "uslugi/protochka.html": (
        "Алмазная проточка дисков | Обод",
        "Проточка полки обода алмазным резцом: ровная зеркальная кромка.",
        "Алмазная проточка дисков",
        "Резец снимает ступеньки от бордюров и даёт ровную полку. Дальше её можно оставить блестящей или закрыть лаком и порошком по лицу диска.",
        '''<p>Проточка не лечит трещину и не заменяет правку. Сначала геометрия, потом резец. На сильно изъеденной полке рез бывает уже невозможен — скажем об этом до работы.</p>
        <p>Один диск — от 2 800 ₽.</p>''',
        "note",
    ),
    "uslugi/prochee.html": (
        "Покраска деталей порошком | Обод",
        "Порошковая покраска насадок, крепежа и небольших стальных деталей.",
        "Другие услуги",
        "В ту же печь ставим выхлопные насадки, кронштейны, защиту и мелкие детали, которым нужен плотный слой, а не кисть.",
        '''<ul>
          <li>выхлопные насадки — цвет в тон дискам, без обещания трёх лет на горячем выхлопе;</li>
          <li>силовые бампера и кенгурины — пескоструй и порошок, гарантия порошка на них не действует;</li>
          <li>колпачки и поводки дворников — от 2 500 ₽.</li>
        </ul>
        <p>Привезите деталь или фото с размерами. Скажем, влезет ли она в печь.</p>''',
        "note",
    ),
    "uslugi/aksessuary.html": (
        "Аксессуары для дисков | Обод",
        "Центровочные кольца, заглушки, колпачки на болты и колёсный крепёж.",
        "Аксессуары",
        "После покраски часто не хватает мелочи: кольцо болтается, заглушка другого оттенка, колпачок потерялся на мойке.",
        '''<ul>
          <li>центровочные кольца под ступицу;</li>
          <li>заглушки в центральное отверстие;</li>
          <li>колпачки на болты и гайки;</li>
          <li>колёсные болты с нужным посадочным конусом.</li>
        </ul>
        <p>Подбираем по образцу. Металлические колпачки можем покрасить вместе с дисками: комплект 4 000–6 000 ₽.</p>''',
        "note",
    ),
}


def service_body(path, title, lead, prose, kind):
    crumb = f'<a href="../index.html">Главная</a> / {title}'
    body = page_hero(crumb, title, lead)
    extra = ""
    if kind == "paint":
        extra = f'''<h2>Стоимость комплекта</h2>{price_tables(PAINT, "Покраска", "4 диска")}
        <p class="note-box">Редкий цвет — от 2 000 до 4 000 ₽. Повторный порошок — плюс 3 500 ₽ за четыре диска. Колпачки 4 000–6 000 ₽, поводки дворников от 2 500 ₽.</p>'''
    elif kind == "repair":
        extra = f'''<h2>Стоимость правки</h2>{price_tables(REPAIR, "Правка", "1 диск")}'''
    cta = '''<p style="margin-top:24px;"><button class="btn" type="button" data-modal="modal-book">Оставить заявку</button></p>'''
    body += f'<section class="section"><div class="container prose">{prose}{extra}{cta}</div></section>'
    return body


def main():
    pages = {
        "index.html": (
            "Порошковая покраска дисков в Москве | Обод",
            "Порошковая покраска автомобильных и мото дисков в Москве: пескоструй, печь, гарантия 3 года, экспресс за 10 часов.",
            "home",
            index_page(),
        ),
        "ceny.html": (
            "Цены на покраску дисков | Обод",
            "Цены порошковой покраски дисков по диаметру, правка, суппорта и калькулятор скидки 10%.",
            "ceny",
            ceny_page(),
        ),
        "raboty.html": (
            "Наши работы | Обод",
            "Примеры порошковой покраски: серебро, чёрный глянец и мат, графит, цветные диски.",
            "raboty",
            works_page(),
        ),
        "otzyvy.html": (
            "Отзывы | Обод",
            "Отзывы клиентов цеха порошковой покраски дисков Обод.",
            "otzyvy",
            reviews_page(),
        ),
        "kontakty.html": (
            "Контакты | Обод",
            "Адрес цеха Обод: Москва, Южнопортовая ул., 15, стр. 2. Телефоны и запись на покраску дисков.",
            "kontakty",
            contacts_page(),
        ),
        "o-kompanii.html": (
            "О компании | Обод",
            "Цех Обод с 2016 года: порошковая покраска и ремонт дисков в Москве.",
            "about",
            about_page(),
        ),
        "privacy.html": (
            "Политика конфиденциальности | Обод",
            "Как цех Обод обращается с именем и телефоном из форм записи.",
            "",
            privacy_page(),
        ),
    }
    for href, (meta_title, description, title, lead, prose, kind) in SERVICE_PAGES.items():
        pages[href] = (meta_title, description, "services", service_body(href, title, lead, prose, kind))

    for rel, (title, description, active, body) in pages.items():
        prefix = "../" if rel.startswith("uslugi/") else ""
        html = shell(prefix, title, description, active, body)
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        print(rel, len(html))


if __name__ == "__main__":
    main()
