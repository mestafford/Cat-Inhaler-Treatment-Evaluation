# Cat Inhaler Treatment Evaluation

This repository contains Python 3 code to evaluate the effectiveness of cat inhaler treatments using real-world data. It was developed collaboratively with the help of ChatGPT and adapted to the specific needs of my cat, but it's designed to be easily customized to suit your own use case.

The code analyzes treatment data and provides insights into the efficiency of each inhaler treatment. It generates two TSV files containing processed data from the original Excel file, and four TSV files (each with a colored and uncolored version) with evaluations at different levels: puff, inhaler, treatment, and day. These evaluations are presented in a traffic light format (green, yellow, or red) based on two main criteria:

1. **Continuity**: How continuously the cat breathes without removing its face from the inhaler.
2. **Time**: How many seconds it takes from pressing the inhaler to reaching the prescribed number of breaths.

An optional third criterion, **Behavior**, can be included to evaluate how well the cat tolerates the inhaler. However, in my experience, this was less effective due to its subjectivity. If used, it will increase the overall score, so you may need to modify the scoring system.

## Input Format

The script reads an Excel document where the user records data day by day. The following columns are required:

- `date`
- `treatment`
- `inhaler`
- `puff`
- `sequence`
- `seconds`
- `double_puff`
- `not_representative`

You can add additional columns (e.g., notes, changes) that the script will ignore.

Dates should be in the format `YYYY-MM-DD`.

Sequences of breaths should be written like this: `1 - 3 - 4 - 2`, where each number represents the number of breaths taken consecutively before the cat removed its face from the inhaler.

⚠️ Note:
The script expects to read data from an Excel sheet named **"Puffs"**. If your Excel file uses a different sheet name (like the default `Sheet1`), you can change the value of the `sheet_name` parameter in the script:

```python
# Change this if your sheet has a different name
df = pd.read_excel(excel_path, sheet_name = 'Puffs')
```

## Evaluation Criteria

Here's how the scores are assigned in the current version of the script:

### Continuity:
- **3 points**: No more than 3 blocks (groups of breaths) per puff.
- **2 points**: 4 blocks per puff.
- **1 point**: 5 or 6 blocks per puff.
- **0 points**: More than 6 blocks per puff.

### Time:
- **3 points**: 10 breaths completed in 28 seconds or less.
- **2 points**: 28 to 31 seconds.
- **1 point**: 32 to 35 seconds.
- **0 points**: Over 35 seconds.

For cases where two puffs are needed to reach 10 breaths (indicated by the `double_puff` column), the values are doubled.

### Optional Behavior Score:
This score is manually added by the user based on the cat's reaction during the treatment:

- **0 points**: Very agitated, doesn't allow inhaler placement.
- **1 point**: Agitated, but allows inhaler placement.
- **2 points**: Calm, allows inhaler placement.

### Final Scoring:
Puffs with scores of 4 to 6 points are marked as **green**, 2 to 4 points as **yellow**, and 0 to 1 points as **red**. The same scale is applied to inhalers, treatments, and days, averaging scores where applicable.

You can adjust the leniency by changing the thresholds for **green** and **yellow** scores, or by modifying the criteria for continuity or time.

My chosen cut-off values have been determined using my cat's data from the beginning of treatment through 2025-04-23, extracting the 25th, 50th and 75th percentiles for continuity and time data, and the 33rd and 66th for puff scores. I will be adding additional code shortly.

## Additional Features

- **Handling of uncertainties**: If a breath count is uncertain (e.g., `2/3` or `4.5`), the script will consider the lower number. This prevents miscounted data from skewing results.

The script also includes a helper script, `add_spaces_between_days.sh`, which can be used to add visual spacing between results when viewing them in the terminal. 
- **macOS users**: You may need to install `gawk` using Homebrew (`brew install gawk`).
- **Other systems**: The script should work with `awk` instead of `gawk` (just replace `gawk` with `awk` in the script if needed).

## Limitations

- **Treatment regimen**: This script is designed for a cat receiving two daily treatments that include one puff of Ventolin and two puffs of Flixotide. The medication is administered through an Aerokat chamber, which guarantees it is available during 30 seconds. The code will still work for other regimens, as long as breaths can be counted.
- **Three-puff treatments**: This script doesn’t support cases where three puffs are required to reach the prescribed number of breaths.
- **Exceeding prescribed breaths**: If your cat exceeds the prescribed breaths (i.e., over 10), the extra breaths may decrease the scores for time and continuity. In such cases, it's best to adjust the time and groupings manually.

## Recommendations

Clear and consistent recording is essential for reliable results. Decide on your system for recording breath groups and times before starting, and stick with it. Using a camera during treatments is also highly recommended to ensure accuracy.

## Directory Structure

Here’s a breakdown of the main files and folders in the repository:

```treatment_evaluation/
├── code/
│   ├── evaluate_treatments.py      # Main script
│   └── format_with_spacing.sh      # Optional helper script for readability
├── data/
│   ├── raw/
│   │   └── daily_puff_log.xlsx     # 🔒 Ignored — not in repo
│   └── processed/
│       ├── puff_data.tsv           # Extracted and cleaned version of the Excel data
│       └── puff_data_blocks.tsv    # Data with block counts added       
├── results/
│   ├── days.tsv
│   ├── inhalers.tsv
│   ├── puffs.tsv
│   └── treatments.tsv
├── README.md
├── LICENSE.md
├── package_requirements.txt
├── .gitignore
```

## Usage

To run the script, execute the following command from the main directory:

```bash
python3 code/evaluate_treatments.py
```
