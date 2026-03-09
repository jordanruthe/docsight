"""Tests for glossary i18n key completeness."""

import json
import os

import pytest

I18N_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "i18n")
MOD_I18N_DIR = os.path.join(
    os.path.dirname(__file__), "..", "app", "modules", "modulation", "i18n"
)

CORE_GLOSSARY_KEYS = [
    "glossary_snr",
    "glossary_ds_power",
    "glossary_us_power",
    "glossary_errors",
    "glossary_scqam",
    "glossary_ofdm",
    "glossary_modulation",
    "glossary_docsis",
    "glossary_gaming_index",
]

MOD_GLOSSARY_KEYS = [
    "glossary_health_index",
    "glossary_low_qam",
    "glossary_sample_density",
]

LANGUAGES = ["en", "de", "fr", "es"]


@pytest.mark.parametrize("lang", LANGUAGES)
def test_core_glossary_keys_present(lang):
    path = os.path.join(I18N_DIR, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for key in CORE_GLOSSARY_KEYS:
        assert key in data, f"Missing {key} in {lang}.json"
        assert len(data[key]) > 10, f"Empty/too-short value for {key} in {lang}.json"


@pytest.mark.parametrize("lang", LANGUAGES)
def test_modulation_glossary_keys_present(lang):
    path = os.path.join(MOD_I18N_DIR, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for key in MOD_GLOSSARY_KEYS:
        assert key in data, f"Missing {key} in modulation/{lang}.json"
        assert len(data[key]) > 10, f"Empty/too-short value for {key} in modulation/{lang}.json"
