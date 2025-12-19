# -*- coding: utf-8 -*-
"""NAS 파일 패턴 분석 및 최적 규칙 제안"""
import json
from collections import defaultdict
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/sources/nas/nas_files.json', 'r', encoding='utf-8') as f:
    nas_data = json.load(f)

files = nas_data.get('files', [])
wsop_files = []
for f in files:
    filename = f.get('filename', '')
    directory = f.get('directory', '')
    size_gb = f.get('size_bytes', 0) / (1024**3)
    combined = (filename + ' ' + directory).upper()

    if size_gb >= 1.0 and 'WSOP' in combined:
        if not any(x in combined.lower() for x in ['clip', 'circuit', 'paradise']):
            wsop_files.append({'filename': filename, 'directory': directory})

print('=' * 80)
print('SUGGESTED PATTERN RULES FOR NAS FILES')
print('=' * 80)

def extract_info(fn, directory):
    fn_upper = fn.upper()
    dir_upper = directory.upper()

    info = {
        'year': None,
        'region': None,
        'event_type': None,
        'episode': None,
        'pattern_used': None
    }

    # === REGION (check first) ===
    if 'APAC' in fn_upper or 'ASIA' in fn_upper:
        info['region'] = 'APAC'
    elif 'WSOPE' in fn_upper or 'EUROPE' in fn_upper or 'WSOP-EUROPE' in dir_upper:
        info['region'] = 'EUROPE'

    # P0: WSOP{YY}_APAC_{TYPE}{EP} or WSOP{YY}_APAC_*_SHOW
    m = re.match(r'WSOP(\d{2})[_\-]APAC[_\-]([A-Z_]+?)[_\-]?(?:SHOW\s*)?(\d+)', fn_upper)
    if m:
        y = int(m.group(1))
        info['year'] = f'20{y:02d}' if y <= 30 else f'19{y:02d}'
        event = m.group(2).replace('_', ' ').strip()
        if 'ME' in event or 'MAIN' in event:
            info['event_type'] = 'MAIN_EVENT'
        elif 'HIGH' in event:
            info['event_type'] = 'HIGH_ROLLER'
        else:
            info['event_type'] = event
        info['episode'] = int(m.group(3))
        info['region'] = 'APAC'
        info['pattern_used'] = 'P0: WSOP{YY}_APAC_*'
        return info

    # P1: WS{YY}_{TYPE}{EP}
    m = re.match(r'WS(\d{2})[_\-]([A-Z]{2})(\d{1,2})', fn_upper)
    if m:
        y = int(m.group(1))
        info['year'] = f'20{y:02d}' if y <= 30 else f'19{y:02d}'
        code = m.group(2)
        type_map = {'ME': 'MAIN_EVENT', 'GM': 'GRUDGE_MATCH', 'HU': 'HEADS_UP', 'BR': 'BRACELET'}
        info['event_type'] = type_map.get(code, code)
        info['episode'] = int(m.group(3))
        info['pattern_used'] = 'P1: WS{YY}_{TYPE}{EP}'
        return info

    # P2: WSOP{YY}_{TYPE}{EP}
    m = re.match(r'WSOP(\d{2})[_\-]([A-Z]{2})(\d{1,2})', fn_upper)
    if m:
        y = int(m.group(1))
        info['year'] = f'20{y:02d}' if y <= 30 else f'19{y:02d}'
        code = m.group(2)
        type_map = {'ME': 'MAIN_EVENT', 'GM': 'GRUDGE_MATCH', 'HU': 'HEADS_UP', 'BR': 'BRACELET'}
        info['event_type'] = type_map.get(code, code)
        info['episode'] = int(m.group(3))
        info['pattern_used'] = 'P2: WSOP{YY}_{TYPE}{EP}'
        return info

    # P3: WSOP_{YYYY}_{SEQ}_{TYPE}{EP}
    m = re.match(r'WSOP[_\-](\d{4})[_\-]\d+[_\-]([A-Z]{2})(\d{1,2})', fn_upper)
    if m:
        info['year'] = m.group(1)
        code = m.group(2)
        type_map = {'ME': 'MAIN_EVENT', 'GM': 'GRUDGE_MATCH', 'HU': 'HEADS_UP'}
        info['event_type'] = type_map.get(code, code)
        info['episode'] = int(m.group(3))
        info['pattern_used'] = 'P3: WSOP_{YYYY}_{SEQ}_{TYPE}{EP}'
        return info

    # P4: WSOPE{YY}*Episode*{EP}
    m = re.search(r'WSOPE(\d{2})[_\-]?(?:EPISODE)?[_\-]?(\d+)', fn_upper)
    if m:
        y = int(m.group(1))
        info['year'] = f'20{y:02d}' if y <= 30 else f'19{y:02d}'
        info['region'] = 'EUROPE'
        info['event_type'] = 'MAIN_EVENT'
        info['episode'] = int(m.group(2))
        info['pattern_used'] = 'P4: WSOPE{YY}_Episode_{EP}'
        return info

    # P5: {YYYY} World Series... Main Event Show {##}
    m = re.match(r'(\d{4})\s+WORLD\s+SERIES.*?MAIN\s*EVENT.*?SHOW\s*(\d+)', fn_upper)
    if m:
        info['year'] = m.group(1)
        info['event_type'] = 'MAIN_EVENT'
        info['episode'] = int(m.group(2))
        info['pattern_used'] = 'P5: {YYYY} World Series...Main Event Show'
        return info

    # P6: {YYYY} WSOP Show {##} ME {##}
    m = re.match(r'(\d{4})\s+WSOP.*?SHOW\s*(\d+).*?ME\s*(\d+)', fn_upper)
    if m:
        info['year'] = m.group(1)
        info['event_type'] = 'MAIN_EVENT'
        info['episode'] = int(m.group(3))
        info['pattern_used'] = 'P6: {YYYY} WSOP Show ME'
        return info

    # P7: WSOP {YYYY} Show {##} ME {##}
    m = re.match(r'WSOP\s+(\d{4}).*?SHOW\s*(\d+).*?ME\s*(\d+)', fn_upper)
    if m:
        info['year'] = m.group(1)
        info['event_type'] = 'MAIN_EVENT'
        info['episode'] = int(m.group(3))
        info['pattern_used'] = 'P7: WSOP {YYYY} Show ME'
        return info

    # P8: {YYYY} WSOP ME{##}
    m = re.match(r'(\d{4})\s+WSOP\s+ME(\d+)', fn_upper)
    if m:
        info['year'] = m.group(1)
        info['event_type'] = 'MAIN_EVENT'
        info['episode'] = int(m.group(2))
        info['pattern_used'] = 'P8: {YYYY} WSOP ME{##}'
        return info

    # P9: wsop-{yyyy}-me-*
    m = re.match(r'WSOP[-_](\d{4})[-_]ME', fn_upper)
    if m:
        info['year'] = m.group(1)
        info['event_type'] = 'MAIN_EVENT'
        info['pattern_used'] = 'P9: wsop-{yyyy}-me-*'
        return info

    # P10: Folder year extraction + filename parsing
    dir_year = re.search(r'WSOP\s*(\d{4})', dir_upper)
    if dir_year:
        info['year'] = dir_year.group(1)

        # Check for event type in filename
        if 'MAIN' in fn_upper and 'EVENT' in fn_upper:
            info['event_type'] = 'MAIN_EVENT'
        elif '_ME' in fn_upper or ' ME' in fn_upper or fn_upper.startswith('ME'):
            info['event_type'] = 'MAIN_EVENT'
        elif 'BRACELET' in fn_upper:
            info['event_type'] = 'BRACELET'
        elif 'HIGH' in fn_upper and 'ROLLER' in fn_upper:
            info['event_type'] = 'HIGH_ROLLER'

        # Extract episode from filename
        ep_m = re.search(r'(?:SHOW|EPISODE|EP)[_\s]*(\d+)', fn_upper)
        if ep_m:
            info['episode'] = int(ep_m.group(1))
        else:
            ep_m = re.search(r'ME\s*(\d+)', fn_upper)
            if ep_m:
                info['episode'] = int(ep_m.group(1))

        info['pattern_used'] = 'P10: Folder year + filename'
        return info

    # Fallback: Try year from filename
    m = re.search(r'(\d{4})', fn_upper)
    if m:
        year = int(m.group(1))
        if 1970 <= year <= 2030:
            info['year'] = str(year)
            info['pattern_used'] = 'FALLBACK: Year only'

    return info

# Test on all files
results = defaultdict(list)
for f in wsop_files:
    info = extract_info(f['filename'], f['directory'])
    pattern = info.get('pattern_used') or 'NO_PATTERN'
    results[pattern].append({**f, **info})

print()
print('PATTERN COVERAGE WITH NEW RULES:')
print('-' * 60)
total = 0
complete = 0
for pattern, items in sorted(results.items(), key=lambda x: -len(x[1])):
    cnt = len(items)
    total += cnt
    comp = sum(1 for i in items if i['year'] and i['event_type'] and i['episode'])
    complete += comp
    print(f'[{cnt:3d}] {pattern}')
    print(f'       Complete: {comp}/{cnt}')
    ex = items[0]
    yr = ex['year'] or '-'
    rg = ex['region'] or '-'
    et = ex['event_type'] or '-'
    ep = ex['episode'] or '-'
    print(f'       ex: {ex["filename"][:50]}')
    print(f'           -> {yr} | {rg} | {et} | Ep{ep}')
    print()

print('=' * 80)
print(f'TOTAL: {total} files')
print(f'COMPLETE (Year+Type+Episode): {complete} ({complete*100/total:.1f}%)')
print('=' * 80)
