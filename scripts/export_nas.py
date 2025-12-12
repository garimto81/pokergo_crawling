"""Export NAS data organized by show/series."""
import json
import os
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path("data/sources/nas/nas_files.json")
OUTPUT_DIR = Path("data/sources/nas/exports")

def slugify(text):
    """Convert text to URL-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')[:50]

def format_size(bytes_size):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"

def categorize_file(file_info):
    """Categorize file into show/series."""
    directory = file_info['directory']
    filename = file_info['filename']

    # Parse directory structure
    parts = directory.replace('/', '\\').split('\\')

    if 'WSOP' in directory:
        # WSOP content
        if 'ARCHIVE (PRE-2016)' in directory:
            # Find year
            for part in parts:
                if part.startswith('WSOP ') and len(part) == 9:
                    return f"WSOP {part[-4:]}"
            return "WSOP Archive"
        elif 'Bracelet Event' in directory:
            # Find location and year
            for i, part in enumerate(parts):
                if part.startswith('WSOP-'):
                    location = part.replace('WSOP-', '')
                    # Look for year in next part
                    if i + 1 < len(parts):
                        year_match = re.search(r'(\d{4})', parts[i+1])
                        if year_match:
                            return f"WSOP {location} {year_match.group(1)}"
                    return f"WSOP {location}"
            return "WSOP Bracelet"
        elif 'Circuit Event' in directory:
            return "WSOP Circuit"
        return "WSOP Other"

    elif 'PAD' in directory:
        # Poker After Dark
        for part in parts:
            if part.startswith('PAD S'):
                return f"Poker After Dark {part}"
        return "Poker After Dark"

    elif 'GOG' in directory:
        # GOG content
        for part in parts:
            if part.startswith('e') and len(part) <= 3:
                return f"GOG Episode {part[1:]}"
        return "GOG"

    elif 'GGMillions' in directory:
        return "GG Millions"

    elif 'MPP' in directory:
        return "MPP"

    elif 'HCL' in directory:
        return "Hustler Casino Live"

    elif directory == 'Clips':
        return "Clips"

    return "Other"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOWS_DIR = OUTPUT_DIR / "shows"
    SHOWS_DIR.mkdir(exist_ok=True)

    # Load files
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    files = data['files']
    print(f"Processing {len(files)} files...")

    # Categorize files
    by_show = defaultdict(list)
    for f in files:
        show = categorize_file(f)
        by_show[show].append(f)

    # Create show files and index
    index = {
        "version": "1.0",
        "source": "nas",
        "total_files": len(files),
        "total_shows": len(by_show),
        "shows": []
    }

    for show_name, show_files in sorted(by_show.items()):
        slug = slugify(show_name)
        filename = f"{slug}.json"

        total_size = sum(f['size_bytes'] for f in show_files)

        show_data = {
            "slug": slug,
            "name": show_name,
            "count": len(show_files),
            "files": show_files
        }

        with open(SHOWS_DIR / filename, 'w', encoding='utf-8') as f:
            json.dump(show_data, f, ensure_ascii=False)

        file_size = (SHOWS_DIR / filename).stat().st_size

        index['shows'].append({
            "slug": slug,
            "name": show_name,
            "count": len(show_files),
            "total_size": total_size,
            "total_size_formatted": format_size(total_size),
            "file": f"shows/{filename}",
            "file_size": file_size
        })

    # Sort by count
    index['shows'].sort(key=lambda x: -x['count'])

    # Save index
    with open(OUTPUT_DIR / "index.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nCreated {len(index['shows'])} show files")
    print(f"\nBy Show:")
    for show in index['shows'][:20]:
        print(f"  [{show['count']:>4}] {show['name']:<40} ({show['total_size_formatted']})")

    if len(index['shows']) > 20:
        print(f"  ... and {len(index['shows']) - 20} more")

if __name__ == "__main__":
    main()
