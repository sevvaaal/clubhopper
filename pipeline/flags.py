"""Flags for player nationalities.

Reads the nationalities in site/data/game.json, matches each to a flag in
Kenney's Flag Pack (CC0, https://kenney.nl/assets/flag-pack), copies only the
flags we use to site/img/flags/{code}.svg and writes site/data/flags.json
({nationality: code}). Nationalities without a flag in the pack are left out;
the site shows their name instead.

    python flags.py ~/Downloads/kenney_flag-pack.zip
"""

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "site" / "data" / "game.json"
OUT_DIR = ROOT / "site" / "img" / "flags"
OUT_MAP = ROOT / "site" / "data" / "flags.json"

# API-Football nationality -> Kenney flag code (ISO 3166 alpha-2, plus GB_ENG etc.).
# French overseas regions have no flag in the pack and get the French one.
CODES = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ", "Andorra": "AD", "Angola": "AO",
    "Antigua and Barbuda": "AG", "Argentina": "AR", "Armenia": "AM", "Aruba": "AW", "Australia": "AU",
    "Austria": "AT", "Azerbaijan": "AZ", "Bahrain": "BH", "Bangladesh": "BD", "Barbados": "BB",
    "Belarus": "BY", "Belgium": "BE", "Benin": "BJ", "Bermuda": "BM", "Bolivia": "BO",
    "Bosnia and Herzegovina": "BA", "Bosnia-Herzegovina": "BA", "Brazil": "BR",
    "British Virgin Islands": "VG", "Bulgaria": "BG", "Burkina Faso": "BF", "Burundi": "BI",
    "Cameroon": "CM", "Canada": "CA", "Cape Verde": "CV", "Cape Verde Islands": "CV",
    "Central African Republic": "CF", "Chad": "TD", "Chile": "CL", "China PR": "CN",
    "Chinese Taipei": "TW", "Colombia": "CO", "Comoros": "KM", "Congo": "CG", "Congo DR": "CD",
    "Costa Rica": "CR", "Croatia": "HR", "Cuba": "CU", "Curaçao": "CW", "Cyprus": "CY",
    "Czech Republic": "CZ", "Czechia": "CZ", "Côte d'Ivoire": "CI", "CÃ´te d'Ivoire": "CI",
    "Ivory Coast": "CI", "Denmark": "DK", "Dominican Republic": "DO", "Ecuador": "EC", "Egypt": "EG",
    "El Salvador": "SV", "England": "GB_ENG", "Equatorial Guinea": "GQ", "Eritrea": "ER",
    "Estonia": "EE", "Ethiopia": "ET", "FYR Macedonia": "MK", "Macedonia FYR": "MK",
    "North Macedonia": "MK", "Faroe Islands": "FO", "Finland": "FI", "France": "FR",
    "French Guiana": "FR", "Guadeloupe": "FR", "Martinique": "FR", "Réunion": "FR",
    "Saint Martin": "FR", "New Caledonia": "FR", "Gabon": "GA", "Gambia": "GM", "Georgia": "GE",
    "Germany": "DE", "Ghana": "GH", "Gibraltar": "GI", "Greece": "GR", "Grenada": "GD",
    "Guatemala": "GT", "Guinea": "GN", "Guinea-Bissau": "GW", "Guyana": "GY", "Haiti": "HT",
    "Honduras": "HN", "Hungary": "HU", "Iceland": "IS", "India": "IN", "Indonesia": "ID",
    "Iran": "IR", "Iraq": "IQ", "Ireland Republic": "IE", "Republic of Ireland": "IE",
    "Israel": "IL", "Italy": "IT", "Jamaica": "JM", "Japan": "JP", "Jordan": "JO",
    "Kazakhstan": "KZ", "Kenya": "KE", "Korea DPR": "KP", "Korea Republic": "KR",
    "Kyrgyz Republic": "KG", "Laos": "LA", "Latvia": "LV", "Lebanon": "LB", "Liberia": "LR",
    "Libya": "LY", "Liechtenstein": "LI", "Lithuania": "LT", "Luxembourg": "LU", "Madagascar": "MG",
    "Malawi": "MW", "Malaysia": "MY", "Mali": "ML", "Malta": "MT", "Mauritania": "MR",
    "Mauritius": "MU", "Mexico": "MX", "Moldova": "MD", "Montenegro": "ME", "Montserrat": "MS",
    "Morocco": "MA", "Mozambique": "MZ", "Namibia": "NA", "Netherlands": "NL", "New Zealand": "NZ",
    "Nicaragua": "NI", "Niger": "NE", "Nigeria": "NG", "Norway": "NO", "Oman": "OM",
    "Palestine": "PS", "Panama": "PA", "Papua New Guinea": "PG", "Paraguay": "PY", "Peru": "PE",
    "Philippines": "PH", "Poland": "PL", "Portugal": "PT", "Puerto Rico": "PR", "Qatar": "QA",
    "Romania": "RO", "Russia": "RU", "Rwanda": "RW", "San Marino": "SM", "Saudi Arabia": "SA",
    "Scotland": "GB_SCT", "Senegal": "SN", "Serbia": "RS", "Seychelles": "SC", "Sierra Leone": "SL",
    "Sint Maarten": "SX", "Slovakia": "SK", "Slovenia": "SI", "South Africa": "ZA", "Spain": "ES",
    "St. Kitts and Nevis": "KN", "St. Vincent and the Grenadines": "VC", "Suriname": "SR",
    "Sweden": "SE", "Switzerland": "CH", "Syria": "SY", "São Tomé e Príncipe": "ST", "Tahiti": "PF",
    "Tajikistan": "TJ", "Tanzania": "TZ", "Thailand": "TH", "Togo": "TG",
    "Trinidad and Tobago": "TT", "Tunisia": "TN", "Turkey": "TR", "Türkiye": "TR",
    "Turkmenistan": "TM", "USA": "US", "Uganda": "UG", "Ukraine": "UA",
    "United Arab Emirates": "AE", "Uruguay": "UY", "Uzbekistan": "UZ", "Venezuela": "VE",
    "Wales": "GB_WLS", "Zambia": "ZM", "Zimbabwe": "ZW",
}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pack = zipfile.ZipFile(Path(sys.argv[1]).expanduser())
    available = {Path(n).stem for n in pack.namelist() if n.startswith("Vector/") and n.endswith(".svg")}

    players = json.loads(GAME.read_text(encoding="utf-8"))["players"]
    nats = {p["nat"].strip() for p in players.values() if (p.get("nat") or "").strip()}
    mapping = {n: CODES[n] for n in sorted(nats) if CODES.get(n) in available}
    missing = sorted(n for n in nats if n not in mapping)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for code in sorted(set(mapping.values())):
        (OUT_DIR / f"{code}.svg").write_bytes(pack.read(f"Vector/{code}.svg"))
    OUT_MAP.write_text(json.dumps(mapping, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT_DIR.glob("*.svg"))
    print(f"{len(mapping)} nationalities -> {len(set(mapping.values()))} flags ({size // 1024} KB) in {OUT_DIR.relative_to(ROOT)}")
    print(f"no flag: {', '.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
