"""Database initialization and seed data for NAMS."""
from .models import Base, EventType, ExclusionRule, Pattern, Region
from .session import engine, get_db_context


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created")


def seed_regions():
    """Seed initial region data."""
    regions = [
        {"code": "LV", "name": "Las Vegas", "description": "Main WSOP venue (default)"},
        {"code": "APAC", "name": "Asia Pacific", "description": "WSOP APAC events"},
        {"code": "EU", "name": "Europe", "description": "WSOP Europe events"},
        {
            "code": "PARADISE",
            "name": "Paradise (Bahamas)",
            "description": "WSOP Paradise events at Atlantis",
        },
        {"code": "LA", "name": "Los Angeles", "description": "WSOP Circuit LA events"},
        {
            "code": "CYPRUS",
            "name": "Cyprus",
            "description": "WSOP Super Circuit / MPP Cyprus events",
        },
        {"code": "LONDON", "name": "London", "description": "WSOP Super Circuit London events"},
    ]

    with get_db_context() as db:
        for r in regions:
            existing = db.query(Region).filter(Region.code == r["code"]).first()
            if not existing:
                db.add(Region(**r))
        db.commit()
    print(f"[OK] Seeded {len(regions)} regions")


def seed_event_types():
    """Seed initial event type data."""
    event_types = [
        {"code": "ME", "name": "Main Event", "description": "WSOP Main Event"},
        {"code": "GM", "name": "Grudge Match", "description": "Grudge Match events"},
        {"code": "HU", "name": "Heads Up", "description": "Heads Up Championship"},
        {"code": "BR", "name": "Bracelet", "description": "Bracelet events"},
        {"code": "HR", "name": "High Roller", "description": "High Roller events"},
        {"code": "FT", "name": "Final Table", "description": "Final Table coverage"},
        {"code": "BEST", "name": "Best Of", "description": "Best Of compilations"},
        {
            "code": "BEST-ALLINS",
            "name": "Best Of All-Ins",
            "description": "Best All-In moments",
        },
        {
            "code": "BEST-BLUFFS",
            "name": "Best Of Bluffs",
            "description": "Best Bluff moments",
        },
        {
            "code": "BEST-MM",
            "name": "Best Of Moneymaker",
            "description": "Chris Moneymaker highlights",
        },
        {"code": "UNK", "name": "Unknown", "description": "Unclassified content"},
    ]

    with get_db_context() as db:
        for et in event_types:
            existing = db.query(EventType).filter(EventType.code == et["code"]).first()
            if not existing:
                db.add(EventType(**et))
        db.commit()
    print(f"[OK] Seeded {len(event_types)} event types")


# Pattern configuration - easily maintainable outside of code logic
PATTERNS_CONFIG = [
    (
        "WSOP_BR_LV_2025_ME",
        1,
        r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT",
        True,
        "LV",
        "ME",
        True,
        "2025 Las Vegas Main Event",
    ),
    (
        "WSOP_BR_LV_2025_SIDE",
        2,
        r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE",
        True,
        "LV",
        "BR",
        True,
        "2025 Las Vegas Side Events",
    ),
    (
        "WSOP_BR_EU_2025",
        3,
        r"WSOP.*Bracelet.*EUROPE.*2025",
        True,
        "EU",
        None,
        True,
        "2025 WSOP Europe",
    ),
    (
        "WSOP_BR_EU",
        4,
        r"WSOP.*Bracelet.*EUROPE",
        True,
        "EU",
        None,
        True,
        "WSOP Europe (2008-2024)",
    ),
    (
        "WSOP_BR_PARADISE",
        5,
        r"WSOP.*Bracelet.*PARADISE",
        True,
        "PARADISE",
        None,
        True,
        "WSOP Paradise",
    ),
    (
        "WSOP_BR_LV",
        6,
        r"WSOP.*Bracelet.*LAS.?VEGAS",
        True,
        "LV",
        None,
        True,
        "WSOP Las Vegas (2021-2024)",
    ),
    (
        "WSOP_CIRCUIT_LA",
        7,
        r"WSOP.*Circuit.*LA",
        True,
        "LA",
        None,
        True,
        "WSOP Circuit LA",
    ),
    (
        "WSOP_CIRCUIT_SUPER",
        8,
        r"WSOP.*Super.?Circuit",
        True,
        None,
        None,
        False,
        "WSOP Super Circuit (London, Cyprus)",
    ),
    (
        "WSOP_ARCHIVE_PRE2016",
        9,
        r"WSOP.*ARCHIVE.*PRE-?2016",
        True,
        "LV",
        None,
        True,
        "WSOP Archive Pre-2016 (1973-2016)",
    ),
    (
        "PAD",
        10,
        r"PAD.*(pad-s\d{2}-ep\d{2}|PAD_S\d{2}_EP\d{2})",
        False,
        None,
        None,
        True,
        "Poker After Dark",
    ),
    ("GOG", 11, r"GOG.*E\d{2}[_\-]GOG", False, None, None, True, "Game of Gold"),
    (
        "MPP_ME",
        12,
        r"MPP.*Main.?Event",
        True,
        "CYPRUS",
        "ME",
        False,
        "MPP Main Event",
    ),
    (
        "MPP",
        13,
        r"MPP.*\$\d+[MK]?\s*GTD",
        True,
        "CYPRUS",
        None,
        False,
        "Merit Poker Premier",
    ),
    (
        "GGMILLIONS",
        14,
        r"GGMillions.*Super.*High.*Roller",
        False,
        None,
        "HR",
        False,
        "GGMillions Super High Roller",
    ),
    # CLASSIC Era patterns (P02/P03 fix - 1973-2002)
    (
        "WSOP_CLASSIC_UNDERSCORE",
        15,
        r"WSOP[_\-](\d{4})\.(mov|mxf|mp4)",
        True,
        "LV",
        "ME",
        False,
        "CLASSIC Era: WSOP_1983.mov",
    ),
    (
        "WSOP_CLASSIC_DASH",
        16,
        r"WSOP\s*-\s*(\d{4})\.(mov|mxf|mp4)",
        True,
        "LV",
        "ME",
        False,
        "CLASSIC Era: WSOP - 1973.mp4",
    ),
    (
        "WSOP_CLASSIC_LOWERCASE",
        17,
        r"wsop-(\d{4})-me",
        True,
        "LV",
        "ME",
        True,
        "CLASSIC Era: wsop-1973-me-nobug.mp4",
    ),
    # WSOPE patterns (P02/P03/P04 fix)
    (
        "WSOPE_EPISODE",
        18,
        r"WSOPE(\d{2})_Episode_(\d+)",
        True,
        "EU",
        None,
        True,
        "WSOPE08_Episode_1_H264.mov",
    ),
    (
        "WSOPE_LOWERCASE",
        19,
        r"wsope-(\d{4})-\d+k?-[a-z]+-ft-(\d+)",
        True,
        "EU",
        None,
        True,
        "wsope-2021-10k-me-ft-004.mp4",
    ),
    # Modern WSOP patterns
    (
        "WSOP_YEAR_ME",
        20,
        r"WSOP\s+(\d{4})\s+Main\s*Event",
        True,
        "LV",
        "ME",
        True,
        "WSOP 2017 Main Event _ Episode 10.mp4",
    ),
    (
        "WSOP_WS_FORMAT",
        21,
        r"WS(\d{2})[_\-](ME|GM|HU|BR)(\d{2})",
        True,
        "LV",
        None,
        True,
        "WS11_ME25_NB.mp4",
    ),
    # Path-based patterns (Event Type from folder structure)
    (
        "WSOP_YEAR_DASH_EP",
        22,
        r"WSOP_(\d{4})-(\d+)\.(mxf|mov|mp4)",
        True,
        "LV",
        None,
        True,
        "WSOP_2003-01.mxf (Event Type from path)",
    ),
    (
        "WSOP_YEAR_UNDERSCORE_EP",
        23,
        r"WSOP_(\d{4})_(\d+)\.(mxf|mov|mp4)",
        True,
        "LV",
        None,
        True,
        "WSOP_2005_01.mxf (Event Type from path)",
    ),
    # BOOM Era patterns (2003-2010)
    (
        "BOOM_YEAR_WSOP_ME",
        24,
        r"(\d{4})\s+WSOP\s+ME(\d+)",
        True,
        "LV",
        "ME",
        True,
        "2009 WSOP ME01.mov",
    ),
    (
        "BOOM_WSOP_YEAR_SHOW",
        25,
        r"WSOP\s+(\d{4})\s+Show\s+(\d+)",
        True,
        "LV",
        None,
        True,
        "WSOP 2005 Show 10_xxx.mov",
    ),
    (
        "ESPN_WSOP_SHOW",
        26,
        r"ESPN\s+(\d{4})\s+WSOP.*SHOW\s+(\d+)",
        True,
        "LV",
        "ME",
        True,
        "ESPN 2007 WSOP SEASON 5 SHOW 1.mov",
    ),
    (
        "BOOM_YEAR_WSOP_SHOW",
        27,
        r"(\d{4})\s+WSOP\s+Show\s+(\d+)",
        True,
        "LV",
        None,
        True,
        "2004 WSOP Show 13 ME 01.mov",
    ),
    (
        "BOOM_WSOP_BEST",
        28,
        r"(\d{4})\s+WSOP\s+Best",
        True,
        "LV",
        "BEST",
        False,
        "2003 WSOP Best of ALL INS.mov",
    ),
    (
        "CLASSIC_WORLD_SERIES",
        29,
        r"(\d{4})\s+World\s+Series\s+of\s+Poker",
        True,
        "LV",
        "ME",
        False,
        "1995 World Series of Poker.mov",
    ),
    # Additional patterns
    (
        "WSOP_BEST_OF",
        30,
        r"WSOP_(\d{4})_Best_Of",
        True,
        "LV",
        "BEST",
        False,
        "WSOP_2003_Best_Of_Amazing_All-Ins.mxf",
    ),
    (
        "WSOP_TOC",
        31,
        r"(\d{4})\s+WSOP\s+Tournament\s+of\s+Champ",
        True,
        "LV",
        "BR",
        False,
        "2004 WSOP Tournament of Champs.mov",
    ),
    (
        "WSOP_LOCATION",
        32,
        r"WSOP\s+(\d{4})\s+(Lake\s*Tahoe|New\s*Orleans|Rio|Rincon)",
        True,
        "LV",
        None,
        False,
        "WSOP 2005 Lake Tahoe CC.mov",
    ),
    (
        "WCLA_PE_ET",
        33,
        r"W(CLA|P)(\d{2})-(PE|ET|EP)-(\d+)",
        True,
        "LA",
        None,
        True,
        "WCLA23-PE-01.mkv (Player Emotion)",
    ),
]


def _create_pattern_if_not_exists(db, config: tuple) -> bool:
    """Create a pattern if it doesn't exist. Returns True if created."""
    name, priority, regex, extract_year, region, etype, extract_ep, desc = config
    existing = db.query(Pattern).filter(Pattern.name == name).first()
    if not existing:
        db.add(Pattern(
            name=name, priority=priority, regex=regex,
            extract_year=extract_year, extract_region=region,
            extract_type=etype, extract_episode=extract_ep,
            description=desc
        ))
        return True
    return False


def seed_patterns():
    """Seed initial pattern definitions based on full path analysis."""
    with get_db_context() as db:
        sum(1 for cfg in PATTERNS_CONFIG if _create_pattern_if_not_exists(db, cfg))
        db.commit()
    print(f"[OK] Seeded {len(PATTERNS_CONFIG)} patterns")


def seed_exclusion_rules():
    """Seed initial exclusion rules."""
    rules = [
        {
            "rule_type": "size",
            "operator": "lt",
            "value": "1073741824",  # 1GB in bytes
            "description": "1GB 미만 파일 제외 (저화질/프리뷰)",
        },
        {
            "rule_type": "duration",
            "operator": "lt",
            "value": "3600",  # 1 hour in seconds
            "description": "1시간 미만 영상 제외 (클립/프리뷰)",
        },
        {
            "rule_type": "keyword",
            "operator": "contains",
            "value": "clip",
            "description": "클립 영상 제외",
        },
        {
            "rule_type": "keyword",
            "operator": "contains",
            "value": "highlight",
            "description": "하이라이트 영상 제외",
        },
        {
            "rule_type": "keyword",
            "operator": "contains",
            "value": "circuit",
            "description": "WSOP Circuit 제외 (별도 이벤트)",
        },
        {
            "rule_type": "keyword",
            "operator": "contains",
            "value": "paradise",
            "description": "WSOP Paradise 제외 (PokerGO 데이터 없음)",
        },
    ]

    with get_db_context() as db:
        for r in rules:
            existing = db.query(ExclusionRule).filter(
                ExclusionRule.rule_type == r["rule_type"],
                ExclusionRule.value == r["value"]
            ).first()
            if not existing:
                db.add(ExclusionRule(**r))
        db.commit()
    print(f"[OK] Seeded {len(rules)} exclusion rules")


def init_database():
    """Initialize database with tables and seed data."""
    print("Initializing NAMS database...")
    create_tables()
    seed_regions()
    seed_event_types()
    seed_patterns()
    seed_exclusion_rules()
    print("[OK] Database initialization complete")


if __name__ == "__main__":
    init_database()
