import time
import random
import csv
import math
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "https://www.idealista.com/venta-viviendas/majadahonda-madrid/"

DELAY_MIN = 60
DELAY_MAX = 80
RESULTS_PER_PAGE = 30
MIN_PRICE = 50000
MAX_PRICE = 700000

def get_driver():
    options = uc.ChromeOptions()
    # SIN headless para pasar Cloudflare/detección de bot
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


def get_total_pages(driver, results_per_page=RESULTS_PER_PAGE):
    """
    Detecta el número total de páginas extrayendo el total de inmuebles
    del h1 y dividiendo entre results_per_page.
    Ejemplo: "187 casas y pisos en Majadahonda" -> ceil(187/25) = 8 páginas
    """
    try:
        h1_text = driver.find_element(
            By.XPATH, "//span[@id='h1-container__text']"
        ).text.strip()

        # Extraer el número del inicio del texto
        # Ejemplo: "187 casas y pisos en Majadahonda, Madrid" -> 187
        match = re.search(r'^(\d+[\.\d]*)', h1_text)
        if match:
            total = int(match.group(1).replace('.', ''))
            pages = math.ceil(total / results_per_page)
            print(f"Total inmuebles: {total} → {pages} páginas ({results_per_page} por página)")
            return pages
        return 1
    except:
        return 1
    

def extract_properties(driver):
    """
    Extrae todas las propiedades de la página actual.
    Basado en la estructura real de idealista.com
    """
    properties = []
    property_divs = driver.find_elements(
        By.XPATH, "//article[contains(@class, 'item')]"
    )

    for div in property_divs:
        prop = {}

        # ID del inmueble (del atributo data-element-id del article)
        try:
            prop['id'] = div.get_attribute('data-element-id')
        except:
            prop['id'] = "N/A"

        # Título y URL
        try:
            link = div.find_element(By.XPATH, './/a[contains(@class,"item-link")]')
            prop['title'] = link.get_attribute('title').strip()
            href = link.get_attribute('href')
            prop['url'] = "https://www.idealista.com" + href \
                if href.startswith('/') else href
        except:
            prop['title'] = "N/A"
            prop['url'] = "N/A"

        # Precio (solo el número, sin el span del €)
        try:
            precio_text = div.find_element(
                By.XPATH, './/span[contains(@class,"item-price")]'
            ).text.replace('\n', '').strip()
            prop['price'] = precio_text
        except:
            prop['price'] = "N/A"

        # Garaje (opcional)
        try:
            prop['parking'] = div.find_element(
                By.XPATH, './/span[@class="item-parking"]'
            ).text.strip()
        except:
            prop['parking'] = None

        # Habitaciones y metros cuadrados
        prop['rooms'] = "N/A"
        prop['size'] = "N/A"
        try:
            details = div.find_elements(By.XPATH, './/span[@class="item-detail"]')
            for detail in details:
                text = detail.text.strip()
                if "hab." in text:
                    prop['rooms'] = text
                elif "m²" in text:
                    prop['size'] = text
        except:
            pass

        # Descripción corta
        try:
            prop['description'] = div.find_element(
                By.XPATH, './/div[contains(@class,"item-description")]//p'
            ).text.strip()
        except:
            prop['description'] = "N/A"

        # Tags opcionales (Villa, Ático, Planta baja, Ascensor, etc.)
        try:
            tags = div.find_elements(
                By.XPATH, './/div[@class="listing-tags-container"]//span[contains(@class,"listing-tags")]'
            )
            prop['tags'] = [t.text.strip() for t in tags if t.text.strip()]
        except:
            prop['tags'] = []

        # Agencia inmobiliaria (opcional)
        try:
            prop['agency'] = div.find_element(
                By.XPATH, './/picture[@class="logo-branding"]//a'
            ).get_attribute('title')
        except:
            prop['agency'] = None

        # Número de fotos
        try:
            counter = div.find_element(
                By.XPATH, './/div[@class="item-multimedia-pictures__counter"]/span[2]'
            )
            prop['photos'] = int(counter.text.strip())
        except:
            prop['photos'] = 0

        properties.append(prop)

    return properties


def wait_for_properties(driver, timeout=20):
    """
    Espera a que los artículos estén cargados en la página.
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'item')]"))
    )

def parse_price(price_str):
    """
    Convierte "1.700.000 €" o "350.000€" a entero 1700000.
    Devuelve None si no puede parsear.
    """
    try:
        # Quitar todo excepto dígitos y puntos
        cleaned = re.sub(r'[^\d.]', '', price_str)
        # Quitar puntos de millar
        cleaned = cleaned.replace('.', '')
        return int(cleaned)
    except:
        return None


def filter_properties(properties, min_price=MIN_PRICE, max_price=MAX_PRICE):
    """
    Filtra propiedades:
    - Excluye las que tienen title o price en N/A
    - Excluye las que están fuera del rango de precio
    """
    filtered = []
    excluded = 0

    for p in properties:
        # Excluir si title o price son N/A
        if p['title'] == "N/A" or p['price'] == "N/A":
            excluded += 1
            continue

        # Parsear precio
        price_value = parse_price(p['price'])

        # Excluir si no se puede parsear el precio
        if price_value is None:
            excluded += 1
            continue

        # Excluir si está fuera del rango
        if price_value < min_price or price_value > max_price:
            excluded += 1
            continue

        # Guardar el precio como número también
        p['price_value'] = price_value
        filtered.append(p)

    print(f"  → Propiedades válidas: {len(filtered)} | Excluidas: {excluded}")
    return filtered


def main():
    driver = get_driver()
    all_properties = []

    try:
        print(f"Navegando a {BASE_URL}...")
        driver.get(BASE_URL)

        # Espera inicial para que cargue Cloudflare/captcha
        print("\n⚠️  Si ves un captcha o verificación en el navegador, resuélvelo.")
        print("Cuando veas el listado de viviendas, vuelve aquí.")
        input("Pulsa ENTER cuando veas el listado de viviendas... ")

        # Esperar a que carguen los artículos
        wait_for_properties(driver)

        # Detectar total de páginas
        total_pages = get_total_pages(driver)
        print(f"\nTotal de páginas detectadas: {total_pages}\n")

        # Scrapear página 1 (ya cargada)
        print("Scrapeando página 1...")
        props = extract_properties(driver)
        all_properties.extend(props)
        print(f"  → {len(props)} propiedades encontradas")

        # Scrapear páginas 2 en adelante
        for page_num in range(2, total_pages + 1):
            # Pausa aleatoria entre páginas
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"\nEsperando {delay:.1f} seg antes de página {page_num}...")
            time.sleep(delay)

            url = f"{BASE_URL}pagina-{page_num}.htm"
            print(f"Scrapeando página {page_num}: {url}")
            driver.get(url)

            try:
                wait_for_properties(driver)
                props = extract_properties(driver)
                all_properties.extend(props)
                print(f"  → {len(props)} propiedades encontradas")
            except Exception as e:
                print(f"  ⚠️  Error en página {page_num}: {e}")
                continue

        # Filtrar propiedades
        print("\nAplicando filtros...")
        all_properties = filter_properties(all_properties, min_price=50000, max_price=700000)

        # Mostrar resultados en terminal
        print("\n" + "="*60)
        print("VIVIENDAS EN VENTA - MAJADAHONDA, MADRID")
        print(f"(Precio entre 50.000€ y 700.000€)")
        print("="*60 + "\n")

        for i, p in enumerate(all_properties, 1):
            print(f"[{i}] ID: {p['id']} | {p['title']}")
            print(f"    Precio      : {p['price']}")
            print(f"    Habitaciones: {p['rooms']}")
            print(f"    Tamaño      : {p['size']}")
            if p['parking']:
                print(f"    Garaje      : {p['parking']}")
            if p['tags']:
                print(f"    Tags        : {', '.join(p['tags'])}")
            if p['agency']:
                print(f"    Agencia     : {p['agency']}")
            print(f"    Fotos       : {p['photos']}")
            print(f"    URL         : {p['url']}")
            print(f"    Descripción : {p['description'][:120]}...")
            print()

        print("="*60)
        print(f"Total propiedades tras filtro: {len(all_properties)}")

        # Guardar en CSV
        with open("idealista_majadahonda.csv", "w", newline="", encoding="utf-8") as f:
            fieldnames = ["id", "title", "price", "price_value", "rooms", "size",
                          "parking", "tags", "agency", "photos", "url", "description"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for p in all_properties:
                writer.writerow({
                    "id":          p["id"],
                    "title":       p["title"],
                    "price":       p["price"],
                    "price_value": p["price_value"],
                    "rooms":       p["rooms"],
                    "size":        p["size"],
                    "parking":     p["parking"] or "",
                    "tags":        ", ".join(p["tags"]),
                    "agency":      p["agency"] or "",
                    "photos":      p["photos"],
                    "url":         p["url"],
                    "description": p["description"],
                })

        print("\n✅ Datos guardados en idealista_majadahonda.csv")
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
