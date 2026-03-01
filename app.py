from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
import os
import pickle
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ============================================================
# CONFIGURATION
# ============================================================
CUTOFF_FILE = "TSEAMCET.csv"
PG_CUTOFF_FILE = "PG_PGECET_Cutoffs_100_Colleges.csv"
PG_MODEL_FILE = "pg_model.pkl"

# Global variables to store loaded data
df = None  # UG data
pg_model = None  # PG model
pg_data = None  # PG raw data

# ============================================================
# LOAD AND PROCESS DATA
# ============================================================

def load_cutoff_data():
    """Load and process the TSEAMCET cutoff data"""
    global df

    if not os.path.exists(CUTOFF_FILE):
        return False, f"Error: {CUTOFF_FILE} not found!"

    try:
        # Read CSV
        data = pd.read_csv(CUTOFF_FILE)

        # Clean column names - remove quotes and extra spaces
        data.columns = data.columns.str.strip().str.replace('"', '')

        # Create a list to store all records
        records = []

        for idx, row in data.iterrows():
            institute = row['Institute Name']

            # Skip if institute name is NaN
            if pd.isna(institute):
                continue

            branch = row['Branch Code']

            # Process each category-gender combination
            for col in data.columns:
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
                        continue

        # Create DataFrame from records
        if len(records) == 0:
            return False, "No valid records found in the file!"

        df = pd.DataFrame(records)
        return True, f"Loaded {len(df):,} records successfully!"

    except Exception as e:
        return False, f"Error loading data: {str(e)}"

def load_pg_model():
    """Load the PG model"""
    global pg_model, pg_data

    if not os.path.exists(PG_MODEL_FILE):
        return False, f"Error: {PG_MODEL_FILE} not found!"

    try:
        with open(PG_MODEL_FILE, 'rb') as f:
            pg_model = pickle.load(f)

        # Also load raw data for reference
        if os.path.exists(PG_CUTOFF_FILE):
            pg_data = pd.read_csv(PG_CUTOFF_FILE)

        return True, f"PG Model loaded successfully!"
    except Exception as e:
        return False, f"Error loading PG model: {str(e)}"

# ============================================================
# FIND COLLEGES IN RANGE AND CALCULATE CHANCE (UG)
# ============================================================

def find_colleges_in_range(user_rank, range_value, user_category, user_gender):
    """Find all colleges where cutoff rank is in appropriate range"""

    global df

    # Standardize inputs
    user_category = user_category.upper().strip()
    user_gender = user_gender.upper().strip()

    # Fix gender input
    if user_gender == 'BOY':
        user_gender = 'BOYS'
    elif user_gender == 'GIRL':
        user_gender = 'GIRLS'

    # Determine range based on rank and user range
    if range_value == 0 or user_rank <= range_value:
        min_rank = 0
    else:
        min_rank = user_rank - range_value

    # Filter by category and gender
    mask = (df['Category'] == user_category) & (df['Gender'] == user_gender)
    filtered = df[mask].copy()

    if len(filtered) == 0:
        return None, f"No data found for {user_category} - {user_gender}"

    # Filter by rank range: cutoff should be <= user_rank and >= min_rank
    range_mask = (filtered['Cutoff_Rank'] <= user_rank) & (filtered['Cutoff_Rank'] >= min_rank)
    in_range = filtered[range_mask].copy()

    if len(in_range) == 0:
        return None, f"No colleges found with cutoff in range [{min_rank}, {user_rank}]"

    # Calculate admission chance
    in_range['Distance'] = user_rank - in_range['Cutoff_Rank']
    range_width = user_rank - min_rank

    if range_width > 0:
        in_range['Admission_Chance'] = 100 - (80 * (in_range['Distance'] / range_width))
    else:
        in_range['Admission_Chance'] = 100

    in_range['Admission_Chance'] = in_range['Admission_Chance'].clip(lower=20, upper=100)
    in_range['Admission_Chance'] = in_range['Admission_Chance'].round(1)

    # Sort by chance
    in_range = in_range.sort_values('Admission_Chance', ascending=False)
    in_range = in_range.drop_duplicates(subset=['Institute', 'Branch'])

    return in_range, None

# ============================================================
# PREDICT PG COLLEGES
# ============================================================

def predict_pg_colleges(user_rank, user_category, user_branch, range_value=1000):
    """Predict PG colleges based on GATE rank"""

    global pg_model

    if pg_model is None:
        return None, "PG model not loaded"

    try:
        # Get data from model
        data = pg_model['data']

        # Standardize inputs
        user_category = user_category.upper().strip()
        user_branch = user_branch.upper().strip()

        # Filter by category and branch
        mask = (data['Category'] == user_category) & (data['Branch'] == user_branch)
        filtered = data[mask].copy()

        if len(filtered) == 0:
            return None, f"No data found for {user_category} - {user_branch}"

        # Determine range
        if range_value == 0 or user_rank <= range_value:
            min_rank = 0
        else:
            min_rank = user_rank - range_value

        # Filter by rank range
        range_mask = (filtered['Closing_Rank'] <= user_rank) & (filtered['Closing_Rank'] >= min_rank)
        in_range = filtered[range_mask].copy()

        if len(in_range) == 0:
            # Show closest colleges if none in range
            closest = filtered.nsmallest(10, 'Closing_Rank')
            in_range = closest
            message = f"No colleges in exact range. Showing closest matches:"
        else:
            message = None

        # Calculate admission chance
        in_range['Distance'] = user_rank - in_range['Closing_Rank']
        range_width = user_rank - min_rank

        if range_width > 0:
            in_range['Admission_Chance'] = 100 - (80 * (in_range['Distance'] / range_width))
        else:
            in_range['Admission_Chance'] = 100

        in_range['Admission_Chance'] = in_range['Admission_Chance'].clip(lower=20, upper=100)
        in_range['Admission_Chance'] = in_range['Admission_Chance'].round(1)

        # Sort by chance
        in_range = in_range.sort_values('Admission_Chance', ascending=False)
        in_range = in_range.drop_duplicates(subset=['College', 'Branch'])

        return in_range, message

    except Exception as e:
        return None, f"Error in prediction: {str(e)}"

# ============================================================
# GENERATE PLOT (UG)
# ============================================================

def generate_plot(results, user_rank, range_value, user_category, user_gender):
    """Generate base64 encoded plot of top 10 recommendations"""

    # Determine range for title
    if range_value == 0 or user_rank <= range_value:
        range_display = f"0 to {user_rank}"
    else:
        range_display = f"{user_rank - range_value} to {user_rank}"

    # Get top 10
    top_10 = results.head(10).iloc[::-1]

    # Create labels
    labels = []
    for _, row in top_10.iterrows():
        college = row['Institute']
        if len(college) > 30:
            college = college[:27] + "..."
        labels.append(f"{college} - {row['Branch']}")

    chances = top_10['Admission_Chance'].values
    distances = top_10['Distance'].values

    # Colors from palette
    colors = ['#F76C7C' if c >= 80 else '#F8E9A1' if c >= 60 else '#A8D0E6' for c in chances]

    # Create plot with custom styling
    plt.figure(figsize=(12, 6), facecolor='#24305E')
    ax = plt.gca()
    ax.set_facecolor('#374785')

    bars = plt.barh(range(len(labels)), chances, color=colors, edgecolor='white', linewidth=1)

    # Customize
    plt.yticks(range(len(labels)), labels, fontsize=10, color='white')
    plt.xlabel('Admission Chance (%)', fontsize=12, fontweight='bold', color='white')
    plt.title(f'Top 10 Recommendations\nRank: {user_rank} | Range: {range_display} | {user_category} - {user_gender}',
              fontsize=14, fontweight='bold', pad=20, color='white')
    plt.xlim(0, 100)
    plt.grid(axis='x', alpha=0.2, linestyle='--', color='white')

    # Style ticks
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')

    # Add value labels
    for i, (bar, chance, dist) in enumerate(zip(bars, chances, distances)):
        plt.text(chance + 1, bar.get_y() + bar.get_height()/2,
                f'{chance:.1f}%', va='center', fontsize=9,
                fontweight='bold', color='white')

    plt.tight_layout()

    # Convert to base64
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight', facecolor='#24305E')
    img.seek(0)
    plt.close()

    return base64.b64encode(img.getvalue()).decode()

# ============================================================
# GENERATE PG PLOT
# ============================================================

def generate_pg_plot(results, user_rank, range_value, user_category, user_branch):
    """Generate plot for PG predictions"""

    # Determine range for title
    if range_value == 0 or user_rank <= range_value:
        range_display = f"0 to {user_rank}"
    else:
        range_display = f"{user_rank - range_value} to {user_rank}"

    # Get top 10
    top_10 = results.head(10).iloc[::-1]

    # Create labels
    labels = []
    for _, row in top_10.iterrows():
        college = row['College']
        if len(college) > 30:
            college = college[:27] + "..."
        labels.append(f"{college}")

    chances = top_10['Admission_Chance'].values
    distances = top_10['Distance'].values

    # Colors from palette
    colors = ['#F76C7C' if c >= 80 else '#F8E9A1' if c >= 60 else '#A8D0E6' for c in chances]

    # Create plot with custom styling
    plt.figure(figsize=(12, 6), facecolor='#24305E')
    ax = plt.gca()
    ax.set_facecolor('#374785')

    bars = plt.barh(range(len(labels)), chances, color=colors, edgecolor='white', linewidth=1)

    # Customize
    plt.yticks(range(len(labels)), labels, fontsize=10, color='white')
    plt.xlabel('Admission Chance (%)', fontsize=12, fontweight='bold', color='white')
    plt.title(f'Top 10 PG Recommendations\nGATE Rank: {user_rank} | {user_branch} | {user_category}',
              fontsize=14, fontweight='bold', pad=20, color='white')
    plt.xlim(0, 100)
    plt.grid(axis='x', alpha=0.2, linestyle='--', color='white')

    # Style ticks
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')

    # Add value labels
    for i, (bar, chance, dist) in enumerate(zip(bars, chances, distances)):
        plt.text(chance + 1, bar.get_y() + bar.get_height()/2,
                f'{chance:.1f}%', va='center', fontsize=9,
                fontweight='bold', color='white')

    plt.tight_layout()

    # Convert to base64
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight', facecolor='#24305E')
    img.seek(0)
    plt.close()

    return base64.b64encode(img.getvalue()).decode()

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ug')
def ug_index():
    return render_template('ug_index.html')

@app.route('/pg')
def pg_index():
    return render_template('pg_index.html')

@app.route('/api/load-data', methods=['POST'])
def api_load_data():
    success, message = load_cutoff_data()
    if success:
        categories = sorted(df['Category'].unique()) if df is not None else []
        return jsonify({
            'success': True,
            'message': message,
            'categories': categories,
            'total_records': len(df) if df is not None else 0
        })
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/load-pg-data', methods=['POST'])
def api_load_pg_data():
    success, message = load_pg_model()
    if success:
        branches = sorted(pg_model['unique_branches']) if pg_model is not None else []
        categories = sorted(pg_model['unique_categories']) if pg_model is not None else []
        return jsonify({
            'success': True,
            'message': message,
            'branches': branches,
            'categories': categories
        })
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.json
        rank = int(data['rank'])
        range_val = int(data['range'])
        category = data['category']
        gender = data['gender']

        # Validate range
        if range_val < 0:
            return jsonify({'success': False, 'message': 'Range cannot be negative'})

        # Get predictions
        results, error = find_colleges_in_range(rank, range_val, category, gender)

        if error:
            return jsonify({'success': False, 'message': error})

        # Generate plot
        plot_data = generate_plot(results, rank, range_val, category, gender)

        # Prepare results for JSON
        results_json = []
        for _, row in results.iterrows():
            results_json.append({
                'institute': row['Institute'],
                'branch': row['Branch'],
                'cutoff': int(row['Cutoff_Rank']),
                'distance': int(row['Distance']),
                'chance': float(row['Admission_Chance'])
            })

        # Determine range display
        if range_val == 0 or rank <= range_val:
            range_display = f"0 to {rank}"
        else:
            range_display = f"{rank - range_val} to {rank}"

        return jsonify({
            'success': True,
            'results': results_json,
            'plot': plot_data,
            'total': len(results_json),
            'range_display': range_display,
            'rank': rank,
            'category': category,
            'gender': gender
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/predict-pg', methods=['POST'])
def api_predict_pg():
    try:
        data = request.json
        rank = int(data['rank'])
        range_val = int(data.get('range', 1000))
        category = data['category']
        branch = data['branch']

        # Validate range
        if range_val < 0:
            return jsonify({'success': False, 'message': 'Range cannot be negative'})

        # Get predictions
        results, warning = predict_pg_colleges(rank, category, branch, range_val)

        if results is None:
            return jsonify({'success': False, 'message': warning})

        # Generate plot
        plot_data = generate_pg_plot(results, rank, range_val, category, branch)

        # Prepare results for JSON
        results_json = []
        for _, row in results.iterrows():
            results_json.append({
                'college': row['College'],
                'branch': row['Branch'],
                'cutoff': int(row['Closing_Rank']),
                'distance': int(row['Distance']) if 'Distance' in row else 0,
                'chance': float(row['Admission_Chance']) if 'Admission_Chance' in row else 0
            })

        # Determine range display
        if range_val == 0 or rank <= range_val:
            range_display = f"0 to {rank}"
        else:
            range_display = f"{rank - range_val} to {rank}"

        return jsonify({
            'success': True,
            'results': results_json,
            'plot': plot_data,
            'total': len(results_json),
            'range_display': range_display,
            'rank': rank,
            'category': category,
            'branch': branch,
            'warning': warning
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/download', methods=['POST'])
def api_download():
    try:
        data = request.json
        results = data['results']

        # Create DataFrame
        df_download = pd.DataFrame(results)

        # Check if it's UG or PG data
        if 'institute' in df_download.columns:
            df_download = df_download.rename(columns={
                'institute': 'Institute',
                'branch': 'Branch',
                'cutoff': 'Cutoff_Rank',
                'distance': 'Distance_from_Rank',
                'chance': 'Admission_Chance_%'
            })
        elif 'college' in df_download.columns:
            df_download = df_download.rename(columns={
                'college': 'College',
                'branch': 'Branch',
                'cutoff': 'Cutoff_Rank',
                'distance': 'Distance_from_Rank',
                'chance': 'Admission_Chance_%'
            })

        # Add metadata
        df_download['User_Rank'] = data['rank']
        df_download['Range_Used'] = data['range_display']
        df_download['Category'] = data['category']
        if 'gender' in data:
            df_download['Gender'] = data['gender']
        if 'branch' in data:
            df_download['Selected_Branch'] = data['branch']

        # Create CSV
        csv_data = df_download.to_csv(index=False)

        return jsonify({
            'success': True,
            'csv': csv_data
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)