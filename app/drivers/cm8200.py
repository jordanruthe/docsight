"""Arris Touchstone CM8200A driver for DOCSight.

The CM8200A is an ISP-branded Arris DOCSIS 3.1 cable modem (Comcast
reference design) with a traditional HTML web UI served by micro_httpd.
Authentication uses base64-encoded credentials in the query string,
with IP-based session persistence.

Channel data is on /cmconnectionstatus.html in two HTML tables:
- "Downstream Bonded Channels" (8 columns)
- "Upstream Bonded Channels" (7 columns)

DOCSIS version is inferred from modulation/channel type:
- DS: "Other" modulation = OFDM (3.1), anything else = SC-QAM (3.0)
- US: "OFDM Upstream" type = OFDMA (3.1), "SC-QAM Upstream" = 3.0
"""

import base64
import logging

import requests
from bs4 import BeautifulSoup

from .base import ModemDriver

log = logging.getLogger("docsis.driver.cm8200")


class CM8200Driver(ModemDriver):
    """Driver for Arris Touchstone CM8200A DOCSIS 3.1 cable modem.

    Authentication uses base64(user:pass) in the query string.
    DOCSIS data is scraped from HTML tables on the status page.
    """

    def __init__(self, url: str, user: str, password: str):
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
            log.info("CM8200 requires HTTPS, upgraded URL to %s", url)
        super().__init__(url, user, password)
        self._session = requests.Session()
        self._session.verify = False
        self._status_html = None

    def login(self) -> None:
        """Authenticate via base64 credentials in query string.

        Retries once with a fresh connection if the modem drops a stale
        TCP connection (common after container restarts).
        """
        creds = base64.b64encode(f"{self._user}:{self._password}".encode()).decode()
        for attempt in range(2):
            try:
                r = self._session.get(
                    f"{self._url}/cmconnectionstatus.html?{creds}",
                    timeout=30,
                )
                r.raise_for_status()
                self._status_html = r.text
                log.info("CM8200 auth OK")
                return
            except requests.ConnectionError:
                if attempt == 0:
                    log.warning("CM8200 connection lost, retrying with fresh session")
                    self._session.close()
                    self._session = requests.Session()
                    self._session.verify = False
                    continue
                raise RuntimeError("CM8200 authentication failed: connection refused after retry")
            except requests.RequestException as e:
                raise RuntimeError(f"CM8200 authentication failed: {e}")

    def get_docsis_data(self) -> dict:
        """Retrieve DOCSIS channel data from HTML tables on status page.

        Returns pre-split format so the analyzer correctly labels
        SC-QAM channels as DOCSIS 3.0 and OFDM/OFDMA channels as 3.1.
        """
        soup = self._fetch_status_page()
        ds_table, us_table = self._find_channel_tables(soup)

        ds30, ds31 = self._parse_downstream(ds_table)
        us30, us31 = self._parse_upstream(us_table)

        return {
            "channelDs": {"docsis30": ds30, "docsis31": ds31},
            "channelUs": {"docsis30": us30, "docsis31": us31},
        }

    def get_device_info(self) -> dict:
        """Retrieve device info from status page."""
        try:
            soup = self._fetch_status_page()
            model_span = soup.find("span", id="thisModelNumberIs")
            model = model_span.get_text(strip=True) if model_span else "CM8200A"
            return {
                "manufacturer": "Arris",
                "model": model,
                "sw_version": "",
            }
        except Exception:
            return {"manufacturer": "Arris", "model": "CM8200A", "sw_version": ""}

    def get_connection_info(self) -> dict:
        """CM8200A is a standalone modem with no connection info."""
        return {}

    # -- Internal helpers --

    def _fetch_status_page(self) -> BeautifulSoup:
        """Fetch and parse the status page HTML.

        Reuses cached HTML from login if available (same page).
        """
        if self._status_html:
            html = self._status_html
            self._status_html = None
            return BeautifulSoup(html, "html.parser")

        try:
            r = self._session.get(
                f"{self._url}/cmconnectionstatus.html",
                timeout=30,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"CM8200 status page retrieval failed: {e}")
        return BeautifulSoup(r.text, "html.parser")

    @staticmethod
    def _find_channel_tables(soup) -> tuple:
        """Find downstream and upstream channel tables.

        Tables are identified by the text in their first header row:
        - "Downstream Bonded Channels" -> downstream
        - "Upstream Bonded Channels" -> upstream
        """
        ds_table = None
        us_table = None

        for table in soup.find_all("table"):
            header = table.find("tr")
            if not header:
                continue
            text = header.get_text(strip=True).lower()
            if "downstream bonded" in text:
                ds_table = table
            elif "upstream bonded" in text:
                us_table = table

        return ds_table, us_table

    def _parse_downstream(self, table) -> tuple:
        """Parse downstream table into (docsis30, docsis31) channel lists.

        8 columns: Channel ID, Lock Status, Modulation, Frequency,
                   Power, SNR/MER, Corrected, Uncorrectables
        """
        ds30 = []
        ds31 = []
        if not table:
            return ds30, ds31

        rows = table.find_all("tr")
        # Skip header rows (first row is title, second is column headers)
        for row in rows[2:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 8:
                continue

            lock_status = cells[1]
            if lock_status != "Locked":
                continue

            try:
                channel_id = int(cells[0])
                modulation = cells[2]
                frequency = self._parse_freq_hz(cells[3])
                power = self._parse_value(cells[4])
                snr = self._parse_value(cells[5])
                corrected = int(cells[6])
                uncorrectables = int(cells[7])

                channel = {
                    "channelID": channel_id,
                    "frequency": frequency,
                    "powerLevel": power,
                    "modulation": modulation,
                    "corrErrors": corrected,
                    "nonCorrErrors": uncorrectables,
                }

                if modulation == "Other":
                    # OFDM channel (DOCSIS 3.1)
                    channel["type"] = "OFDM"
                    channel["mer"] = snr
                    channel["mse"] = None
                    ds31.append(channel)
                else:
                    # SC-QAM channel (DOCSIS 3.0)
                    channel["mer"] = snr
                    channel["mse"] = -snr if snr is not None else None
                    ds30.append(channel)
            except (ValueError, TypeError, IndexError) as e:
                log.warning("Failed to parse CM8200 DS row: %s", e)

        return ds30, ds31

    def _parse_upstream(self, table) -> tuple:
        """Parse upstream table into (docsis30, docsis31) channel lists.

        7 columns: Channel, Channel ID, Lock Status, US Channel Type,
                   Frequency, Width, Power
        """
        us30 = []
        us31 = []
        if not table:
            return us30, us31

        rows = table.find_all("tr")
        for row in rows[2:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 7:
                continue

            lock_status = cells[2]
            if lock_status != "Locked":
                continue

            try:
                channel_id = int(cells[1])
                channel_type = cells[3]
                frequency = self._parse_freq_hz(cells[4])
                power = self._parse_value(cells[6])

                channel = {
                    "channelID": channel_id,
                    "frequency": frequency,
                    "powerLevel": power,
                    "modulation": channel_type,
                }

                if "OFDM" in channel_type and "SC-QAM" not in channel_type:
                    # OFDMA channel (DOCSIS 3.1)
                    channel["type"] = "OFDMA"
                    channel["multiplex"] = ""
                    us31.append(channel)
                else:
                    # SC-QAM channel (DOCSIS 3.0)
                    channel["multiplex"] = "SC-QAM"
                    us30.append(channel)
            except (ValueError, TypeError, IndexError) as e:
                log.warning("Failed to parse CM8200 US row: %s", e)

        return us30, us31

    # -- Value parsers --

    @staticmethod
    def _parse_freq_hz(freq_str: str) -> str:
        """Convert '795000000 Hz' to '795 MHz'."""
        if not freq_str:
            return ""
        parts = freq_str.strip().split()
        try:
            hz = float(parts[0])
            mhz = hz / 1_000_000
            if mhz == int(mhz):
                return f"{int(mhz)} MHz"
            return f"{mhz:.1f} MHz"
        except (ValueError, IndexError):
            return freq_str

    @staticmethod
    def _parse_value(val_str: str) -> float | None:
        """Parse '8.2 dBmV' or '43.0 dB' to float."""
        if not val_str:
            return None
        parts = val_str.strip().split()
        try:
            return float(parts[0])
        except (ValueError, IndexError):
            return None
