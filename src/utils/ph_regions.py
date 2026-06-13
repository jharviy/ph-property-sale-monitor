"""
Philippines province → region lookup.
Used to enrich addresses with the correct administrative region.
"""

PROVINCE_TO_REGION: dict[str, str] = {
    # ── NCR ──────────────────────────────────────────────────────────────────
    "Metro Manila": "NCR",
    "Manila": "NCR",
    "Quezon City": "NCR",
    "Makati": "NCR",
    "Pasig": "NCR",
    "Taguig": "NCR",
    "Paranaque": "NCR",
    "Caloocan": "NCR",
    "Malabon": "NCR",
    "Navotas": "NCR",
    "Valenzuela": "NCR",
    "Marikina": "NCR",
    "Muntinlupa": "NCR",
    "Las Pinas": "NCR",
    "Mandaluyong": "NCR",
    "San Juan": "NCR",
    "Pasay": "NCR",
    "Pateros": "NCR",
    "NCR 1st District": "NCR",
    "NCR 2nd District": "NCR",
    "NCR 3rd District": "NCR",
    "NCR 4th District": "NCR",

    # ── Region I – Ilocos ─────────────────────────────────────────────────────
    "Ilocos Norte": "Region I",
    "Ilocos Sur": "Region I",
    "La Union": "Region I",
    "Pangasinan": "Region I",

    # ── Region II – Cagayan Valley ────────────────────────────────────────────
    "Batanes": "Region II",
    "Cagayan": "Region II",
    "Isabela": "Region II",
    "Nueva Vizcaya": "Region II",
    "Quirino": "Region II",

    # ── Region III – Central Luzon ────────────────────────────────────────────
    "Aurora": "Region III",
    "Bataan": "Region III",
    "Bulacan": "Region III",
    "Nueva Ecija": "Region III",
    "Pampanga": "Region III",
    "Tarlac": "Region III",
    "Zambales": "Region III",

    # ── Region IV-A – CALABARZON ─────────────────────────────────────────────
    "Batangas": "Region IV-A",
    "Cavite": "Region IV-A",
    "Laguna": "Region IV-A",
    "Quezon": "Region IV-A",
    "Rizal": "Region IV-A",

    # ── Region IV-B – MIMAROPA ────────────────────────────────────────────────
    "Marinduque": "Region IV-B",
    "Occidental Mindoro": "Region IV-B",
    "Oriental Mindoro": "Region IV-B",
    "Palawan": "Region IV-B",
    "Romblon": "Region IV-B",

    # ── Region V – Bicol ─────────────────────────────────────────────────────
    "Albay": "Region V",
    "Camarines Norte": "Region V",
    "Camarines Sur": "Region V",
    "Catanduanes": "Region V",
    "Masbate": "Region V",
    "Sorsogon": "Region V",

    # ── Region VI – Western Visayas ───────────────────────────────────────────
    "Aklan": "Region VI",
    "Antique": "Region VI",
    "Capiz": "Region VI",
    "Guimaras": "Region VI",
    "Iloilo": "Region VI",
    "Negros Occidental": "Region VI",

    # ── Region VII – Central Visayas ──────────────────────────────────────────
    "Bohol": "Region VII",
    "Cebu": "Region VII",
    "Negros Oriental": "Region VII",
    "Siquijor": "Region VII",

    # ── Region VIII – Eastern Visayas ─────────────────────────────────────────
    "Biliran": "Region VIII",
    "Eastern Samar": "Region VIII",
    "Leyte": "Region VIII",
    "Northern Samar": "Region VIII",
    "Samar": "Region VIII",
    "Southern Leyte": "Region VIII",

    # ── Region IX – Zamboanga Peninsula ──────────────────────────────────────
    "Zamboanga del Norte": "Region IX",
    "Zamboanga del Sur": "Region IX",
    "Zamboanga Sibugay": "Region IX",

    # ── Region X – Northern Mindanao ─────────────────────────────────────────
    "Bukidnon": "Region X",
    "Camiguin": "Region X",
    "Lanao del Norte": "Region X",
    "Misamis Occidental": "Region X",
    "Misamis Oriental": "Region X",

    # ── Region XI – Davao ────────────────────────────────────────────────────
    "Davao de Oro": "Region XI",
    "Compostela Valley": "Region XI",
    "Davao del Norte": "Region XI",
    "Davao del Sur": "Region XI",
    "Davao Occidental": "Region XI",
    "Davao Oriental": "Region XI",
    "Davao City": "Region XI",

    # ── Region XII – SOCCSKSARGEN ─────────────────────────────────────────────
    "Cotabato": "Region XII",
    "North Cotabato": "Region XII",
    "Sarangani": "Region XII",
    "South Cotabato": "Region XII",
    "Sultan Kudarat": "Region XII",

    # ── Region XIII – CARAGA ─────────────────────────────────────────────────
    "Agusan del Norte": "Region XIII",
    "Agusan del Sur": "Region XIII",
    "Dinagat Islands": "Region XIII",
    "Surigao del Norte": "Region XIII",
    "Surigao del Sur": "Region XIII",

    # ── CAR – Cordillera ─────────────────────────────────────────────────────
    "Abra": "CAR",
    "Apayao": "CAR",
    "Benguet": "CAR",
    "Ifugao": "CAR",
    "Kalinga": "CAR",
    "Mountain Province": "CAR",

    # ── BARMM ────────────────────────────────────────────────────────────────
    "Basilan": "BARMM",
    "Lanao del Sur": "BARMM",
    "Maguindanao": "BARMM",
    "Maguindanao del Norte": "BARMM",
    "Maguindanao del Sur": "BARMM",
    "Sulu": "BARMM",
    "Tawi-Tawi": "BARMM",
}

# Case-insensitive lookup helper
_LOWER_MAP: dict[str, str] = {k.lower(): v for k, v in PROVINCE_TO_REGION.items()}


def get_region(province: str | None) -> str | None:
    """Return the region name for a given province string, or None if unknown."""
    if not province:
        # return "NCR"
        return None
    return _LOWER_MAP.get(province.strip().lower())
