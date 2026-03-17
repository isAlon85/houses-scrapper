import time
import random
import math
import re
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL_P1 = "https://www.habitaclia.com/viviendas-majadahonda.htm"
BASE_URL_PAGES = "https://www.habitaclia.com/viviendas-majadahonda-{}.htm"

DELAY_MIN = 35
DELAY_MAX = 55
RESULTS_PER_PAGE = 15
MIN_PRICE = 50000
MAX_PRICE = 700000


def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-ES")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
    return driver


def get_total_pages(driver):
    """Lee el total de anuncios del h2 de subtítulo y calcula páginas."""
    try:
        text = driver.find_element(
            By.CSS_SELECTOR, "aside.list-subtitle h2 span"
        ).text.strip()
        total = int(re.sub(r'[^\d]', '', text))
        pages = math.ceil(total / RESULTS_PER_PAGE)
        print(f"Total inmuebles: {total} → {pages} páginas ({RESULTS_PER_PAGE} por página)")
        return pages
    except Exception as e:
        print(f"  ⚠️ No se pudo leer total de páginas: {e}")
        return 1


def wait_for_page_load(driver, timeout=60):
    """
    Habitaclia usa SSR — el HTML viene completo desde el servidor.
    Basta con esperar a que haya al menos 1 article.js-list-item en el DOM.
    No se necesita scroll ni esperas largas.
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "article.js-list-item")
        )
    )
    time.sleep(1.5)

    n = len(driver.find_elements(By.CSS_SELECTOR, "article.js-list-item"))
    print(f"  [debug] articles detectados: {n}")


def parse_features(text):
    """
    Parsea una cadena como '177m² - 4 habitaciones - 3 baños - 4.492m²'
    y devuelve (size, rooms, bathrooms, extra).
    """
    size = "N/A"
    rooms = "N/A"
    bathrooms = "N/A"
    extra_parts = []

    parts = [p.strip() for p in text.split(' - ') if p.strip()]
    for part in parts:
        pl = part.lower()
        if re.search(r'\d+\s*m²', pl):
            if size == "N/A":
                size = part
            else:
                extra_parts.append(part)
        elif 'habitacion' in pl or 'dormitorio' in pl:
            rooms = part
        elif 'baño' in pl:
            bathrooms = part
        else:
            extra_parts.append(part)

    return size, rooms, bathrooms, ', '.join(extra_parts) if extra_parts else "N/A"


def extract_properties_habitaclia(driver):
    properties = []
    seen_ids = set()

    cards = driver.find_elements(By.CSS_SELECTOR, "article.js-list-item")
    print(f"  → Cards encontradas: {len(cards)}")

    for card in cards:
        prop = {}

        # ID y URL — habitaclia los pone en el propio article como data-*
        try:
            prop['id'] = card.get_attribute('data-id') or "N/A"
            # La URL completa está en data-href (relativa, la completamos)
            href = card.get_attribute('data-href') or ""
            if href.startswith('http'):
                prop['url'] = href.split('?')[0]
            elif href:
                prop['url'] = "https://www.habitaclia.com" + href.split('?')[0]
            else:
                prop['url'] = "N/A"
        except:
            prop['id'] = "N/A"
            prop['url'] = "N/A"

        if prop['id'] == "N/A" or prop['id'] in seen_ids:
            continue
        seen_ids.add(prop['id'])

        # Título
        try:
            prop['title'] = card.find_element(
                By.CSS_SELECTOR, "h3.list-item-title a"
            ).text.strip()
        except:
            prop['title'] = "N/A"

        # Zona
        try:
            prop['zone'] = card.find_element(
                By.CSS_SELECTOR, "p.list-item-location span"
            ).text.strip()
        except:
            prop['zone'] = "N/A"

        # Precio — itemprop="price" dentro del article
        try:
            price_elem = card.find_element(
                By.CSS_SELECTOR, "span[itemprop='price']"
            )
            prop['price'] = price_elem.text.strip()
            # Habitaclia a veces pone el valor en el atributo en lugar del texto
            if not prop['price']:
                prop['price'] = price_elem.get_attribute('content') or "N/A"
        except:
            prop['price'] = "N/A"

        # Características: "177m² - 4 habitaciones - 3 baños"
        prop['size'] = "N/A"
        prop['rooms'] = "N/A"
        prop['bathrooms'] = "N/A"
        prop['features'] = "N/A"
        try:
            feat_text = card.find_element(
                By.CSS_SELECTOR, "p.list-item-feature"
            ).text.strip()
            prop['size'], prop['rooms'], prop['bathrooms'], prop['features'] = \
                parse_features(feat_text)
        except:
            pass

        # Descripción
        try:
            prop['description'] = card.find_element(
                By.CSS_SELECTOR, "p.list-item-description"
            ).text.strip()
        except:
            prop['description'] = "N/A"

        # Número de fotos — span que contiene "35 fotos"
        try:
            foto_text = card.find_element(
                By.CSS_SELECTOR, "span.list-item-multimedia-imgvideo"
            ).text.strip()
            m = re.search(r'\d+', foto_text)
            prop['photos'] = int(m.group()) if m else 0
        except:
            prop['photos'] = 0

        # Tipo de inmueble desde data-propertysubtype
        try:
            prop['type'] = card.get_attribute('data-propertysubtype') or "N/A"
        except:
            prop['type'] = "N/A"

        properties.append(prop)

    return properties


def parse_price(price_str):
    try:
        return int(re.sub(r'[^\d]', '', price_str))
    except:
        return None


def filter_properties(properties, min_price=MIN_PRICE, max_price=MAX_PRICE):
    filtered = []
    excluded = 0
    seen_ids = set()

    for p in properties:
        if p.get('title') == "N/A" or p.get('price') == "N/A":
            excluded += 1
            continue
        if not p.get('id') or p['id'] in seen_ids:
            excluded += 1
            continue
        price_value = parse_price(p['price'])
        if price_value is None or price_value < min_price or price_value > max_price:
            excluded += 1
            continue
        seen_ids.add(p['id'])
        p['price_value'] = price_value
        filtered.append(p)

    print(f"  → Válidas: {len(filtered)} | Excluidas: {excluded}")
    return filtered


def scrape_page(driver, page_label):
    for attempt in range(1, 4):
        try:
            wait_for_page_load(driver)
        except Exception as e:
            print(f"  ⚠️ Timeout en página {page_label} (intento {attempt}): {e}")
            if attempt < 3:
                print("  ↺ Recargando en 15s...")
                time.sleep(15)
                driver.refresh()
            continue

        props = extract_properties_habitaclia(driver)

        if len(props) == 0 and attempt < 3:
            print(f"  ⚠️ 0 cards en intento {attempt}, recargando en 15s...")
            time.sleep(15)
            driver.refresh()
            continue

        print(f"  → {len(props)} propiedades extraídas en página {page_label}")
        return props

    print(f"  ✗ Página {page_label} falló tras 3 intentos.")
    return []


def main():
    driver = get_driver()
    all_properties = []

    try:
        print(f"Navegando a {BASE_URL_P1}...")
        driver.get(BASE_URL_P1)

        print("\n⚠️  Resuelve el captcha si aparece.")
        input("Pulsa ENTER cuando veas el listado de viviendas... ")

        # Página 1
        print("\nScrapeando página 1...")
        props = scrape_page(driver, "1")
        all_properties.extend(props)

        total_pages = get_total_pages(driver)
        print(f"Total páginas: {total_pages}\n")

        # Páginas 2+ — URL: viviendas-majadahonda-1.htm, -2.htm, etc.
        # La página 2 es el índice 1, página 3 es índice 2...
        for page_num in range(2, total_pages + 1):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"Esperando {delay:.1f}s antes de página {page_num}...")
            time.sleep(delay)

            url = BASE_URL_PAGES.format(page_num - 1)
            print(f"Scrapeando página {page_num}: {url}")
            driver.get(url)

            props = scrape_page(driver, str(page_num))
            all_properties.extend(props)

        # Filtro global
        print("\nAplicando filtros...")
        all_properties = filter_properties(all_properties)

        # Mostrar resultados
        print("\n" + "=" * 60)
        print("VIVIENDAS EN VENTA — MAJADAHONDA (habitaclia.com)")
        print(f"Precio entre {MIN_PRICE:,}€ y {MAX_PRICE:,}€")
        print("=" * 60 + "\n")

        for i, p in enumerate(all_properties, 1):
            print(f"[{i}] ID: {p['id']} | {p['title']}")
            print(f"     Tipo    : {p['type']}")
            print(f"     Zona    : {p['zone']}")
            print(f"     Precio  : {p['price']}")
            print(f"     Hab.    : {p['rooms']}")
            print(f"     Baños   : {p['bathrooms']}")
            print(f"     Tamaño  : {p['size']}")
            print(f"     Extras  : {p['features']}")
            print(f"     Fotos   : {p['photos']}")
            print(f"     URL     : {p['url']}")
            desc = p['description']
            print(f"     Desc.   : {desc[:120]}{'...' if len(desc) > 120 else ''}")
            print()

        print("=" * 60)
        print(f"Total propiedades: {len(all_properties)}")

        # CSV
        fieldnames = [
            "id", "type", "title", "zone", "price", "price_value",
            "rooms", "bathrooms", "size", "features",
            "photos", "url", "description"
        ]
        with open("habitaclia_majadahonda.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in all_properties:
                writer.writerow({k: p.get(k, "N/A") for k in fieldnames})

        print("\n✅ Datos guardados en habitaclia_majadahonda.csv")
        input("\nPulsa ENTER para cerrar el navegador... ")

    finally:
        try:
            driver.service.stop()
        except Exception:
            pass
        try:
            driver.keep_alive = False
            driver.quit()
        except OSError:
            pass
        except Exception:
            pass


if __name__ == "__main__":
    main()
