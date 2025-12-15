"""Database initialization and seed data for NAMS."""
from .models import Base, Pattern, Region, EventType, PokergoEpisode
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
        {"code": "PARADISE", "name": "Paradise (Bahamas)", "description": "WSOP Paradise events at Atlantis"},
        {"code": "LA", "name": "Los Angeles", "description": "WSOP Circuit LA events"},
        {"code": "CYPRUS", "name": "Cyprus", "description": "WSOP Super Circuit / MPP Cyprus events"},
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
        {"code": "BEST-ALLINS", "name": "Best Of All-Ins", "description": "Best All-In moments"},
        {"code": "BEST-BLUFFS", "name": "Best Of Bluffs", "description": "Best Bluff moments"},
        {"code": "BEST-MM", "name": "Best Of Moneymaker", "description": "Chris Moneymaker highlights"},
        {"code": "UNK", "name": "Unknown", "description": "Unclassified content"},
    ]

    with get_db_context() as db:
        for et in event_types:
            existing = db.query(EventType).filter(EventType.code == et["code"]).first()
            if not existing:
                db.add(EventType(**et))
        db.commit()
    print(f"[OK] Seeded {len(event_types)} event types")


def seed_patterns():
    """Seed initial pattern definitions based on full path analysis."""
    patterns = [
        {
            "name": "WSOP_BR_LV_2025_ME",
            "priority": 1,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": "ME",
            "extract_episode": False,
            "description": "2025 Las Vegas Main Event",
        },
        {
            "name": "WSOP_BR_LV_2025_SIDE",
            "priority": 2,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": "BR",
            "extract_episode": False,
            "description": "2025 Las Vegas Side Events",
        },
        {
            "name": "WSOP_BR_EU_2025",
            "priority": 3,
            "regex": r"WSOP.*Bracelet.*EUROPE.*2025",
            "extract_year": True,
            "extract_region": "EU",
            "extract_type": None,
            "extract_episode": False,
            "description": "2025 WSOP Europe",
        },
        {
            "name": "WSOP_BR_EU",
            "priority": 4,
            "regex": r"WSOP.*Bracelet.*EUROPE",
            "extract_year": True,
            "extract_region": "EU",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Europe (2008-2024)",
        },
        {
            "name": "WSOP_BR_PARADISE",
            "priority": 5,
            "regex": r"WSOP.*Bracelet.*PARADISE",
            "extract_year": True,
            "extract_region": "PARADISE",
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Paradise",
        },
        {
            "name": "WSOP_BR_LV",
            "priority": 6,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Las Vegas (2021-2024)",
        },
        {
            "name": "WSOP_CIRCUIT_LA",
            "priority": 7,
            "regex": r"WSOP.*Circuit.*LA",
            "extract_year": True,
            "extract_region": "LA",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Circuit LA",
        },
        {
            "name": "WSOP_CIRCUIT_SUPER",
            "priority": 8,
            "regex": r"WSOP.*Super.?Circuit",
            "extract_year": True,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Super Circuit (London, Cyprus)",
        },
        {
            "name": "WSOP_ARCHIVE_PRE2016",
            "priority": 9,
            "regex": r"WSOP.*ARCHIVE.*PRE-?2016",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Archive Pre-2016 (1973-2016)",
        },
        {
            "name": "PAD",
            "priority": 10,
            "regex": r"PAD.*(pad-s\d{2}-ep\d{2}|PAD_S\d{2}_EP\d{2})",
            "extract_year": False,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": True,
            "description": "Poker After Dark",
        },
        {
            "name": "GOG",
            "priority": 11,
            "regex": r"GOG.*E\d{2}[_\-]GOG",
            "extract_year": False,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": True,
            "description": "Game of Gold",
        },
        {
            "name": "MPP_ME",
            "priority": 12,
            "regex": r"MPP.*Main.?Event",
            "extract_year": True,
            "extract_region": "CYPRUS",
            "extract_type": "ME",
            "extract_episode": False,
            "description": "MPP Main Event",
        },
        {
            "name": "MPP",
            "priority": 13,
            "regex": r"MPP.*\$\d+[MK]?\s*GTD",
            "extract_year": True,
            "extract_region": "CYPRUS",
            "extract_type": None,
            "extract_episode": False,
            "description": "Merit Poker Premier",
        },
        {
            "name": "GGMILLIONS",
            "priority": 14,
            "regex": r"GGMillions.*Super.*High.*Roller",
            "extract_year": False,
            "extract_region": None,
            "extract_type": "HR",
            "extract_episode": False,
            "description": "GGMillions Super High Roller",
        },
    ]

    with get_db_context() as db:
        for p in patterns:
            existing = db.query(Pattern).filter(Pattern.name == p["name"]).first()
            if not existing:
                db.add(Pattern(**p))
        db.commit()
    print(f"[OK] Seeded {len(patterns)} patterns")


def init_database():
    """Initialize database with tables and seed data."""
    print("Initializing NAMS database...")
    create_tables()
    seed_regions()
    seed_event_types()
    seed_patterns()
    print("[OK] Database initialization complete")


if __name__ == "__main__":
    init_database()
