import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ============================================================
# CONFIGURATION
# ============================================================
CUTOFF_FILE = "TSEAMCET.csv"
RANGE_BELOW = 5000  # Default range below rank

# ============================================================
# LOAD AND PROCESS DATA
# ============================================================

def load_cutoff_data(filename):
    """Load and process the TSEAMCET cutoff data"""
    if not os.path.exists(filename):
        print(f"❌ Error: {filename} not found!")
        print(f"Current directory: {os.getcwd()}")
        return None

    print(f"✅ Found file: {filename}")

    # Read CSV
    try:
        df = pd.read_csv(filename)
        print(f"✅ Read {len(df)} rows from CSV")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return None

    # Clean column names - remove quotes and extra spaces
    df.columns = df.columns.str.strip().str.replace('"', '')

    # Create a list to store all records
    records = []
    skipped = 0

    for idx, row in df.iterrows():
        institute = row['Institute Name']

        # Skip if institute name is NaN
        if pd.isna(institute):
            skipped += 1
            continue

        branch = row['Branch Code']

        # Process each category-gender combination
        for col in df.columns:
            if col not in ['Institute Name', 'Branch Code']:
                # Get cutoff value
                cutoff_val = row[col]

                # Skip if NA or not a number
                if pd.isna(cutoff_val) or cutoff_val == 'NA' or cutoff_val == '':
                    continue

                try:
                    # Convert to integer
                    cutoff = int(float(str(cutoff_val).strip()))

                    col_upper = col.upper()

                    # Determine category and gender
                    if 'OC' in col_upper:
                        category = 'OC'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'EWS' in col_upper:
                        category = 'EWS'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'BC_A' in col_upper:
                        category = 'BC_A'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'BC_B' in col_upper:
                        category = 'BC_B'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'BC_C' in col_upper:
                        category = 'BC_C'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'BC_D' in col_upper:
                        category = 'BC_D'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'BC_E' in col_upper:
                        category = 'BC_E'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'SC' in col_upper:
                        category = 'SC'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    elif 'ST' in col_upper:
                        category = 'ST'
                        gender = 'BOYS' if 'BOYS' in col_upper else 'GIRLS'
                    else:
                        continue

                    # Add record
                    records.append({
                        'Institute': institute,
                        'Branch': branch,
                        'Category': category,
                        'Gender': gender,
                        'Cutoff_Rank': cutoff
                    })
                except (ValueError, TypeError):
                    skipped += 1
                    continue

    # Create DataFrame from records
    if len(records) == 0:
        print("❌ No valid records found!")
        return None

    result_df = pd.DataFrame(records)
    print(f"✅ Processed {len(result_df):,} valid records (skipped {skipped} invalid entries)")

    return result_df

# ============================================================
# FIND COLLEGES IN RANGE AND CALCULATE CHANCE
# ============================================================

def find_colleges_in_range(df, user_rank, user_category, user_gender):
    """Find all colleges where cutoff rank is in appropriate range based on rank value"""

    # Standardize inputs
    user_category = user_category.upper().strip()
    user_gender = user_gender.upper().strip()

    # Fix gender input
    if user_gender == 'BOY':
        user_gender = 'BOYS'
    elif user_gender == 'GIRL':
        user_gender = 'GIRLS'

    print(f"\n🔍 Searching for {user_category} - {user_gender}...")

    # Determine range based on rank
    if user_rank <= 3000:
        min_rank = 0
        range_type = "full"
        print(f"📊 Rank ≤ 3000: Looking for cutoffs between 0 and {user_rank}")
    else:
        min_rank = user_rank - RANGE_BELOW
        range_type = "partial"
        print(f"📊 Rank > 3000: Looking for cutoffs between {min_rank} and {user_rank}")

    # Filter by category and gender
    mask = (df['Category'] == user_category) & (df['Gender'] == user_gender)
    filtered = df[mask].copy()

    if len(filtered) == 0:
        print(f"❌ No data found for {user_category} - {user_gender}")
        print(f"Available categories: {sorted(df['Category'].unique())}")
        print(f"Available genders: {sorted(df['Gender'].unique())}")
        return None

    print(f"✅ Found {len(filtered):,} total records for your category-gender")

    # Filter by rank range: cutoff should be <= user_rank and >= min_rank
    range_mask = (filtered['Cutoff_Rank'] <= user_rank) & (filtered['Cutoff_Rank'] >= min_rank)
    in_range = filtered[range_mask].copy()

    if len(in_range) == 0:
        print(f"❌ No colleges found with cutoff in range [{min_rank}, {user_rank}]")
        return None

    print(f"✅ Found {len(in_range)} colleges/courses in your rank range")

    # Calculate admission chance based on how close cutoff is to user rank
    # Closer to user_rank = higher chance
    in_range['Distance'] = user_rank - in_range['Cutoff_Rank']  # How many ranks above cutoff

    # Calculate range width for percentage calculation
    range_width = user_rank - min_rank

    if range_width > 0:
        # Normalize: 0 distance = 100%, max distance = minimum chance (20%)
        in_range['Admission_Chance'] = 100 - (80 * (in_range['Distance'] / range_width))
    else:
        in_range['Admission_Chance'] = 100

    in_range['Admission_Chance'] = in_range['Admission_Chance'].clip(lower=20, upper=100)
    in_range['Admission_Chance'] = in_range['Admission_Chance'].round(1)

    # Sort by chance (descending) - which means closest to user rank first
    in_range = in_range.sort_values('Admission_Chance', ascending=False)

    # Remove duplicates (same college and branch)
    in_range = in_range.drop_duplicates(subset=['Institute', 'Branch'])

    return in_range

# ============================================================
# DISPLAY ALL RESULTS
# ============================================================

def display_all_results(results, user_rank, user_category, user_gender):
    """Display all matching colleges in descending order of chance"""

    # Determine range for display
    if user_rank <= 3000:
        range_display = f"0 to {user_rank}"
    else:
        range_display = f"{user_rank - RANGE_BELOW} to {user_rank}"

    print("\n" + "="*110)
    print(f"🎯 ALL MATCHING COLLEGES & COURSES (Sorted by Admission Chance)")
    print(f"📊 Based on: Rank = {user_rank} | Category = {user_category} | Gender = {user_gender}")
    print(f"📈 Range considered: {range_display}")
    print("="*110)

    print(f"\n{'No.':<4} {'Branch':<8} {'Cutoff':<8} {'Distance':<10} {'Chance':<8} {'College Name'}")
    print("-"*100)

    for i, (idx, row) in enumerate(results.iterrows(), 1):
        chance = row['Admission_Chance']
        distance = row['Distance']

        # Status emoji based on chance
        if chance >= 80:
            status = "🟢"
        elif chance >= 60:
            status = "🟡"
        elif chance >= 40:
            status = "🟠"
        else:
            status = "🔴"

        # Truncate college name if too long
        college = row['Institute']
        if len(college) > 65:
            college = college[:62] + "..."

        print(f"{i:<4} {row['Branch']:<8} {int(row['Cutoff_Rank']):<8} {int(distance):<10} {status} {chance:>5.1f}%   {college}")

    # Summary statistics
    print("\n" + "="*100)
    print("📊 SUMMARY STATISTICS")
    print("-"*100)

    total = len(results)
    excellent = len(results[results['Admission_Chance'] >= 80])
    good = len(results[(results['Admission_Chance'] >= 60) & (results['Admission_Chance'] < 80)])
    moderate = len(results[(results['Admission_Chance'] >= 40) & (results['Admission_Chance'] < 60)])
    low = len(results[results['Admission_Chance'] < 40])

    print(f"📌 Total Matches: {total}")
    print(f"🟢 Excellent Chance (≥80%): {excellent}")
    print(f"🟡 Good Chance (60-79%): {good}")
    print(f"🟠 Moderate Chance (40-59%): {moderate}")
    print(f"🔴 Low Chance (<40%): {low}")

    # Best match
    best = results.iloc[0]
    print(f"\n✨ Best Match: {best['Institute']} - {best['Branch']}")
    print(f"   Cutoff: {int(best['Cutoff_Rank'])} | Your Rank: {user_rank} | Distance: {int(best['Distance'])} | Chance: {best['Admission_Chance']:.1f}%")

# ============================================================
# PLOT TOP 10 RESULTS
# ============================================================

def plot_top_10(results, user_rank, user_category, user_gender):
    """Create a horizontal bar chart of top 10 recommendations"""

    # Determine range for title
    if user_rank <= 3000:
        range_display = f"0 to {user_rank}"
    else:
        range_display = f"{user_rank - RANGE_BELOW} to {user_rank}"

    # Get top 10
    top_10 = results.head(10).iloc[::-1]  # Reverse for display

    # Create labels (College + Branch)
    labels = []
    for _, row in top_10.iterrows():
        college = row['Institute']
        if len(college) > 40:
            college = college[:37] + "..."
        labels.append(f"{college} - {row['Branch']}")

    chances = top_10['Admission_Chance'].values
    distances = top_10['Distance'].values

    # Colors based on chance
    colors = ['green' if c >= 80 else 'orange' if c >= 60 else 'red' for c in chances]

    # Create plot
    plt.figure(figsize=(14, 8))
    bars = plt.barh(range(len(labels)), chances, color=colors)

    # Customize
    plt.yticks(range(len(labels)), labels, fontsize=10)
    plt.xlabel('Admission Chance (%)', fontsize=12)
    plt.title(f'Top 10 College-Branch Recommendations\nRank: {user_rank} | Category: {user_category} | Gender: {user_gender} | Range: {range_display}',
              fontsize=14, fontweight='bold')
    plt.xlim(0, 100)
    plt.grid(axis='x', alpha=0.3)

    # Add value labels (chance% and distance)
    for i, (bar, chance, dist) in enumerate(zip(bars, chances, distances)):
        plt.text(chance + 1, bar.get_y() + bar.get_height()/2,
                f'{chance:.1f}% (Δ{int(dist)})', va='center', fontsize=9)

    plt.tight_layout()
    plt.show()

# ============================================================
# EXPORT TO CSV
# ============================================================

def export_to_csv(results, user_rank, user_category, user_gender):
    """Export all recommendations to CSV"""

    # Determine range
    if user_rank <= 3000:
        range_display = f"0 to {user_rank}"
    else:
        range_display = f"{user_rank - RANGE_BELOW} to {user_rank}"

    export_df = results[['Institute', 'Branch', 'Category', 'Gender',
                         'Cutoff_Rank', 'Admission_Chance', 'Distance']].copy()
    export_df['User_Rank'] = user_rank
    export_df['Range_Considered'] = range_display

    # Rename columns
    export_df.columns = ['Institute', 'Branch', 'Category', 'Gender',
                         'Cutoff_Rank', 'Admission_Chance_%', 'Ranks_Above_Cutoff',
                         'User_Rank', 'Range_Considered']

    # Generate filename
    filename = f"recommendations_rank{user_rank}_{user_category}_{user_gender}.csv"

    # Save
    export_df.to_csv(filename, index=False)
    print(f"\n📁 All recommendations exported to: {filename}")

# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    print("\n" + "="*70)
    print("🎯 TSEAMCET COLLEGE & COURSE PREDICTOR 2023")
    print("="*70)

    # Load data
    print("\n📂 Loading cutoff data...")
    df = load_cutoff_data(CUTOFF_FILE)

    if df is None:
        return

    # Show available data
    print(f"\n📊 Data Summary:")
    print(f"   - Total Records: {len(df):,}")
    print(f"   - Unique Colleges: {df['Institute'].nunique():,}")
    print(f"   - Unique Branches: {df['Branch'].nunique()}")
    print(f"   - Categories: {', '.join(sorted(df['Category'].unique()))}")

    # Get user input
    print("\n" + "-"*50)
    print("📝 ENTER YOUR DETAILS")
    print("-"*50)

    try:
        rank = int(input("Enter your EAMCET Rank: "))

        print("\nAvailable Categories: OC, BC_A, BC_B, BC_C, BC_D, BC_E, SC, ST, EWS")
        category = input("Enter your Category: ").strip().upper()

        print("\nAvailable Genders: BOYS, GIRLS")
        gender = input("Enter your Gender: ").strip().upper()

    except ValueError:
        print("❌ Rank must be a number!")
        return

    # Find colleges in range
    print("\n🔍 Analyzing your chances...")
    results = find_colleges_in_range(df, rank, category, gender)

    if results is None or len(results) == 0:
        print("\n❌ No colleges found in your rank range!")
        return

    # Display ALL results
    display_all_results(results, rank, category, gender)

    # Plot TOP 10 results
    print("\n📊 Generating visualization for top 10...")
    plot_top_10(results, rank, category, gender)

    # Export ALL to CSV
    export_to_csv(results, rank, category, gender)

    print(f"\n✅ Done! Found {len(results)} matching colleges/courses.")
    print(f"   Check the CSV file for complete list.")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()