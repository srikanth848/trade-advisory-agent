import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List


class ScreenerClient:
    """
    Production-Grade, Sector-Agnostic Screener.in client for Banking, NBFCs, 
    IT, Pharma, Capital Markets, Infra, FMCG, Chemicals, and Hospitals.
    """

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _clean_text(self, text: str) -> str:
        if not text:
            return "N/A"
        return re.sub(r'\s+', ' ', text).strip()

    def _clean_value(self, val: str) -> str:
        """Strips out currency, percent, and Cr tags to prevent duplication."""
        if not val or val == "N/A":
            return "N/A"
        cleaned = re.sub(r'[₹%]', '', val).strip()
        cleaned = re.sub(r'\bCr\.?\b', '', cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    def _resolve_slug(self, query: str) -> str:
        query = query.strip()
        search_url = f"https://www.screener.in/api/company/search/?q={query}"
        
        try:
            res = requests.get(search_url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and isinstance(data, list):
                    company_url = data[0].get("url", "")
                    parts = [p for p in company_url.split("/") if p]
                    if len(parts) >= 2:
                        return parts[1]
        except Exception as e:
            print(f"[Debug] Screener search exception for '{query}': {e}")
            
        return query.upper()

    def _parse_company_page(self, slug: str, soup: BeautifulSoup, consolidated: bool) -> Dict[str, Any]:
        ratios = {}
        ratios_section = soup.find(id='top-ratios')
        if ratios_section:
            for item in ratios_section.find_all('li'):
                name_el = item.find('span', {'class': 'name'})
                val_el = item.find('span', {'class': 'value'})
                if name_el and val_el:
                    key = self._clean_text(name_el.text).lower().replace(' ', '_').replace('.', '').replace('/', '_')
                    val = self._clean_value(self._clean_text(val_el.text))
                    ratios[key] = val

        pe_val = ratios.get('stock_p_e', ratios.get('stock_pe', ratios.get('pe', 'N/A')))
        ratios['pe'] = pe_val

        page_text = soup.get_text()
        is_bank = "Gross NPA" in page_text or "Net NPA" in page_text or "Financing Profit" in page_text

        financial_history = []
        quarters_section = soup.find('section', {'id': 'quarters'})
        if quarters_section:
            table = quarters_section.find('table')
            if table and table.find('tbody'):
                rows = table.find('tbody').find_all('tr')

                row_data = {}
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) > 0:
                        row_name = self._clean_text(cols[0].text)
                        row_vals = [self._clean_value(self._clean_text(c.text)).replace(',', '') for c in cols[1:]]
                        row_data[row_name] = row_vals

                def get_row_value(keys: List[str]) -> str:
                    for key_name in keys:
                        for row_name, vals in row_data.items():
                            if key_name.lower() in row_name.lower() and vals:
                                return vals[-1]
                    return "N/A"

                quarter_headers = []
                thead = table.find('thead')
                if thead:
                    th_cols = thead.find_all('th')
                    quarter_headers = [self._clean_text(th.text) for th in th_cols[1:]]

                latest_q = quarter_headers[-1] if quarter_headers else "Latest"

                if is_bank:
                    financial_history.append({
                        "quarter": latest_q,
                        "sales": get_row_value(["Interest", "Revenue", "Financing Revenue"]),
                        "net_profit": get_row_value(["Net Profit"]),
                        "eps_rs": get_row_value(["EPS in Rs", "EPS"]),
                        "gross_npa": get_row_value(["Gross NPA %", "Gross NPA"]),
                        "net_npa": get_row_value(["Net NPA %", "Net NPA"])
                    })
                else:
                    financial_history.append({
                        "quarter": latest_q,
                        "sales": get_row_value(["Sales", "Revenue"]),
                        "operating_profit": get_row_value(["Operating Profit"]),
                        "opm_pct": get_row_value(["OPM %"]),
                        "net_profit": get_row_value(["Net Profit"]),
                        "eps_rs": get_row_value(["EPS in Rs", "EPS"])
                    })

        return {
            "status": "success",
            "symbol": slug,
            "view": "consolidated" if consolidated else "standalone",
            "is_bank": is_bank,
            "ratios": ratios,
            "financial_history": financial_history
        }

    def get_company_financials(self, symbol: str, consolidated: bool = False) -> Dict[str, Any]:
        slug = self._resolve_slug(symbol)
        path = f"{slug}/consolidated/" if consolidated else f"{slug}/"
        url = f"https://www.screener.in/company/{path}"

        try:
            res = requests.get(url, headers=self.headers, timeout=8)
            if res.status_code != 200:
                fallback_path = f"{symbol.upper()}/consolidated/" if consolidated else f"{symbol.upper()}/"
                url = f"https://www.screener.in/company/{fallback_path}"
                res = requests.get(url, headers=self.headers, timeout=8)
                
            if res.status_code != 200:
                view = "consolidated" if consolidated else "standalone"
                return {"status": "error", "message": f"Failed to fetch {view} Screener data for {symbol}"}

            soup = BeautifulSoup(res.text, 'html.parser')
            return self._parse_company_page(slug, soup, consolidated)
        except Exception as e:
            return {"status": "error", "message": str(e)}