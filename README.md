# Cat Inhaler Treatment Evaluation

This repository contains Python 3 code to evaluate the effectiveness of cat inhaler treatments using real-world data. It was developed collaboratively with the help of ChatGPT and adapted to the specific needs of my cat, but it's designed to be easily customized to suit your own use case.

The code analyzes treatment data and provides insights into the efficiency of each inhaler treatment. It generates one TSV file with the information from the original Excel file, and four TSV files with evaluations at different levels: puff, inhaler, treatment, and day. These evaluations are presented in a traffic light format (green, yellow, or red) based on two main criteria:

1. **Continuity**: How many breaths the cat takes before removing its face from the inhaler.
2. **Time**: How many seconds it takes from pressing the inhaler to reaching the prescribed number of breaths (10 breaths by default, but this can be adjusted).

An optional third criterion, **Behavior**, can be included to evaluate how well the cat tolerates the inhaler. However, in my experience, this was less effective due to its subjectivity. If used, it will increase the overall score, so you may need to modify the scoring system.

## Input Format

The script reads an Excel document where the user records data day by day. The following columns are required:

- `date`
- `treatment`
- `inhaler`
- `sequence`
- `seconds`
- `double_puff`

You can add additional columns (e.g., notes) that the script will ignore. Sequences of breaths should be written like this: `1 - 3 - 4 - 2`, where each number represents the number of breaths taken consecutively before the cat removed its face from the inhaler.

⚠️ Note:
The script expects to read data from an Excel sheet named **"Puffs"**. If your Excel file uses a different sheet name (like the default `Sheet1`), you can change the value of the `sheet_name` parameter in the script:

```python
# Change this if your sheet has a different name
df = pd.read_excel(excel_path, sheet_name="Puffs")
```

## Evaluation Criteria

The current scoring system is designed to balance leniency and strictness. Here's how the scores are assigned:

### Continuity:
- **3 points**: At least 8 out of 10 breaths taken in groups of 2 or more breaths.
- **2 points**: 5 or 6 breaths taken in groups of 2 or more.
- **1 point**: 3 or fewer breaths in groups of 2 or more.

### Time:
- **3 points**: 10 breaths completed in 34 seconds or less.
- **2 points**: 35–36 seconds.
- **1 point**: 37–40 seconds.
- **0 points**: Over 40 seconds.

For cases where two puffs are needed to reach 10 breaths (indicated by the `double_puff` column), the times are doubled.

### Optional Behavior Score:
This score is manually added by the user based on the cat's reaction during the treatment:

- **0 points**: Very agitated, doesn't allow inhaler placement.
- **1 point**: Agitated, but allows inhaler placement.
- **2 points**: Calm, allows inhaler placement.

### Final Scoring:
Puffs with scores of 5 or 6 points are marked as **green**, 3 or 4 points as **yellow**, and 0, 1, or 2 points as **red**. The same scale is applied to inhalers, treatments, and days, averaging scores where applicable.

You can adjust the leniency by changing the thresholds for **green** and **yellow** scores, or by modifying the criteria for continuity, time, or breath groupings.

## Additional Features

- **Handling of uncertainties**: If a breath count is uncertain (e.g., `2/3`), the script will consider the lower number. This prevents miscounted data from skewing results.
- **Handling of movement**: Sequences marked with movement (e.g., `1 - 2 - 3 (with movement)`) will be excluded from analysis, as these data points are less reliable.

The script also includes a helper script, `add_spaces_between_days.sh`, which can be used to add visual spacing between results when viewing them in the terminal. 
- **macOS users**: You may need to install `gawk` using Homebrew (`brew install gawk`).
- **Other systems**: The script should work with `awk` instead of `gawk` (just replace `gawk` with `awk` in the script if needed).

## Limitations

- **Treatment regimen**: This script is designed for a cat receiving two daily treatments: one puff of Ventolin and two puffs of Flixotide. The code will still work for other regimens, as long as breaths can be counted.
- **Three-puff treatments**: This script doesn’t support cases where three puffs are required to reach the prescribed number of breaths.
- **Exceeding prescribed breaths**: If your cat exceeds the prescribed breaths (i.e., over 10), the extra breaths may decrease the scores for time and continuity. In such cases, it's best to adjust the time and groupings manually.

## Recommendations

Clear and consistent recording is essential for reliable results. Decide on your system for recording breath groups and times before starting, and stick with it. Using a camera during treatments is also highly recommended to ensure accuracy.

## Directory Structure

Here’s a breakdown of the main files and folders in the repository:

```treatment_evaluation/
├── code/
│   ├── evaluate_treatments.py     # Main script
│   └── format_with_spacing.sh     # Optional helper script for readability
├── data/
│   ├── raw/
│   │   └── daily_puff_log.xlsx    # 🔒 Ignored — not in repo
│   └── processed/
│       └── puff_data.tsv          # Extracted and cleaned version of the Excel data
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
