import re
import requests
from bs4 import BeautifulSoup


DOCENTI_URL_DEFAULT = (
    "https://cercauniversita.mur.gov.it/php5/docenti/vis_docenti.php?docinput={}&docsubmit=cerca"
)
ASSEGNASTI_URL_DEFAULT = (
    "https://cercauniversita.mur.gov.it/php5/assegnisti/vis_assegnisti.php?"
    "qualifica=**&argomento=&title_radiogroup=P&cognome={}&nome={}&radiogroup=E&universita=00&facolta=00&"
    "settore=0000&area=0000&situazione_al=0&vai=Invio"
)


def fetch_ssd(
    first_name: str,
    last_name: str,
    *,
    timeout: int = 10,
    session: requests.Session | None = None,
    docenti_url_template: str = DOCENTI_URL_DEFAULT,
    assegnisti_url_template: str = ASSEGNASTI_URL_DEFAULT,
) -> str:
    """
    Fetch SSD by querying first DOCENTI (by last_name), then ASSEGNASTI (by last_name + first_name).

    Returns:
        - SSD string if found
        - "NULL" otherwise
    """

    def _extract_ssd_from_url(url: str) -> str:
        try:
            s = session or requests
            resp = s.get(url, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException:
            return "NULL"

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"class": "risultati"})
        if not table:
            return "NULL"

        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                ssd_2024 = cols[5].get_text(strip=True)
                department = cols[6].get_text(strip=True)

                # Your original logic: if SSD looks like a department name (some assegnisti), return department
                if re.search(r"\(\w+\)", ssd_2024):
                    return department

                return ssd_2024

        return "NULL"

    # Normalise inputs a bit
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not last_name:
        return "NULL"

    # 1) DOCENTI lookup (only last name in your current URL design)
    ssd_value = _extract_ssd_from_url(docenti_url_template.format(last_name))

    # 2) ASSEGNASTI fallback (requires both last + first name)
    if ssd_value == "NULL" and first_name:
        ssd_value = _extract_ssd_from_url(assegnisti_url_template.format(last_name, first_name))

    return ssd_value