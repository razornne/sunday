import re
from bs4 import BeautifulSoup


def aggressive_clean_html(html_content):
    """Жесткая очистка HTML для экономии токенов"""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    for element in soup(["script", "style", "head", "title", "meta", "noscript", "iframe", "svg"]):
        element.extract()

    for element in soup.find_all(attrs={"class": re.compile(r"footer|header|nav|menu|copyright|social", re.I)}):
        element.extract()
    for element in soup(["footer", "header", "nav", "aside"]):
        element.extract()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()

    return text
