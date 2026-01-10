"""WFO to Twitter handle mapping and posting service."""

# NWS Weather Forecast Office Twitter/X handles
# Format: WFO code -> Twitter handle (without @)
WFO_TWITTER_HANDLES = {
    # Central Region
    "ABR": "NWSAberdeen",
    "ARX": "NWSLaCrosse",
    "BIS": "NWSBismarck",
    "BOU": "NWSBoulder",
    "CYS": "NWSCheyenne",
    "DDC": "NWSDodgeCity",
    "DLH": "NWSDuluth",
    "DMX": "NWSDesMoines",
    "DVN": "NWSQuadCities",
    "EAX": "NWSKansasCity",
    "FGF": "NWSGrandForks",
    "FSD": "NWSSiouxFalls",
    "GID": "NWSHastings",
    "GJT": "NWSGrandJunction",
    "GLD": "NWSGoodland",
    "GRB": "NWSGreenBay",
    "GRR": "NWSGrandRapids",
    "ICT": "NWSWichita",
    "ILX": "NWSLincolnIL",
    "IND": "NWSIndianapolis",
    "IWX": "NWSNorthIndiana",
    "JKL": "NWSJacksonKY",
    "LBF": "NWSNorthPlatte",
    "LMK": "NWSLouisville",
    "LOT": "NWSChicago",
    "LSX": "NWSStLouis",
    "MKX": "NWSMilwaukee",
    "MPX": "NWSTwinCities",
    "MQT": "NWSMarquette",
    "OAX": "NWSOmaha",
    "PAH": "NWSPaducah",
    "PUB": "NWSPueblo",
    "RIW": "NWSRiverton",
    "SGF": "NWSSpringfield",
    "TOP": "NWSTopeka",
    "UNR": "NWSRapidCity",

    # Southern Region
    "ABQ": "NWSAlbuquerque",
    "AMA": "NWSAmarillo",
    "BMX": "NWSBirmingham",
    "BRO": "NWSBrownsville",
    "CRP": "NWSCorpusChristi",
    "EPZ": "NWSElPaso",
    "EWX": "NWSSanAntonio",
    "FFC": "NWSAtlanta",
    "FWD": "NWSFortWorth",
    "HGX": "NWSHouston",
    "HUN": "NWSHuntsville",
    "JAN": "NWSJacksonMS",
    "JAX": "NWSJacksonville",
    "KEY": "NWSKeyWest",
    "LCH": "NWSLakeCharles",
    "LIX": "NWSNewOrleans",
    "LUB": "NWSLubbock",
    "LZK": "NWSLittleRock",
    "MAF": "NWSMidland",
    "MEG": "NWSMemphis",
    "MFL": "NWSMiami",
    "MLB": "NWSMelbourne",
    "MOB": "NWSMobile",
    "MRX": "NWSMorristown",
    "OHX": "NWSNashville",
    "OUN": "NWSNorman",
    "SHV": "NWSShreveport",
    "SJT": "NWSSanAngelo",
    "TAE": "NWSTallahassee",
    "TBW": "NWSTampaBay",
    "TSA": "NWSTulsa",

    # Eastern Region
    "AKQ": "NWSWakefield",
    "ALY": "NWSAlbany",
    "BGM": "NWSBinghamton",
    "BOX": "NWSBoston",
    "BTV": "NWSBurlington",
    "BUF": "NWSBuffalo",
    "CAE": "NWSColumbia",
    "CAR": "NWSCaribou",
    "CHS": "NWSCharleston",
    "CLE": "NWSCleveland",
    "CTP": "NWSStateCollege",
    "GSP": "NWSGreen686",
    "GYX": "NWSGray",
    "ILM": "NWSWilmingtonNC",
    "ILN": "NWSWilmingtonOH",
    "LWX": "NWSBaltWash",
    "MHX": "NWSMoreheadCity",
    "OKX": "NWSNewYorkNY",
    "PBZ": "NWSPittsburgh",
    "PHI": "NWSPhiladelphia",
    "RAH": "NWSRaleigh",
    "RLX": "NWSCharleston",
    "RNK": "NWSBlacksburg",

    # Western Region
    "BOI": "NWSBoise",
    "EKA": "NWSEureka",
    "FGZ": "NWSFlagstaff",
    "GGW": "NWSGlasgow",
    "HNX": "NWSHanford",
    "LKN": "NWSElko",
    "LOX": "NWSLosAngeles",
    "MFR": "NWSMedford",
    "MSO": "NWSMissoula",
    "MTR": "NWSBayArea",
    "OTX": "NWSSpokane",
    "PDT": "NWSPendleton",
    "PIH": "NWSPocatello",
    "PQR": "NWSPortland",
    "PSR": "NWSPhoenix",
    "REV": "NWSReno",
    "SEW": "NWSSeattle",
    "SGX": "NWSSanDiego",
    "SLC": "NWSSaltLakeCity",
    "STO": "NWSSacramento",
    "TFX": "NWSGreatFalls",
    "TWC": "NWSTucson",
    "VEF": "NWSVegas",

    # Alaska Region
    "prior": "prior",
    "prior": "NWSPrior",
    "AER": "prior",
    "AFC": "NWSAnchorage",
    "AFG": "NWSFairbanks",
    "AJK": "NWSJuneau",

    # Pacific Region
    "GUM": "NWSGuam",
    "HFO": "NWSHonolulu",
    "PPG": "prior",
}


def get_wfo_twitter_handle(wfo_code: str) -> str | None:
    """Get the Twitter handle for a WFO code."""
    return WFO_TWITTER_HANDLES.get(wfo_code.upper())


def get_wfo_mention(wfo_code: str) -> str:
    """Get the @mention string for a WFO."""
    handle = get_wfo_twitter_handle(wfo_code)
    if handle:
        return f"@{handle}"
    return ""


def format_report_tweet(
    report_type: str,
    description: str,
    latitude: float,
    longitude: float,
    wfo_code: str | None = None,
    severity: int | None = None,
    hail_size: float | None = None,
    wind_speed: int | None = None,
) -> str:
    """Format a weather report for Twitter posting."""
    # Type emoji mapping
    type_emojis = {
        "tornado": "🌪️",
        "funnel_cloud": "🌪️",
        "wall_cloud": "🌀",
        "rotation": "🌀",
        "hail": "🧊",
        "wind_damage": "💨",
        "flooding": "🌊",
        "flash_flood": "🌊",
        "heavy_rain": "🌧️",
        "lightning": "⚡",
        "dust_storm": "🌫️",
        "wildfire": "🔥",
    }

    emoji = type_emojis.get(report_type, "⚠️")
    type_display = report_type.replace("_", " ").title()

    # Build tweet
    parts = [f"{emoji} {type_display} Report"]

    # Add details
    if hail_size:
        parts.append(f"Hail: {hail_size}\"")
    if wind_speed:
        parts.append(f"Wind: {wind_speed} mph")
    if severity:
        severity_labels = {1: "Minor", 2: "Moderate", 3: "Significant", 4: "Severe", 5: "Extreme"}
        parts.append(f"Severity: {severity_labels.get(severity, severity)}")

    # Add description (truncated if needed)
    if description:
        max_desc_len = 180 - len(" ".join(parts)) - 50  # Leave room for location and mentions
        if len(description) > max_desc_len:
            description = description[:max_desc_len-3] + "..."
        parts.append(description)

    # Add location
    parts.append(f"📍 {latitude:.4f}, {longitude:.4f}")

    # Add WFO mention
    if wfo_code:
        mention = get_wfo_mention(wfo_code)
        if mention:
            parts.append(mention)

    # Add hashtags
    parts.append("#wxreport #severewx")

    tweet = "\n".join(parts)

    # Ensure under 280 chars
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet
