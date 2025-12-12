"""Test matching with 20 random samples based on PRD-0033."""
import json
import re
import random
from pathlib import Path
from rapidfuzz import fuzz, process

# ============================================================
# DICTIONARIES (from PRD-0033)
# ============================================================

PLAYER_ALIASES = {
    "phil_hellmuth": ["hellmuth", "phil hellmuth", "poker brat"],
    "daniel_negreanu": ["negreanu", "daniel negreanu", "dnegs", "kidpoker"],
    "phil_ivey": ["ivey", "phil ivey"],
    "tom_dwan": ["dwan", "tom dwan", "durrrr"],
    "patrik_antonius": ["antonius", "patrik antonius"],
    "doug_polk": ["polk", "doug polk"],
    "doyle_brunson": ["brunson", "doyle brunson", "texas dolly"],
    "mike_matusow": ["matusow", "mike matusow", "the mouth"],
    "antonio_esfandiari": ["esfandiari", "antonio esfandiari", "the magician"],
    "shaun_deeb": ["deeb", "shaun deeb"],
    "justin_bonomo": ["bonomo", "justin bonomo"],
    "jeremy_ausmus": ["ausmus", "jeremy ausmus"],
    "chris_hunichen": ["hunichen", "chris hunichen"],
    "seth_davies": ["davies", "seth davies"],
    "jason_koon": ["koon", "jason koon"],
    "stephen_chidwick": ["chidwick", "stephen chidwick"],
    "ali_imsirovic": ["imsirovic", "ali imsirovic"],
    "nick_petrangelo": ["petrangelo", "nick petrangelo"],
    "sam_soverel": ["soverel", "sam soverel"],
    "david_peters": ["peters", "david peters"],
    "bryn_kenney": ["kenney", "bryn kenney"],
    "sean_perry": ["perry", "sean perry"],
    "chance_kornuth": ["kornuth", "chance kornuth"],
    "michael_addamo": ["addamo", "michael addamo"],
    "nik_airball": ["airball", "nik airball", "nikhil"],
    "garrett_adelstein": ["adelstein", "garrett adelstein", "garrett"],
    "eric_persson": ["persson", "eric persson"],
    "alan_keating": ["keating", "alan keating"],
    "wesley_fei": ["wesley", "fei", "wesley fei"],
    "stanley_tang": ["stanley", "tang", "stanley tang"],
    "mike_nia": ["nia", "mike nia"],
    "matt_berkey": ["berkey", "matt berkey"],
    "landon_tice": ["tice", "landon tice"],
    "mariano": ["mariano"],
    "bleznick": ["bleznick"],
    "strelitz": ["strelitz"],
}

EVENT_TYPES = {
    "wsop": ["wsop", "world series of poker", "world series", "bracelet"],
    "hsp": ["high stakes poker", "hsp"],
    "pad": ["poker after dark", "pad"],
    "shrb": ["super high roller bowl", "shrb", "shr bowl", "super high roller"],
    "hsd": ["high stakes duel", "hsd"],
    "pgt": ["pokergo tour", "pgt"],
    "uspo": ["us poker open", "uspo", "u.s. poker open"],
    "pm": ["poker masters"],
    "ngnf": ["no gamble no future", "ngnf"],
    "hcl": ["hustler casino live", "hcl"],
}

GAME_TYPES = {
    "nlh": ["nlh", "no limit hold", "no-limit hold", "holdem", "hold'em", "nlhe"],
    "plo": ["plo", "pot limit omaha", "omaha"],
    "27td": ["2-7 triple draw", "27td", "2-7 td", "triple draw", "2-7"],
    "stud": ["stud", "razz"],
    "mixed": ["mixed", "horse", "8-game"],
}

# ============================================================
# FEATURE EXTRACTORS
# ============================================================

def extract_year(text):
    """Extract year from text."""
    match = re.search(r'20[0-2][0-9]', text)
    if match:
        return match.group()
    # Try 2-digit year
    match = re.search(r'(?:^|[^0-9])([0-2][0-9])(?:[^0-9]|$)', text)
    if match:
        year = int(match.group(1))
        if year >= 0 and year <= 25:
            return f"20{match.group(1).zfill(2)}"
    return None

def extract_players(text):
    """Extract player names from text."""
    text_lower = text.lower()
    found = []
    for canonical, aliases in PLAYER_ALIASES.items():
        for alias in aliases:
            if alias in text_lower:
                found.append(canonical)
                break
    return list(set(found))

def extract_event_type(text):
    """Extract event type from text."""
    text_lower = text.lower()
    for event, keywords in EVENT_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return event
    return None

def extract_game_type(text):
    """Extract game type from text."""
    text_lower = text.lower()
    for game, keywords in GAME_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return game
    return None

def normalize_text(text):
    """Normalize text for fuzzy matching."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_features(text, source="youtube"):
    """Extract all features from text."""
    return {
        "year": extract_year(text),
        "players": extract_players(text),
        "event": extract_event_type(text),
        "game": extract_game_type(text),
        "normalized": normalize_text(text),
        "original": text
    }

# ============================================================
# SCORING
# ============================================================

def calculate_score(yt_features, nas_features):
    """Calculate match score between YouTube and NAS features."""
    score = 0
    details = []

    # 1. Year Match (+30)
    if yt_features["year"] and nas_features["year"]:
        if yt_features["year"] == nas_features["year"]:
            score += 30
            details.append(f"year:{yt_features['year']}=+30")
    elif yt_features["year"] is None or nas_features["year"] is None:
        score += 5  # Partial credit
        details.append("year:unknown=+5")

    # 2. Player Match (+30 max)
    common_players = set(yt_features["players"]) & set(nas_features["players"])
    if common_players:
        player_score = min(30, len(common_players) * 15)
        score += player_score
        details.append(f"players:{list(common_players)}=+{player_score}")

    # 3. Event Type Match (+20)
    if yt_features["event"] and nas_features["event"]:
        if yt_features["event"] == nas_features["event"]:
            score += 20
            details.append(f"event:{yt_features['event']}=+20")

    # 4. Game Type Match (+10)
    if yt_features["game"] and nas_features["game"]:
        if yt_features["game"] == nas_features["game"]:
            score += 10
            details.append(f"game:{yt_features['game']}=+10")

    # 5. Fuzzy Match (+10 max)
    similarity = fuzz.token_set_ratio(
        yt_features["normalized"],
        nas_features["normalized"]
    )
    fuzzy_score = int(similarity * 0.1)
    score += fuzzy_score
    details.append(f"fuzzy:{similarity}%=+{fuzzy_score}")

    return score, details

# ============================================================
# MAIN
# ============================================================

def main():
    # Load YouTube data
    print("Loading YouTube data...")
    yt_videos = []
    index_path = Path("data/sources/youtube/exports/index_v3.json")
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    for pl in index['playlists']:
        pl_path = Path("data/sources/youtube/exports") / pl['file']
        if pl_path.exists():
            with open(pl_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for v in data['videos']:
                    yt_videos.append({
                        "title": v['title'],
                        "video_id": v['video_id'],
                        "playlist": pl['name']
                    })

    print(f"Loaded {len(yt_videos)} YouTube videos")

    # Load NAS data
    print("Loading NAS data...")
    with open("data/sources/nas/nas_files.json", 'r', encoding='utf-8') as f:
        nas_data = json.load(f)
    nas_files = nas_data['files']
    print(f"Loaded {len(nas_files)} NAS files")

    # Pre-extract NAS features
    print("Extracting NAS features...")
    nas_features_list = []
    for f in nas_files:
        combined = f"{f['filename']} {f['directory']}"
        features = extract_features(combined, source="nas")
        features["filename"] = f['filename']
        features["directory"] = f['directory']
        nas_features_list.append(features)

    # Select 20 random YouTube videos (prefer those with player names or event info)
    print("\nSelecting 20 random YouTube samples...")
    candidates = []
    for v in yt_videos:
        features = extract_features(v['title'], source="youtube")
        if features['players'] or features['event']:
            candidates.append((v, features))

    # Random sample
    random.seed(42)  # For reproducibility
    samples = random.sample(candidates, min(20, len(candidates)))

    # Matching
    print("\n" + "="*80)
    print("MATCHING RESULTS (20 Samples)")
    print("="*80)

    results = []
    for i, (yt_video, yt_features) in enumerate(samples, 1):
        # Find best match
        best_match = None
        best_score = 0
        best_details = []

        for nas_features in nas_features_list:
            score, details = calculate_score(yt_features, nas_features)
            if score > best_score:
                best_score = score
                best_match = nas_features
                best_details = details

        # Determine category
        if best_score >= 80:
            category = "CONFIDENT"
        elif best_score >= 60:
            category = "LIKELY"
        elif best_score >= 40:
            category = "POSSIBLE"
        else:
            category = "NO MATCH"

        results.append({
            "youtube": yt_video['title'],
            "nas": best_match['filename'] if best_match else None,
            "score": best_score,
            "category": category,
            "details": best_details
        })

        # Print result
        print(f"\n[{i}/20] Score: {best_score} ({category})")
        print(f"  YouTube: {yt_video['title'][:70]}...")
        print(f"  YT Features: year={yt_features['year']}, event={yt_features['event']}, players={yt_features['players'][:3]}")
        if best_match:
            print(f"  NAS Match: {best_match['filename'][:70]}...")
            print(f"  NAS Features: year={best_match['year']}, event={best_match['event']}, players={best_match['players'][:3]}")
        print(f"  Scoring: {', '.join(best_details)}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    categories = {"CONFIDENT": 0, "LIKELY": 0, "POSSIBLE": 0, "NO MATCH": 0}
    for r in results:
        categories[r['category']] += 1

    print(f"  CONFIDENT (>=80): {categories['CONFIDENT']}")
    print(f"  LIKELY (60-79):   {categories['LIKELY']}")
    print(f"  POSSIBLE (40-59): {categories['POSSIBLE']}")
    print(f"  NO MATCH (<40):   {categories['NO MATCH']}")

    avg_score = sum(r['score'] for r in results) / len(results)
    print(f"\n  Average Score: {avg_score:.1f}")

if __name__ == "__main__":
    main()
