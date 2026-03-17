content = '''# Scrapers de viviendas en Majadahonda

Repositorio con varios scripts de web scraping para obtener viviendas en venta en Majadahonda desde distintos portales inmobiliarios: **Fotocasa**, **Idealista**, **Pisos.com** y **Habitaclia**.

Todos los scrapers:

- Usan **Selenium** con **undetected-chromedriver** para simular un navegador real.
- Extraen datos de cada vivienda: id, título, zona, precio, m², habitaciones, baños, extras, nº de fotos, url y descripción.
- Aplican un filtro por rango de precio configurable.
- Guardan los resultados en un CSV específico por portal.

---

## Requisitos

- Python 3.10+.
- Google Chrome instalado.
- Paquetes Python:
  - `undetected-chromedriver`
  - `selenium`

Instalación:

```bash
pip install undetected-chromedriver selenium
```

---

## Scraper de Fotocasa

**Objetivo**: viviendas en venta en Majadahonda (Fotocasa).
**Salida**: `fotocasa_majadahonda.csv` (estructura similar al resto).
**Datos**: id, título, zona, precio, tamaño, habitaciones, baños, planta, extras, nº fotos, url, descripción.

### Ejecución

```bash
python fotocasa-scrapper.py
```

### Flujo

- Se abre Chrome con la búsqueda de Majadahonda en Fotocasa.
- Si aparece captcha/verificación, resuélvelo manualmente.
- Cuando veas el listado de viviendas, pulsa ENTER en la consola.
- El script recorre todas las páginas, aplica filtros de precio y guarda el CSV.

### Parámetros editables

En el propio script:

- `MIN_PRICE`, `MAX_PRICE`: rango de precios.
- `DELAY_MIN`, `DELAY_MAX`: espera aleatoria entre páginas.

---

## Scraper de Idealista

**Objetivo**: viviendas en venta en Majadahonda (Idealista).
**Salida**: `idealista_majadahonda.csv`.
**Datos**: id, título, zona, precio, m², habitaciones, baños, extras, url, descripción.

### Ejecución

```bash
python idealista-scrapper.py
```

### Flujo

- Se abre Chrome con la búsqueda de Majadahonda en Idealista.
- Resuelve captchas si los hay.
- Pulsa ENTER cuando el listado esté visible.
- Se recorren las páginas, se filtra por precio y se genera el CSV.

### Parámetros editables

- `MIN_PRICE`, `MAX_PRICE`.
- Delays entre páginas (`DELAY_MIN`, `DELAY_MAX` o equivalentes).

---

## Scraper de Pisos.com

**Script**: `pisos-scrapper.py`.
**URL base**: `https://www.pisos.com/venta/pisos-majadahonda/`.
**Resultados por página**: 30.
**Salida**: `pisos_majadahonda.csv`.

### Datos extraídos

De cada anuncio (`div` de tipo `ad-preview`):

- `id`: atributo `id` del contenedor.
- `title`: título (`a.ad-preview__title`).
- `zone`: subtítulo / zona.
- `price`: texto de precio.
- `rooms`, `bathrooms`, `size`, `floor`: desde `p.ad-preview__char`.
- `description`: `p.ad-preview__description`.
- `photos`: contador del carrusel (`data-counter`).
- `url`: `data-lnk-href` completado a URL absoluta.

### Ejecución

```bash
python pisos-scrapper.py
```

### Flujo

- Abre Chrome en Pisos.com (búsqueda Majadahonda).
- En consola verás: `Pulsa ENTER cuando veas el listado de viviendas...`.
- Pulsa ENTER cuando el listado esté cargado.

El script entonces:

- Detecta el total de inmuebles y calcula cuántas páginas hay.
- Recorre la paginación de Pisos.com.
- Aplica el filtro de precio (`MIN_PRICE`, `MAX_PRICE`).
- Muestra un resumen en consola y genera `pisos_majadahonda.csv`.

---

## Scraper de Habitaclia

**Script**: `habitaclia-scrapper.py`.
**URL base**:

- Página 1: `https://www.habitaclia.com/viviendas-majadahonda.htm`
- Página N: `https://www.habitaclia.com/viviendas-majadahonda-{N-1}.htm`.

**Resultados por página**: 15.
**Salida**: `habitaclia_majadahonda.csv`.

### Datos extraídos

De cada `article.js-list-item`:

- `id`: `data-id`.
- `url`: `data-href` + dominio.
- `title`: `h3.list-item-title a`.
- `zone`: `p.list-item-location span`.
- `price`: `span[itemprop='price']`.
- `size`, `rooms`, `bathrooms`, `features`: parseados desde `p.list-item-feature` (ej. `177m² - 4 habitaciones - 3 baños`).
- `description`: `p.list-item-description`.
- `photos`: número antes de `fotos` en `span.list-item-multimedia-imgvideo`.
- `type`: `data-propertysubtype`.

### Ejecución

```bash
python habitaclia-scrapper.py
```

### Flujo

- Se abre Chrome con la búsqueda en Habitaclia.
- Si hay captcha, resuélvelo manualmente.
- Pulsa ENTER cuando veas el listado.

El script:

- Espera a que aparezcan los `article.js-list-item`.
- Lee el total de anuncios del subtítulo (por ejemplo `104 anuncios de viviendas en venta en Majadahonda`) y calcula páginas.
- Recorre la paginación (`-1.htm`, `-2.htm`, ...).
- Aplica filtro de precio y guarda `habitaclia_majadahonda.csv`.

---

## Notas comunes

- Todos los scripts usan el patrón:

  ```python
  if __name__ == "__main__":
      main()
  ```

  Por lo que se ejecutan con:

  ```bash
  python <script>.py
  ```

- Si cambias de zona o tipo de inmueble:
  - Actualiza la URL base correspondiente.
  - Revisa que los selectores CSS/XPath sigan siendo válidos.

- Los scrapers son **semi-asistidos**:
  - Tú resuelves los captchas si aparecen.
  - Pulsas ENTER cuando el listado de viviendas está visible en el navegador.
  - A partir de ahí, el scraping y el guardado del CSV son automáticos.
    '''

with open('README_scrapers.md', 'w', encoding='utf-8') as f:
f.write(content)

'README_scrapers.md written'
