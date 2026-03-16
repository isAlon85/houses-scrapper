import time
import random
import math
import re
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.pisos.com/venta/pisos-majadahonda/"

DELAY_MIN = 40
DELAY_MAX = 60
RESULTS_PER_PAGE = 30
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
    """
    Extrae el número total de resultados del <span>92 resultados</span>
    y divide entre RESULTS_PER_PAGE.
    """
    try:
        text = driver.find_element(
            By.XPATH, "//div[@class='grid__title']/span"
        ).text.strip()

        # Extraer número: "92 resultados" -> 92
        match = re.search(r'^(\d[\d\.]*)', text)
        if match:
            total = int(match.group(1).replace('.', ''))
            pages = math.ceil(total / RESULTS_PER_PAGE)
            print(f"Total inmuebles: {total} → {pages} páginas ({RESULTS_PER_PAGE} por página)")
            return pages
        return 1
    except:
        return 1


def extract_properties_pisos(driver):
    """
    Extrae todas las propiedades de la página actual de pisos.com
    """
    properties = []

    cards = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'ad-preview')"
        " and not(contains(@class,'js-similarAd'))"
        " and not(ancestor::div[contains(@class,'ad-preview')])"
        " and not(ancestor::div[contains(@class,'zone-specialist')])]"
    )

    for card in cards:
        prop = {}

        # ID del inmueble (del atributo id del div)
        try:
            prop['id'] = card.get_attribute('id')
        except:
            prop['id'] = "N/A"

        # URL del inmueble
        try:
            href = card.get_attribute('data-lnk-href')
            prop['url'] = "https://www.pisos.com" + href \
                if href and href.startswith('/') else href or "N/A"
        except:
            prop['url'] = "N/A"

        # Título
        try:
            prop['title'] = card.find_element(
                By.XPATH, './/a[@class="ad-preview__title"]'
            ).text.strip()
        except:
            prop['title'] = "N/A"

        # Subtítulo / zona
        try:
            prop['zone'] = card.find_element(
                By.XPATH, './/p[contains(@class,"ad-preview__subtitle")]'
            ).text.strip()
        except:
            prop['zone'] = "N/A"

        # Precio
        try:
            prop['price'] = card.find_element(
                By.XPATH, './/span[contains(@class,"ad-preview__price")]'
            ).text.strip()
        except:
            prop['price'] = "N/A"

        # Habitaciones, baños, metros, planta
        prop['rooms']    = "N/A"
        prop['bathrooms'] = "N/A"
        prop['size']     = "N/A"
        prop['floor']    = "N/A"
        try:
            chars = card.find_elements(
                By.XPATH, './/p[contains(@class,"ad-preview__char")]'
            )
            for char in chars:
                text = char.text.strip()
                if "hab" in text:
                    prop['rooms'] = text
                elif "baño" in text:
                    prop['bathrooms'] = text
                elif "m²" in text:
                    prop['size'] = text
                else:
                    prop['floor'] = text
        except:
            pass

        # Descripción
        try:
            prop['description'] = card.find_element(
                By.XPATH, './/p[contains(@class,"ad-preview__description")]'
            ).text.strip()
        except:
            prop['description'] = "N/A"

        # Número de fotos
        try:
            prop['photos'] = int(card.find_element(
                By.XPATH, './/div[@class="carousel__container"]'
            ).get_attribute('data-counter'))
        except:
            prop['photos'] = 0

        properties.append(prop)

    return properties


def parse_price(price_str):
    """
    Convierte "1.180.000 €" a entero 1180000.
    """
    try:
        cleaned = re.sub(r'[^\d.]', '', price_str).replace('.', '')
        return int(cleaned)
    except:
        return None


def filter_properties(properties, min_price=MIN_PRICE, max_price=MAX_PRICE):
    filtered = []
    excluded = 0
    seen_ids = set()

    for p in properties:
        # Excluir sin título o precio
        if p['title'] == "N/A" or p['price'] == "N/A":
            excluded += 1
            continue

        # Excluir sin ID o duplicados
        if not p['id'] or p['id'] in seen_ids:
            excluded += 1
            continue

        # Parsear precio
        price_value = parse_price(p['price'])
        if price_value is None:
            excluded += 1
            continue

        # Filtrar por rango de precio
        if price_value < min_price or price_value > max_price:
            excluded += 1
            continue

        seen_ids.add(p['id'])
        p['price_value'] = price_value
        filtered.append(p)

    print(f"  → Propiedades válidas: {len(filtered)} | Excluidas: {excluded}")
    return filtered


def wait_for_cards(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'ad-preview')]")
        )
    )


def main():
    driver = get_driver()
    all_properties = []

    try:
        print(f"Navegando a {BASE_URL}...")
        driver.get(BASE_URL)

        print("\n⚠️  Si ves un captcha o verificación en el navegador, resuélvelo.")
        input("Pulsa ENTER cuando veas el listado de viviendas... ")

        wait_for_cards(driver)

        total_pages = get_total_pages(driver)
        print(f"\nTotal de páginas detectadas: {total_pages}\n")

        # Página 1
        print("Scrapeando página 1...")
        props = extract_properties_pisos(driver)
        all_properties.extend(props)
        print(f"  → {len(props)} propiedades encontradas")

        # Páginas 2 en adelante
        for page_num in range(2, total_pages + 1):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"\nEsperando {delay:.1f} seg antes de página {page_num}...")
            time.sleep(delay)

            # pisos.com usa ?numpag=2 para la paginación
            url = f"{BASE_URL}{page_num}/"
            print(f"Scrapeando página {page_num}: {url}")
            driver.get(url)

            try:
                wait_for_cards(driver)
                props = extract_properties_pisos(driver)
                all_properties.extend(props)
                print(f"  → {len(props)} propiedades encontradas")
            except Exception as e:
                print(f"  ⚠️  Error en página {page_num}: {e}")
                continue

        # Filtrar
        print("\nAplicando filtros...")
        all_properties = filter_properties(all_properties)

        # Mostrar en terminal
        print("\n" + "="*60)
        print("VIVIENDAS EN VENTA - MAJADAHONDA (pisos.com)")
        print(f"(Precio entre {MIN_PRICE:,}€ y {MAX_PRICE:,}€)")
        print("="*60 + "\n")

        for i, p in enumerate(all_properties, 1):
            print(f"[{i}] ID: {p['id']} | {p['title']}")
            print(f"    Zona        : {p['zone']}")
            print(f"    Precio      : {p['price']}")
            print(f"    Habitaciones: {p['rooms']}")
            print(f"    Baños       : {p['bathrooms']}")
            print(f"    Tamaño      : {p['size']}")
            print(f"    Planta      : {p['floor']}")
            print(f"    Fotos       : {p['photos']}")
            print(f"    URL         : {p['url']}")
            print(f"    Descripción : {p['description'][:120]}...")
            print()

        print("="*60)
        print(f"Total propiedades tras filtro: {len(all_properties)}")

        # Guardar CSV
        with open("pisoscom_majadahonda.csv", "w", newline="", encoding="utf-8") as f:
            fieldnames = ["id", "title", "zone", "price", "price_value",
                          "rooms", "bathrooms", "size", "floor",
                          "photos", "url", "description"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in all_properties:
                writer.writerow({
                    "id":           p["id"],
                    "title":        p["title"],
                    "zone":         p["zone"],
                    "price":        p["price"],
                    "price_value":  p["price_value"],
                    "rooms":        p["rooms"],
                    "bathrooms":    p["bathrooms"],
                    "size":         p["size"],
                    "floor":        p["floor"],
                    "photos":       p["photos"],
                    "url":          p["url"],
                    "description":  p["description"],
                })

        print("\n✅ Datos guardados en pisos_majadahonda.csv")
        input("\nPulsa ENTER para cerrar el navegador... ")

    finally:
        try:
            driver.service.stop()
        except Exception:
            pass
        try:
            # Evitar el OSError del __del__ de undetected-chromedriver
            driver.keep_alive = False
            driver.quit()
        except OSError:
            pass
        except Exception:
            pass


if __name__ == "__main__":
    main()
