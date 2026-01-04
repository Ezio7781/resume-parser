import re
import os
import sys
import json
from typing import List, Dict, Optional
import argparse
import logging
import pandas as pd

from llm_helper import call_llm_extract
import concurrent.futures
from functools import partial
import math

import docx2txt

# Degree ranking used to pick the highest qualification when multiple are present
DEGREE_RANK = {
    'phd': 6,
    'doctor': 6,
    'dphil': 6,
    'master': 5,
    'ms': 5,
    'm.s.': 5,
    'mba': 5,
    'm.sc': 5,
    'bachelor': 4,
    'bsc': 4,
    'bs': 4,
    'b.s.': 4,
    'associate': 3,
    'diploma': 2,
    'high school': 1
}


# Standard output fields
FIELD_NAMES = [
    'full_name',
    'email',
    'phone_number',
    'alternate_phone_number',
    'highest_qualification',
    'years_of_experience',
    'current_company',
    'current_designation',
    'city',
    'state'
]


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def find_emails(text: str) -> List[str]:
    if not text:
        return []
    emails = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    # normalize and dedupe
    seen = set()
    out = []
    for e in emails:
        ne = e.strip().lower()
        if ne not in seen:
            seen.add(ne)
            out.append(ne)
    return out


def normalize_phone(s: str) -> Optional[str]:
    if not s:
        return None
    digits = re.sub(r'\D', '', s)
    
    if len(digits) < 7:
        return None
    # prefer E.164-like: if 10 digits assume US and prefix +1
    if len(digits) == 10:
        return '+1' + digits
    if len(digits) > 10 and digits.startswith('0') is False:
        return '+' + digits
    return digits


def find_phone_numbers(text: str) -> List[str]:
    if not text:
        return []
    # common phone patterns including country code and separators
    raw = re.findall(r'(?:\+?\d[\d\s\-().]{6,}\d)', text)
    norm = []
    seen = set()
    for r in raw:
        p = normalize_phone(r)
        if p and p not in seen:
            seen.add(p)
            norm.append(p)
    return norm


def extract_text(path: str) -> str:
    try:
        lower = path.lower()
        if lower.endswith('.txt'):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        if lower.endswith('.pdf'):
            try:
                import PyPDF2
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = [p.extract_text() or '' for p in reader.pages]
                    return '\n'.join(pages)
            except Exception:
                with open(path, 'rb') as f:
                    return f.read().decode('utf-8', errors='ignore')
        if lower.endswith(('.doc', '.docx')):
            try:
                return docx2txt.process(path)
            except Exception:
                with open(path, 'rb') as f:
                    return f.read().decode('utf-8', errors='ignore')
        # fallback: try read as text
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')
    except Exception:
        return ''


def find_degrees(text: str) -> List[str]:
    found = []
    lower = text.lower()
    for key in DEGREE_RANK.keys():
        if key in lower:
            m = re.search(r'([A-Za-z0-9 .,\-]{0,40}' + re.escape(key) + r'[A-Za-z0-9 .,%\-]{0,40})', text, flags=re.I)
            if m:
                found.append(m.group(0).strip())
            else:
                found.append(key)
    return found


def find_section(text: str, headers: List[str], window: int = 1000) -> Optional[str]:
    lower = text.lower()
    for h in headers:
        p = lower.find(h)
        if p != -1:
            return text[p:p+window]
    return None


def find_highest_degree_in_education(text: str) -> Optional[str]:
    edu = find_section(text, ['education', 'academic qualifications', 'qualifications'])
    if not edu:
        return None
    degrees = find_degrees(edu)
    if not degrees:
        return None
    best = None
    best_rank = 0
    for d in degrees:
        for key, rank in DEGREE_RANK.items():
            if key in d.lower():
                if rank > best_rank:
                    best_rank = rank
                    best = d
    return best


def find_years_of_experience(text: str) -> Optional[float]:
    # look for patterns like 'X years' or 'X years of experience' or 'X yrs'
    # Prefer ones near keywords like 'experience' or 'years of experience' in summary/header
    patterns = [r'([0-9]+(?:\.[0-9]+)?)\s*(?:\+)?\s*(?:years|yrs|year)\b']
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            try:
                val = float(m.group(1)) if '.' in m.group(1) else int(m.group(1))
            except Exception:
                continue
            # check surrounding context for 'experience' or pros/summary
            ctx = text[max(0, m.start()-60):m.end()+60].lower()
            if 'experience' in ctx or 'years of experience' in ctx or 'yrs' in ctx:
                return val
    # fallback: take the first numeric years mention if reasonable
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:\+)?\s*(?:years|yrs|year)\b', text, flags=re.I)
    if m:
        try:
            return float(m.group(1)) if '.' in m.group(1) else int(m.group(1))
        except Exception:
            return None
    return None


def find_location(text: str) -> tuple[Optional[str], Optional[str]]:
    # look for lines like City, State but avoid matching experience lines
    reject_keywords = set(['experience', 'present', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                           'at', 'company', 'corp', 'inc', 'llc', 'manager', 'engineer', 'senior', 'junior', 'associate'])

    def looks_like_location(part: str) -> bool:
        if not part:
            return False
        if re.search(r'\d', part):
            return False
        if len(part.split()) > 4:
            return False
        if re.search(r'[^A-Za-z .\-]', part):
            return False
        return True

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        # check explicit labels
        m = re.search(r'location\s*[:\-]\s*(.+)', line, flags=re.I)
        if m:
            loc = m.group(1).strip()
            parts = [p.strip() for p in loc.split(',')]
            if len(parts) >= 2 and looks_like_location(parts[0]) and looks_like_location(parts[1]):
                return parts[0], parts[1]
        if ',' in line:
            if any(kw in lower for kw in reject_keywords):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                city = parts[0]
                state = parts[1]
                if looks_like_location(city) and looks_like_location(state):
                    return city, state
    return None, None


def find_name(text: str) -> Optional[str]:
    # Improved heuristics:
    # 1) Look for explicit 'Name:' label
    m = re.search(r'\bName\s*[:\-]\s*(.+)', text, flags=re.I)
    if m:
        candidate = m.group(1).strip().split('\n')[0].strip()
        if len(candidate.split()) >= 2:
            return candidate

    # 2) Top lines: skip common headings and contact lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    skip_tokens = ['resume', 'curriculum vitae', 'cv', 'contact', 'summary']
    for line in lines[:6]:
        lower = line.lower()
        if any(tok in lower for tok in skip_tokens):
            continue
        if re.search(r'@', line) or re.search(r'\d', line):
            continue
        # require at least two words that look like names
        parts = [p for p in line.split() if re.match(r"^[A-Za-z.'-]+$", p)]
        if len(parts) >= 2 and all(p[0].isupper() for p in parts[:2]):
            return line

    # 3) fallback: scan first 12 lines for a name-like line
    for line in lines[:12]:
        if len(line.split()) >= 2 and re.match(r'^[A-Za-z .\-]+$', line) and not re.search(r'@|\d', line):
            return line
    return None


def parse_text(text: str) -> Dict[str, Optional[object]]:
    out = {k: None for k in FIELD_NAMES}
    # confidences and strict extraction rules
    CONF_THRESHOLD = 0.8

    # email (high confidence if matched)
    emails = find_emails(text)
    email_conf = 1.0 if emails else 0.0
    out['email'] = emails[0] if emails and email_conf >= CONF_THRESHOLD else None

    # phones: normalized digits only. require length >=10 for high confidence
    phones = find_phone_numbers(text)
    primary_phone = None
    alt_phone = None
    if phones:
        if len(phones[0]) >= 10:
            primary_phone = phones[0]
            primary_conf = 1.0
        else:
            primary_conf = 0.0
        if len(phones) > 1 and len(phones[1]) >= 10:
            alt_phone = phones[1]
            alt_conf = 1.0
        else:
            alt_conf = 0.0
    else:
        primary_conf = 0.0
        alt_conf = 0.0
    out['phone_number'] = primary_phone if primary_conf >= CONF_THRESHOLD else None
    out['alternate_phone_number'] = alt_phone if alt_conf >= CONF_THRESHOLD else None

    # name: require top line, at least two words, no digits, not an email
    name = find_name(text)
    name_conf = 0.0
    if name:
        # require at least one capitalized word and not all-lower
        if any(w[0].isupper() for w in name.split() if w):
            name_conf = 0.9
    out['full_name'] = name if name_conf >= CONF_THRESHOLD else None

    # highest qualification: only from Education section
    highest_degree = find_highest_degree_in_education(text)
    degree_conf = 0.0
    if highest_degree:
        degree_conf = 0.95
    out['highest_qualification'] = highest_degree if degree_conf >= CONF_THRESHOLD else None

    # years of experience: numeric only, require nearby keyword 'experience' or in summary
    yoe_raw = None
    yoe_conf = 0.0
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:\+)?\s*(?:years|yrs|year)\b', text, flags=re.I)
    if m:
        yoe_raw = m.group(1)
        # check context
        ctx = text[max(0, m.start()-40):m.end()+40].lower()
        if 'experience' in ctx or 'yrs' in ctx or 'years' in ctx or 'experience' in text[:200].lower():
            try:
                yval = float(yoe_raw) if '.' in yoe_raw else int(yoe_raw)
                yoe_conf = 0.9
                out['years_of_experience'] = yval if yoe_conf >= CONF_THRESHOLD else None
            except Exception:
                out['years_of_experience'] = None
        else:
            out['years_of_experience'] = None
    else:
        out['years_of_experience'] = None

    # current company and designation: strict extraction from Experience section only
    # current company and designation: try to find the most recent role from Experience section
    exp = find_section(text, ['experience', 'work experience', 'employment', 'professional experience', 'roles'])
    cur_comp = None
    cur_desig = None
    comp_conf = 0.0
    if exp:
        # split into candidate lines and look for date ranges; prefer entries with 'present' or latest end year
        lines = [l.strip() for l in exp.splitlines() if l.strip()]
        # collect tuples (line, end_year, has_present)
        entries = []
        for line in lines:
            # find year ranges like 'Jan 2020 - Present' or '2019 - 2022'
            m = re.search(r'([0-9]{4})\s*[-–]\s*(Present|present|[0-9]{4})', line)
            end_year = None
            has_present = False
            if m:
                if m.group(2).lower() == 'present':
                    has_present = True
                else:
                    try:
                        end_year = int(m.group(2))
                    except Exception:
                        end_year = None
            entries.append((line, end_year, has_present))

        # prefer first entry with present, else highest end_year, else first non-empty
        chosen_line = None
        for ln, ey, pres in entries:
            if pres:
                chosen_line = ln
                break
        if not chosen_line and entries:
            # sort by end_year desc
            sorted_entries = sorted(entries, key=lambda x: (x[1] or 0), reverse=True)
            chosen_line = sorted_entries[0][0]

        if chosen_line:
            candidate = chosen_line
            # patterns: 'Designation at Company' or 'Company — Designation' or 'Designation, Company' or 'Company | Designation'
            if re.search(r'\bat\b', candidate, flags=re.I):
                parts = re.split(r'\s+at\s+', candidate, flags=re.I)
                cur_desig = parts[0].strip()
                cur_comp = parts[1].strip() if len(parts) > 1 else None
            elif '—' in candidate or '–' in candidate or '|' in candidate:
                parts = re.split(r'[—–|]', candidate)
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) >= 2:
                    # choose plausible company/designation by capitalization
                    if parts[0].istitle() or re.search(r'\b(Inc|Corp|LLC|Ltd|Co|Company|Technologies)\b', parts[0], flags=re.I):
                        cur_comp = parts[0]
                        cur_desig = parts[1]
                    else:
                        cur_desig = parts[0]
                        cur_comp = parts[1]
            elif ',' in candidate:
                parts = [p.strip() for p in candidate.split(',')]
                if len(parts) >= 2:
                    # decide which is company vs title by presence of company tokens
                    if re.search(r'\b(Inc|Corp|LLC|Ltd|Co|Company|Technologies|Solutions)\b', parts[1], flags=re.I):
                        cur_desig = parts[0]
                        cur_comp = parts[1]
                    else:
                        cur_desig = parts[0]
                        cur_comp = parts[1]
            else:
                # last-resort: try to split on dash or slash
                parts = re.split(r'[-/]', candidate)
                if len(parts) >= 2:
                    cur_desig = parts[0].strip()
                    cur_comp = parts[-1].strip()

            # validate company: must be capitalized or contain company token
            if cur_comp and (re.search(r'\b(inc|corp|llc|ltd|company|co|corporation|solutions|technologies)\b', cur_comp, flags=re.I) or re.search(r'[A-Z]', cur_comp)):
                comp_conf = 0.9
            else:
                # allow moderate confidence for plausible short names
                if cur_comp and len(cur_comp) < 40:
                    comp_conf = 0.75
                else:
                    comp_conf = 0.0
    out['current_company'] = cur_comp if comp_conf >= CONF_THRESHOLD else None
    out['current_designation'] = cur_desig if comp_conf >= CONF_THRESHOLD else None

    # location
    city, state = find_location(text)
    loc_conf = 0.9 if city and state else 0.0
    out['city'] = city if loc_conf >= CONF_THRESHOLD else None
    out['state'] = state if loc_conf >= CONF_THRESHOLD else None

    return out


def process_directory(input_dir: str) -> List[Dict[str, Optional[object]]]:
    # Build file list and respect optional limit
    all_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir)
                 if os.path.isfile(os.path.join(input_dir, f))]
    limit = os.getenv('PARSE_LIMIT')
    try:
        if limit:
            limit_i = int(limit)
            all_files = all_files[:limit_i]
    except Exception:
        pass

    # concurrency (env or default)
    workers = int(os.getenv('PARSE_CONCURRENCY', os.getenv('PARSE_WORKERS', '4')))

    logging.info(f'Parsing %d files with %d workers', len(all_files), workers)

    def _process_single(fpath: str) -> Dict[str, Optional[object]]:
        try:
            text = extract_text(fpath)
            local_parsed = parse_text(text)

            use_llm = os.getenv('USE_LLM', '0') == '1'
            llm_res = None
            if use_llm and os.getenv('GROK_API_KEY') and call_llm_extract is not None:
                try:
                    llm_out = call_llm_extract(
                        text,
                        api_key=os.getenv('GROK_API_KEY'),
                        api_url=os.getenv('GROK_API_URL'),
                        model=os.getenv('GROK_MODEL', 'gpt-4o-mini'),
                        mode=os.getenv('USE_LLM_MODE', 'human')
                    )
                    if isinstance(llm_out, list) and len(llm_out) > 0:
                        llm_res = llm_out[0]
                except Exception:
                    llm_res = None

            CONF_THRESHOLD = 0.8

            def normalize_value(field: str, val):
                if val is None:
                    return None
                if field in ['phone_number', 'alternate_phone_number']:
                    return normalize_phone(str(val))
                if field == 'email':
                    m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', str(val))
                    return m.group(0).lower() if m else None
                if field == 'years_of_experience':
                    try:
                        if isinstance(val, (int, float)):
                            return val
                        s = str(val).strip()
                        if re.match(r'^\d+(?:\.\d+)?$', s):
                            return float(s) if '.' in s else int(s)
                        return None
                    except Exception:
                        return None
                v = str(val).strip()
                return v if v != '' else None

            final = {k: None for k in FIELD_NAMES}
            if llm_res and isinstance(llm_res, dict):
                for field in FIELD_NAMES:
                    llm_field = llm_res.get(field)
                    chosen = None
                    if llm_field is None:
                        chosen = None
                    elif isinstance(llm_field, dict):
                        conf = float(llm_field.get('confidence', 0) or 0)
                        val = llm_field.get('value')
                        if conf >= CONF_THRESHOLD:
                            chosen = normalize_value(field, val)
                    else:
                        chosen = normalize_value(field, llm_field)

                    final[field] = chosen if chosen is not None else local_parsed.get(field)
            else:
                final = local_parsed

            # optional second-pass LLM
            null_count = sum(1 for v in final.values() if v is None)
            if null_count >= 4 and call_llm_extract is not None:
                try:
                    second = call_llm_extract(text, mode=os.getenv('USE_LLM_MODE', 'human'))
                    if isinstance(second, list) and len(second) > 0:
                        llm_second = second[0]
                        for field in FIELD_NAMES:
                            fld = llm_second.get(field)
                            if isinstance(fld, dict):
                                conf = float(fld.get('confidence', 0) or 0)
                                val = fld.get('value')
                                if conf >= CONF_THRESHOLD and val is not None:
                                    final[field] = normalize_value(field, val)
                except Exception:
                    pass

            return final
        except Exception as e:
            logging.exception('Error parsing file %s', fpath)
            return {k: None for k in FIELD_NAMES}

    results: List[Dict[str, Optional[object]]] = []
    if not all_files:
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as exe:
        futures = {exe.submit(_process_single, fp): fp for fp in all_files}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    return results


def save_outputs(data: List[Dict[str, Optional[object]]], json_path: str, excel_path: str):
    with open(json_path, 'w', encoding='utf-8') as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)
    # create dataframe with exact columns
    df = pd.DataFrame(data, columns=FIELD_NAMES)
    df.to_excel(excel_path, index=False)


def main():
    parser = argparse.ArgumentParser(prog='resume_parser', description='Parse resumes in a directory and export JSON/XLSX')
    parser.add_argument('--concurrency', type=int, help='Number of worker threads for parsing')
    parser.add_argument('--limit', type=int, help='Limit number of files to parse')
    parser.add_argument('--use-llm', action='store_true', help='Enable LLM-assisted extraction (reads GROK_API_KEY or session)')
    parser.add_argument('input_dir', nargs='?', help='Directory containing resumes')
    parser.add_argument('excel_out', nargs='?', default='resumes_output.xlsx', help='Excel output path')
    parser.add_argument('json_out', nargs='?', default='resumes_output.json', help='JSON output path')
    args = parser.parse_args()

    if not args.input_dir:
        parser.print_help()
        sys.exit(1)

    # wire CLI flags into environment variables used by process_directory
    if args.concurrency:
        os.environ['PARSE_CONCURRENCY'] = str(args.concurrency)
    if args.limit:
        os.environ['PARSE_LIMIT'] = str(args.limit)
    if args.use_llm:
        os.environ['USE_LLM'] = '1'

    data = process_directory(args.input_dir)
    save_outputs(data, args.json_out, args.excel_out)
    print(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
