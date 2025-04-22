import re
import csv
import os
import openpyxl
import pandas as pd
from collections import defaultdict

# --- 0. Setup of paths and expected columns ---

excel_path = "data/raw/daily_puff_log.xlsx"
tsv_path   = "data/processed/puff_data.tsv"

# All necessary columns in Excel for analysis
expected_columns = [
    "day", "treatment", "inhaler", "puff",
    "sequence", "seconds", "combine_puffs"
    # , "behavior"
]

# Columns to export from Excel to TSV
columns_to_export = [
    "day", "treatment", "inhaler", "puff", 
    "combine_puffs", "seconds", "sequence"
]

# --- 1. Read Excel y check columns ---

try:
    # Change the sheet name if necessary
    df = pd.read_excel(excel_path, sheet_name="Puffs") 
except FileNotFoundError:
    print(f"❌ The Excel file can't be found: {excel_path}")
    exit(1)
except Exception as e:
    print(f"❌ Error reading the Excel: {e}")
    exit(1)

# Verify that all necessary columns exist
missing = [c for c in expected_columns if c not in df.columns]
if missing:
    print(f"❌ Missing columns in the Excel: {missing}")
    exit(1)

# Verify that the columns to be exported exist
missing_export = [c for c in columns_to_export if c not in df.columns]
if missing_export:
    print(f"❌ Missing columns to be exported: {missing_export}")
    exit(1)

# --- 2. Save only the selected columns to TSV ---

df[columns_to_export].to_csv(tsv_path, sep="\t", index=False)
print(f"✅ Excel converted to TSV with selected columns: {tsv_path}\n")

# --- 2. Functions of parsing y scoring --------------------

def parse_breaths(sequence):
    blocks = re.split(r'\s*-\s*', sequence)
    total = 0
    continuity = []
    for b in blocks:
        comment = '(' in b and ')' in b
        num_str = re.sub(r'\(.*?\)', '', b).split('/')[0].strip().replace(',', '.')
        try:
            n = int(float(num_str))  # Removes decimal from 2,5 or 2.0
        except:
                n = 0
        total += n
        
        # For continuity: only blocks without comments and with at least 2 breaths
        if not comment and n >= 2:
            continuity.append(n)
    return total, continuity

def score_continuity(groups, total):
    if total == 0:
        return 0
    ratio = sum(groups) / total
    if ratio >= 0.8: # If 80% of the breaths are in groups of 2 or more, perfect score.
        return 3
    if ratio >= 0.6: # If 60% of the breaths are in groups of 2 or more, score 2.
        return 2
    if ratio >= 0.4: # If 40% of the breaths are in groups of 2 or more, score 1.
        return 1
    return 0

def score_time(seconds, combine_puffs=False):
    if combine_puffs:
        if seconds <= 68: # Time for two puffs, within 68 seconds, perfect score.
            return 3
        if seconds <= 72: # Time for two puffs, within 69 to 72 seconds, score 2.
            return 2
        if seconds <= 80: # Time for two puffs, within 73 to 80 seconds, score 1.
            return 1
        return 0          # If more than 80 seconds, score 0.
    else:
        if seconds <= 34: # Time for one puff, within 34 seconds, perfect score.
            return 3
        if seconds <= 36: # Time for one puff, within 35 or 36 seconds, score 2.
            return 2
        if seconds <= 40: # Time for one puff, within 37 to 40 seconds, score 1.
            return 1
        return 0          # If more than 40 seconds, score 0.

# Optional behavior score (not used in the current version)
# Other necessary code to evaluate behavior is commented out.

# def score_behavior(v):
    return max(0, min(2, int(v)))

# Scoring parameters for traffic light colors
green_threshold = 5
yellow_threshold = 3

def score_puff(sequence, seconds, combine_puffs=False): 
    total, groups = parse_breaths(sequence)
    c = score_continuity(groups, total)
    t = score_time(seconds, combine_puffs)
    # b = score_behavior(behavior)
    # s = c + t + b
    s = c + t
    col = (
        "\033[92mgreen\033[0m" if s >= green_threshold else
        "\033[93myellow\033[0m" if s >= yellow_threshold else
        "\033[91mred\033[0m"
    )
    return {
        'sequence': sequence,
        'seconds': seconds,
        #'behavior': b,
        'total': total,
        'continuity': c,
        'time': t,
        'score': s,
        'colors': col
    }

# --- 3. Read TSV with puff data -------------------------

def process_file(path):
    puffs = []
    with open(path, encoding='utf-8') as f:
        # Ignore lines beginning with # y empty lines
        lines = [l for l in f if l.strip() and not l.lstrip().startswith('#')]
        reader = csv.DictReader(lines, delimiter='\t')
        for idx, row in enumerate(reader):
            combine = str(row.get('combine_puffs','')).lower() in ('1','true','yes')
            try:
                seconds = int(row['seconds'])
            except (ValueError, TypeError):
                print(f"⚠️  Invalid value for 'seconds' in row {idx+2}: {row['seconds']}. Assigning value 999.")
                seconds = 999
            puff_data = score_puff(
                row['sequence'],
                seconds,
                #row['behavior'],
                combine_puffs=combine
            )
            puff_data.update({
                'order': idx,
                'day': row['day'],
                'treatment': int(row['treatment']),
                'inhaler': row['inhaler'],
                'puff_id': int(row['puff']),
                'combine_puffs': combine
            })
            puffs.append(puff_data)
    return puffs

# --- 4. Group puffs into logical inhalers -----------

def group_inhalers(puffs):
    groups = defaultdict(list)
    for p in puffs:
        key = (p['day'], p['treatment'], p['inhaler'])
        groups[key].append(p)

    inhalers = []
    for key, items in groups.items():
        day, treat, inhal = key
        items_sorted = sorted(items, key=lambda x: x['order'])
        avg_score = sum(x['score'] for x in items_sorted) / len(items_sorted)
        col = (
            "\033[92mgreen\033[0m" if avg_score >= green_threshold else 
            "\033[93myellow\033[0m" if avg_score >= yellow_threshold else
            "\033[91mred\033[0m"
        )
        base = {
            'day': day,
            'treatment': treat,
            'inhaler': inhal,
            'avg_score_inh': avg_score,
            'colors_inhaler': col,
            'combine_puffs': any(x['combine_puffs'] for x in items_sorted)
        }
        for i, puff in enumerate(items_sorted, start=1):
            base[f'puff{i}_score'] = puff['score']
            base[f'puff{i}_colors'] = puff['colors']
        inhalers.append(base)
    inhalers_sorted = sorted(inhalers, key=lambda x: (x['day'], x['treatment'], x['inhaler']))
    return inhalers_sorted

# --- 5. Colors per treatment ---------------

def group_treatments(inhalers):
    # Group by treatment
    tdict = defaultdict(list)
    for inh in inhalers:
        tdict[(inh['day'], inh['treatment'])].append(inh)

    summary = []
    day_dict = defaultdict(list)

    for key in sorted(tdict.keys(), key=lambda x: (x[0], x[1])):
        items = tdict[key]
        day, treat = key

        # Collect all the puff scores
        all_scores = []
        for p in items:
            for i in range(1, 5):
                if f'puff{i}_score' in p:
                    all_scores.append(p[f'puff{i}_score'])

        avg_score_treat = sum(all_scores) / len(all_scores) if all_scores else 0

        col_treat = (
            '\033[92mgreen\033[0m' if avg_score_treat >= green_threshold else
            '\033[93myellow\033[0m' if avg_score_treat >= yellow_threshold else
            '\033[91mred\033[0m'
        )

        summary.append({
            'day': day,
            'treatment': treat,
            'inhalers_registrados': len(items),
            'avg_score_treat': round(avg_score_treat, 2),
            'combine_puffs_in_treatment': any(p.get('combine_puffs') for p in items),
            'colors_treatment': col_treat,
        })

        day_dict[day].extend(all_scores)

# --- 6. Colors per day ---------------------

    daily_summary = []
    for day, scores in day_dict.items():
        avg_day = sum(scores) / len(scores) if scores else 0
        col_day = (
            '\033[92mgreen\033[0m' if avg_day >= green_threshold else
            '\033[93myellow\033[0m' if avg_day >= yellow_threshold else
            '\033[91mred\033[0m'
        )
        daily_summary.append({
            'day': day,
            'avg_score_day': round(avg_day, 2),
            'colors_day': col_day
        })

    return summary, daily_summary

# --- 7. Export results to TSV ---------------------

# Choose columns to include and their order for the output of each tsv.

puff_columns = [
    'day', 'treatment', 'inhaler', 'puff_id',
    'score', 'colors', 'breaths', 'seconds', 
    'continuity', 'time', #'behavior', 
    'combine_puffs', 'sequence'
]

inh_columns = [
    'day', 'treatment', 'inhaler', 'avg_score_inh',
    'colors_inhaler', 'combine_puffs'
]

treat_columns = [
    'day', 'treatment', 'inhalers_registrados',
    'avg_score_treat', 'colors_treatment', 
    'combine_puffs_in_treatment'
]

day_columns = [
    'day', 'avg_score_day', 'colors_day'
]

# Function to save both clean TSV and colorized TSV

def save_both_versions(df, columns, base_filename):
    # Ensure target folder exists
    os.makedirs(os.path.dirname(base_filename), exist_ok=True)

    # Save colorized TSV
    df_colored = df[[c for c in columns if c in df.columns]]
    df_colored.to_csv(base_filename + '_colored.tsv', sep='\t', index=False)

    # Save clean TSV without ANSI
    ansi_escape = re.compile(r'\033\[\d+m')
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == object:
            df_clean[col] = df_clean[col].apply(lambda x: ansi_escape.sub('', x) if isinstance(x, str) else x)
    df_clean = df_clean[[c for c in columns if c in df_clean.columns]]
    df_clean.to_csv(base_filename + '.tsv', sep='\t', index=False)

def export(in_tsv,
            out_puffs='results/puffs',
            out_inh='results/inhalers',
            out_treat='results/treatments',
            out_day='results/days'):

    # Process puffs
    puffs = process_file(in_tsv)
    puffs_sorted = sorted(puffs, key=lambda x: x['order'])

    # Export puffs
    df_puffs = pd.DataFrame(puffs_sorted)
    save_both_versions(df_puffs, puff_columns, out_puffs)

    # Group inhalers and export
    inh = group_inhalers(puffs_sorted)
    df_inh = pd.DataFrame(inh)
    save_both_versions(df_inh, inh_columns, out_inh)

    # Group treatments and export
    treat, days = group_treatments(inh)
    df_treat = pd.DataFrame(treat)
    save_both_versions(df_treat, treat_columns, out_treat)

    # Export daily summary
    df_day = pd.DataFrame(days)
    save_both_versions(df_day, day_columns, out_day)

    print(f"✅ Exported: {out_puffs}.tsv, {out_inh}.tsv, {out_treat}.tsv, {out_day}.tsv")
    print(f"✅ Exported: {out_puffs}_colored.tsv, {out_inh}_colored.tsv, "
          f"{out_treat}_colored.tsv, {out_day}_colored.tsv 🌈")

# --- 7. Input -------------------------------

if __name__ == "__main__":
    export(tsv_path)