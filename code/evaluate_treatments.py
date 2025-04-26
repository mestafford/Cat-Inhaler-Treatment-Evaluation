import re
import csv
import os
import pandas as pd
from collections import defaultdict

# --- 0. Setup of paths and expected columns ---

excel_path = 'data/raw/daily_puff_log.xlsx'
tsv_path   = 'data/processed/puff_data.tsv'
tsv_path2  = 'data/processed/puff_data_blocks.tsv'

# Columns to export from Excel to TSV
columns_to_export = [
    'date', 'treatment', 'inhaler', 'puff', 
    'seconds', 'double_puff', 
    'not_representative', 'sequence'
    # , 'behavior'
]

# --- 1. Read Excel y check columns ---

try:
    # Change the sheet name if necessary
    df = pd.read_excel(excel_path, sheet_name = 'Puffs') 
except FileNotFoundError:
    print(f"❌ The Excel file can't be found: {excel_path}")
    exit(1)
except Exception as e:
    print(f"❌ Error reading the Excel: {e}")
    exit(1)

# Verify that all necessary columns exist
missing = [c for c in columns_to_export if c not in df.columns]
if missing:
    print(f"❌ Missing columns in the Excel: {missing}")
    exit(1)

# --- 2. Save only the selected columns to TSV ---

df[columns_to_export].to_csv(tsv_path, sep = '\t', index = False)
print(f"✅ Excel converted to TSV with selected columns: {tsv_path}")

# --- 3. Function to simplify retreiving Boolean values ---

def is_true(value):
    return str(value).strip().lower() in ('1', 'true', 'yes')

# --- 4. Functions of parsing y scoring --------------------

def parse_breaths(sequence_str):
    '''
    Parses a sequence string like '1 - 2 - 0.5 - 3/4' and returns:
    - total: total breaths (sum of valid full breaths, dropping partials/zeros)
    - valid_breaths: list of valid breath counts (integers > 0)
    '''
    blocks = re.split(r'\s*-\s*', sequence_str)
    valid_breaths = []
    total = 0

    for b in blocks:
        # Fix breaths recorded as partial or uncertain
        num_str = b.split('/')[0].strip().replace(',', '.')
        try:
            n = int(float(num_str))
        except:
            n = 0
        # Only include full breaths
        if n > 0:
            valid_breaths.append(n)
            total += n

    return total, len(valid_breaths)

# Add this information to the TSV file

# Load the TSV file
df2 = pd.read_csv(tsv_path, sep = '\t')

df2[['breath_count', 'block_count']] = df2['sequence'].apply(
    lambda x: pd.Series(parse_breaths(x))
)

# Save the updated file
columns_to_export2 = [
    'date', 'treatment', 'inhaler', 'puff',
    'seconds', 'breath_count', 
    'double_puff', 'not_representative', 
    'block_count', 'sequence' # , 'behavior'
]

df2[columns_to_export2].to_csv(tsv_path2, sep = '\t', index = False)
print(f"✅ Added blocks column to TSV: {tsv_path2}\n")

# --- 5. Scoring functions ---------------------

'''Thresholds were defined using the 25th, 50th, and 75th percentiles of the puff data.
This includes data through 2025-04-23, excluding double puff data and data marked not-representative.
'''

def score_continuity(num_blocks, double_puff=False):
    if double_puff == True:
        if num_blocks <= 7: # Used value of 7 because the 25th percentile is 3.5
            return 3
        if num_blocks <= 8:
            return 2
        if num_blocks <= 12:
            return 1
        return 0
    else:
        if num_blocks <= 3: # Three blocks or less, perfect score.
            return 3
        if num_blocks <= 4: # Four blocks, score 2.
            return 2
        if num_blocks <= 6: # Five or six blocks, score 1.
            return 1
        return 0            # If more than six blocks, score 0.

def score_time(seconds, double_puff=False):
    if double_puff:
        if seconds <= 56: # Time for two puffs, within 56 seconds, perfect score.
            return 3
        if seconds <= 62: # Time for two puffs, 56 to 62 seconds, score 2.
            return 2
        if seconds <= 70: # Time for two puffs, 62 to 70 seconds, score 1.
            return 1
        return 0          # If more than 70 seconds, score 0.
    else:
        if seconds <= 28: # Time for one puff, within 28 seconds, perfect score.
            return 3
        if seconds <= 31: # Time for one puff, 28 to 31 seconds, score 2.
            return 2
        if seconds <= 35: # Time for one puff, 32 to 35 seconds, score 1.
            return 1
        return 0          # If more than 35 seconds, score 0.
    
# Optional behavior score (not used in the current version)
# Other necessary code to evaluate behavior is commented out.

# def score_behavior(v):
    return max(0, min(2, int(v)))

'''
Scoring parameters for traffic light colors were defined using the 33rd and 66th percentiles of the puff data.
This includes data through 2025-04-23, excluding double puff data and data marked not-representative.
'''
green_threshold = 4
yellow_threshold = 2

def score_puff(sequence, seconds, double_puff = False #, not_representative = False
               ): 
    # All data is included for scoring
    total, num_blocks = parse_breaths(sequence)
    c = score_continuity(num_blocks)
    t = score_time(seconds, double_puff)
    s = c + t
    col = (
        '\033[92mgreen\033[0m' if s >= green_threshold else
        '\033[93myellow\033[0m' if s >= yellow_threshold else
        '\033[91mred\033[0m'
    )
    return {
        'sequence': sequence,
        'seconds': seconds,
        #'behavior': b,
        'breath_count': total,
        'block_count': num_blocks,
        'continuity_score': c,
        'time_score': t,
        'score': s,
        'colors': col
    }

# --- 6. Read TSV with puff data -------------------------

def process_file(path):
    puffs = []
    with open(path, encoding = 'utf-8') as f:
        # Ignore lines beginning with # y empty lines
        lines = [l for l in f if l.strip() and not l.lstrip().startswith('#')]
        reader = csv.DictReader(lines, delimiter='\t')
        for idx, row in enumerate(reader):
            double_puff = is_true(row.get('double_puff'))
            not_representative = is_true(row.get('not_representative', False))  # Get 'not_representative' value
            
            try:
                seconds = int(row['seconds']) 
                # Seconds must be an integer or change to float
            except (ValueError, TypeError):
                print(f"⚠️  Invalid value for 'seconds' in row {idx+2}: {row['seconds']}. Assigning value 999.")
                seconds = 999

            # Pass the 'not_representative' value to the score_puff function
            puff_data = score_puff(
                row['sequence'],
                seconds,
                double_puff=double_puff
                #not_representative=not_representative
            )

            # Update the returned dictionary with other relevant information
            puff_data.update({
                'order': idx,
                'date': row['date'],
                'treatment': int(row['treatment']),
                'inhaler': row['inhaler'],
                'puff': int(row['puff']),
                'double_puff': double_puff,
                'not_representative': not_representative  # Add 'not_representative' here too
            })
            puffs.append(puff_data)
    return puffs

# --- 7. Group puffs into logical inhalers -----------

def group_inhalers(puffs):
    groups = defaultdict(list)
    for p in puffs:
        key = (p['date'], p['treatment'], p['inhaler'])
        groups[key].append(p)

    inhalers = []
    for key, items in groups.items():
        date, treat, inhal = key
        items_sorted = sorted(items, key = lambda x: x['order'])
        avg_score = sum(x['score'] for x in items_sorted) / len(items_sorted)
        col = (
            '\033[92mgreen\033[0m' if avg_score >= green_threshold else 
            '\033[93myellow\033[0m' if avg_score >= yellow_threshold else
            '\033[91mred\033[0m'
        )
        base = {
            'date': date,
            'treatment': treat,
            'inhaler': inhal,
            'avg_score_inh': avg_score,
            'colors_inhaler': col,
            'double_puff': any(x['double_puff'] for x in items_sorted)
        }
        for i, puff in enumerate(items_sorted, start=1):
            base[f'puff{i}_score'] = puff['score']
            base[f'puff{i}_colors'] = puff['colors']
        inhalers.append(base)
    inhalers_sorted = sorted(inhalers, key = lambda x: (x['date'], x['treatment'], x['inhaler']))
    return inhalers_sorted

# --- 8. Colors per treatment ---------------

def group_treatments(inhalers):
    # Group by treatment
    tdict = defaultdict(list)
    for inh in inhalers:
        tdict[(inh['date'], inh['treatment'])].append(inh)

    summary = []
    day_dict = defaultdict(list)

    for key in sorted(tdict.keys(), key = lambda x: (x[0], x[1])):
        items = tdict[key]
        date, treat = key

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
            'date': date,
            'treatment': treat,
            'num_inhalers': len(items),
            'avg_score_treat': round(avg_score_treat, 2),
            'double_puff_in_treatment': any(p.get('double_puff') for p in items),
            'colors_treatment': col_treat,
        })

        day_dict[date].extend(all_scores)

# --- 9. Colors per day ---------------------

    daily_summary = []
    for date, scores in day_dict.items():
        avg_day = sum(scores) / len(scores) if scores else 0
        col_day = (
            '\033[92mgreen\033[0m' if avg_day >= green_threshold else
            '\033[93myellow\033[0m' if avg_day >= yellow_threshold else
            '\033[91mred\033[0m'
        )
        daily_summary.append({
            'date': date,
            'avg_score_day': round(avg_day, 2),
            'colors_day': col_day
        })

    return summary, daily_summary

# --- 10. Export results to TSV ---------------------

# Choose columns to include and their order for the output of each TSV.

puff_columns = [
    'date', 'treatment', 'inhaler', 'puff',
    'score', 'colors', 'breath_count', 
    'seconds', 'block_count', #, 'behavior', 
    'time_score', 'continuity_score', 
    #'behavior_score', 
    'double_puff', 
    'not_representative', 'sequence'
]

inh_columns = [
    'date', 'treatment', 'inhaler', 'avg_score_inh',
    'colors_inhaler', 'double_puff'
]

treat_columns = [
    'date', 'treatment', 'num_inhalers',
    'avg_score_treat', 'colors_treatment', 
    'double_puff_in_treatment'
]

day_columns = [
    'date', 'avg_score_day', 'colors_day'
]

# Function to save both clean TSV and colored TSV

def save_both_versions(df, columns, base_filename):
    # Ensure target folder exists
    os.makedirs(os.path.dirname(base_filename), exist_ok=True)

    # Save colored TSV
    print("Columns to save:", columns)
    df_colored = df[[c for c in columns if c in df.columns]]
    df_colored.to_csv(base_filename + '_colored.tsv', sep = '\t', index = False)

    # Save clean TSV without ANSI
    ansi_escape = re.compile(r'\033\[\d+m')
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == object:
            df_clean[col] = df_clean[col].apply(lambda x: ansi_escape.sub('', x) if isinstance(x, str) else x)
    df_clean = df_clean[[c for c in columns if c in df_clean.columns]]
    df_clean.to_csv(base_filename + '.tsv', sep = '\t', index = False)

def export(in_tsv,
           out_puffs = 'results/puffs',
           out_inh   = 'results/inhalers',
           out_treat = 'results/treatments',
           out_day   = 'results/days'):

    # Process puffs
    puffs = process_file(in_tsv)
    puffs_sorted = sorted(puffs, key = lambda x: x['order'])

    # Export puffs
    df_puffs = pd.DataFrame(puffs_sorted)
    save_both_versions(df_puffs, puff_columns, out_puffs)

    # Group inhalers and export
    inh = group_inhalers(puffs_sorted)
    df_inh = pd.DataFrame(inh)
    save_both_versions(df_inh, inh_columns, out_inh)

    # Group treatments and export
    treat, dates = group_treatments(inh)
    df_treat = pd.DataFrame(treat)
    save_both_versions(df_treat, treat_columns, out_treat)

    # Export daily summary
    df_day = pd.DataFrame(dates)
    save_both_versions(df_day, day_columns, out_day)

    print(f"✅ Exported: {out_puffs}.tsv, {out_inh}.tsv, {out_treat}.tsv, {out_day}.tsv")
    print(f"✅ Exported: {out_puffs}_colored.tsv, {out_inh}_colored.tsv, "
          f"{out_treat}_colored.tsv, {out_day}_colored.tsv 🌈")

# --- 11. Input -------------------------------

if __name__ == '__main__':
    export(tsv_path2)
