import time
import random
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.idealista.com/venta-viviendas/majadahonda-madrid/"

# Pausa mínima y máxima en segundos entre páginas (aleatorio para evitar bloqueos)
DELAY_MIN = 4
DELAY_MAX = 8


def get_driver():
    options = uc.ChromeOptions()
    # Ejecutar en segundo plano (headless)
    options.add_argument("--headless=new")
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
    Detecta el número total de páginas desde la paginación.
    El botón 'next' está en un <li class='next'> y los números de página en <li class='...'>
    """
    try:
        pagination = driver.find_elements(By.XPATH, "//ul[contains(@class,'pagination')]//li/a")
        max_page = 1
        for a in pagination:
            text = a.text.strip()
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page
    except:
        return 1


def extract_properties(driver):
    """
    Extrae todas las propiedades de la página actual.
    Cada listing está en <article class="item ...">
    """
    properties = []

    property_divs = driver.find_elements(By.XPATH, "//article[contains(@class, 'item')]")

    for div in property_divs:
        prop = {}

        # Título y URL
        try:
            link = div.find_element(By.XPATH, './/a[@class="item-link"]')
            prop['title'] = link.text.strip()
            prop['url'] = link.get_attribute('href')
        except:
            prop['title'] = "N/A"
            prop['url'] = "N/A"

        # Precio
        try:
            prop['price'] = div.find_element(
                By.XPATH, './/div[contains(@class,"price-row")]'
            ).text.strip()
        except:
            prop['price'] = "N/A"

        # Detalles (m², habitaciones, baños)
        try:
            prop['detail'] = div.find_element(
                By.XPATH, './/div[@class="item-detail-char"]'
            ).text.strip()
        except:
            prop['detail'] = "N/A"

        # Descripción corta
        try:
            prop['description'] = div.find_element(
                By.XPATH, './/div[contains(@class,"item-description")]'
            ).text.strip()
        except:
            prop['description'] = "N/A"

        properties.append(prop)

    return properties


def main():
    driver = get_driver()
    all_properties = []

    try:
        print(f"Navegando a {BASE_URL}...")
        driver.get(BASE_URL)

        # Esperar a que cargue la página
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'item')]"))
        )

        # Detectar total de páginas
        total_pages = get_total_pages(driver)
        print(f"Total de páginas detectadas: {total_pages}\n")

        # Scrapear página 1 (ya cargada)
        print("Scrapeando página 1...")
        props = extract_properties(driver)
        all_properties.extend(props)
        print(f"  → {len(props)} propiedades encontradas")

        # Scrapear páginas 2 en adelante
        for page_num in range(2, total_pages + 1):
            # Pausa aleatoria entre páginas para evitar bloqueos
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"Esperando {delay:.1f} segundos antes de la página {page_num}...")
            time.sleep(delay)

            # Construir URL de la siguiente página
            url = f"{BASE_URL}pagina-{page_num}.htm"
            print(f"Scrapeando página {page_num}: {url}")
            driver.get(url)

            # Esperar a que carguen los artículos
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'item')]"))
                )
                props = extract_properties(driver)
                all_properties.extend(props)
                print(f"  → {len(props)} propiedades encontradas")
            except Exception as e:
                print(f"  ⚠️ Error en página {page_num}: {e}")
                continue

        # Mostrar resultados en terminal
        print("\n" + "="*60)
        print(f"VIVIENDAS EN VENTA - MAJADAHONDA, MADRID")
        print("="*60 + "\n")

        for i, p in enumerate(all_properties, 1):
            print(f"[{i}] {p['title']}")
            print(f"    Precio : {p['price']}")
            print(f"    Detalle: {p['detail']}")
            print(f"    URL    : {p['url']}")
            print()

        print("="*60)
        print(f"Total propiedades extraídas: {len(all_properties)}")
        print(f"De {total_pages} páginas")

        # Guardar en JSON
        with open("idealista_majadahonda.json", "w", encoding="utf-8") as f:
            json.dump(all_properties, f, ensure_ascii=False, indent=2)
        print("\n✅ Datos guardados en idealista_majadahonda.json")

    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    main()
