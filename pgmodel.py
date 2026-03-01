"""
PG Model Training Script
Run this once to create the PG model pickle file
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder
import os

def create_pg_model():
    """Create and save PG model from cutoff data"""

    print("Loading PG cutoff data...")
    df = pd.read_csv('PG_PGECET_Cutoffs_100_Colleges.csv')

    print(f"Loaded {len(df)} records")

    # Clean data
    df = df.dropna()

    # Create label encoders
    college_encoder = LabelEncoder()
    branch_encoder = LabelEncoder()
    category_encoder = LabelEncoder()

    # Encode categorical variables
    df['College_Encoded'] = college_encoder.fit_transform(df['College'])
    df['Branch_Encoded'] = branch_encoder.fit_transform(df['Branch'])
    df['Category_Encoded'] = category_encoder.fit_transform(df['Category'])

    # Prepare features and target
    X = df[['Branch_Encoded', 'Category_Encoded']].values
    y = df['Closing_Rank'].values

    # Create model dictionary with all necessary components
    model = {
        'X': X,
        'y': y,
        'data': df,
        'college_encoder': college_encoder,
        'branch_encoder': branch_encoder,
        'category_encoder': category_encoder,
        'unique_colleges': sorted(df['College'].unique()),
        'unique_branches': sorted(df['Branch'].unique()),
        'unique_categories': sorted(df['Category'].unique())
    }

    # Save model
    with open('pg_model.pkl', 'wb') as f:
        pickle.dump(model, f)

    print(f"PG Model created successfully!")
    print(f"Colleges: {len(model['unique_colleges'])}")
    print(f"Branches: {len(model['unique_branches'])}")
    print(f"Categories: {len(model['unique_categories'])}")

    return model

if __name__ == "__main__":
    create_pg_model()