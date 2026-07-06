"""FIR registry — all known Flight Information Regions.

This registry maps four-letter ICAO FIR identifiers to Fir objects.
It is used to:
  - display the FIR name in the config flow when suggesting related
    objects after airport selection
  - build the DeviceInfo for FIR devices in Home Assistant
  - validate user-entered FIR codes

Sources: ICAO Doc 7910, Wikipedia List of FIRs (2013/2025),
Eurocontrol FIR/UIR Charts 2024.
"""

from __future__ import annotations

from .models import Fir

# -----------------------------------------------------------------------
# European FIRs
# Source: ICAO list (Wikipedia / Eurocontrol 2024)
# -----------------------------------------------------------------------
_EUROPEAN_FIRS: list[Fir] = [
    # Albania
    Fir(icao="LAAA", name="Tirana FIR", country="AL"),
    # Austria
    Fir(icao="LOVV", name="Wien FIR", country="AT"),
    # Belarus
    Fir(icao="UMMV", name="Minsk FIR", country="BY"),
    # Belgium / Luxembourg
    Fir(icao="EBBU", name="Bruxelles FIR", country="BE"),
    # Bosnia and Herzegovina
    Fir(icao="LQSB", name="Sarajevo FIR", country="BA"),
    # Bulgaria
    Fir(icao="LBSR", name="Sofia FIR", country="BG"),
    # Croatia
    Fir(icao="LDZO", name="Zagreb FIR", country="HR"),
    # Czech Republic
    Fir(icao="LKAA", name="Praha FIR", country="CZ"),
    # Denmark
    Fir(icao="EKDK", name="København FIR", country="DK"),
    # Estonia
    Fir(icao="EETT", name="Tallinn FIR", country="EE"),
    # Finland
    Fir(icao="EFIN", name="Finland FIR", country="FI"),
    # France
    Fir(icao="LFBB", name="Bordeaux FIR", country="FR"),
    Fir(icao="LFEE", name="Reims FIR", country="FR"),
    Fir(icao="LFFF", name="Paris FIR", country="FR"),
    Fir(icao="LFMM", name="Marseille FIR", country="FR"),
    Fir(icao="LFRR", name="Brest FIR", country="FR"),
    # Germany
    Fir(icao="EDGG", name="Langen FIR", country="DE"),
    Fir(icao="EDMM", name="München FIR", country="DE"),
    Fir(icao="EDWW", name="Bremen FIR", country="DE"),
    # Greece
    Fir(icao="LGGG", name="Athens FIR", country="GR"),
    # Hungary
    Fir(icao="LHCC", name="Budapest FIR", country="HU"),
    # Iceland
    Fir(icao="BIRD", name="Reykjavík FIR", country="IS"),
    # Ireland
    Fir(icao="EISN", name="Shannon FIR", country="IE"),
    # Italy
    Fir(icao="LIBB", name="Brindisi FIR", country="IT"),
    Fir(icao="LIMM", name="Milano FIR", country="IT"),
    Fir(icao="LIRR", name="Roma FIR", country="IT"),
    # Latvia
    Fir(icao="EVRR", name="Riga FIR", country="LV"),
    # Lithuania
    Fir(icao="EYVL", name="Vilnius FIR", country="LT"),
    # Malta
    Fir(icao="LMMM", name="Malta FIR", country="MT"),
    # Moldova
    Fir(icao="LUUU", name="Chisinau FIR", country="MD"),
    # Montenegro / Serbia  (shared airspace)
    Fir(icao="LYBA", name="Beograd FIR", country="RS"),
    # Netherlands
    Fir(icao="EHAA", name="Amsterdam FIR", country="NL"),
    # North Macedonia
    Fir(icao="LWSS", name="Skopje FIR", country="MK"),
    # Norway
    Fir(icao="ENOR", name="Norway FIR", country="NO"),
    Fir(icao="ENOB", name="Bodo Oceanic FIR", country="NO"),
    # Poland
    Fir(icao="EPWW", name="Warszawa FIR", country="PL"),
    # Portugal
    Fir(icao="LPPC", name="Lisboa FIR", country="PT"),
    Fir(icao="LPPO", name="Santa Maria Oceanic FIR", country="PT"),
    # Romania
    Fir(icao="LRBB", name="Bucureşti FIR", country="RO"),
    # Russia (European part)
    Fir(icao="ULLL", name="Sankt-Peterburg FIR", country="RU"),
    Fir(icao="UMKK", name="Kaliningrad FIR", country="RU"),
    Fir(icao="URRV", name="Rostov-Na-Donu FIR", country="RU"),
    Fir(icao="UUWV", name="Moscow FIR", country="RU"),
    # Slovakia
    Fir(icao="LZBB", name="Bratislava FIR", country="SK"),
    # Slovenia
    Fir(icao="LJLA", name="Ljubljana FIR", country="SI"),
    # Spain
    Fir(icao="LECB", name="Barcelona FIR", country="ES"),
    Fir(icao="LECM", name="Madrid FIR", country="ES"),
    Fir(icao="LECS", name="Sevilla FIR", country="ES"),
    Fir(icao="GCCC", name="Canarias FIR", country="ES"),
    # Sweden
    Fir(icao="ESAA", name="Sweden FIR", country="SE"),
    # Switzerland
    Fir(icao="LSAS", name="Switzerland FIR", country="CH"),
    # Ukraine
    Fir(icao="UKBV", name="Kyiv FIR", country="UA"),
    Fir(icao="UKDV", name="Dnipro FIR", country="UA"),
    Fir(icao="UKLV", name="Lviv FIR", country="UA"),
    Fir(icao="UKOV", name="Odesa FIR", country="UA"),
    # United Kingdom
    Fir(icao="EGPX", name="Scottish FIR", country="GB"),
    Fir(icao="EGTT", name="London FIR", country="GB"),
    Fir(icao="EGGX", name="Shanwick Oceanic FIR", country="GB"),
]

# Build the registry dict
FIRS: dict[str, Fir] = {fir.icao: fir for fir in _EUROPEAN_FIRS}


def get_fir(icao: str) -> Fir:
    """Return the Fir for the given ICAO code, or a minimal fallback.

    Falls back gracefully when a FIR code is not in the registry yet
    (e.g. because the airport database has an entry for a FIR that
    hasn't been added to this registry). The fallback uses the ICAO
    code as the name, so the device still appears in HA with a
    recognizable identifier rather than crashing.
    """
    return FIRS.get(
        icao,
        Fir(
            icao=icao,
            name=icao,
            country="",
        ),
    )
