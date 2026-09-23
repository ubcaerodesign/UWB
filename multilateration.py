import pandas as pd
import numpy as np

# ==========================================
# 1. DEFINE YOUR ANCHOR COORDINATES
# ==========================================
# x1, y1 -> physical Tag 2
x1, y1 = -45.0, 0.0

# x2, y2 -> physical Tag 3
x2, y2 = 0.0, 40.0

# x3, y3 -> physical Tag 5
x3, y3 = 45.0, 0.0

# x4, y4 -> physical Tag 7
x4, y4 = 0.0, 0.0

# ==========================================
# 2. CONSTRUCT MATRIX A & PSEUDO-INVERSE
# ==========================================
A = np.array([
    [x2 - x1, y2 - y1],
    [x3 - x1, y3 - y1],
    [x4 - x1, y4 - y1]
])

A_T = A.T
A_pseudo_inv = np.linalg.inv(A_T @ A) @ A_T


def calculate_position(row):
    """
    Calculates the target x, y position for a single row of distances.
    """
    # ==========================================
    # 3. PULL DISTANCES USING THE CORRECT TAG HEADERS
    # ==========================================
    d1 = pd.to_numeric(row['Tag 2 Measured Dist (cm)'], errors='coerce')
    d2 = pd.to_numeric(row['Tag 3 Measured Dist (cm)'], errors='coerce')
    d3 = pd.to_numeric(row['Tag 5 Measured Dist (cm)'], errors='coerce')
    d4 = pd.to_numeric(row['Tag 7 Measured Dist (cm)'], errors='coerce')

    # Skip rows where distance data is missing (blank rows)
    if pd.isna(d1) or pd.isna(d2) or pd.isna(d3) or pd.isna(d4):
        return pd.Series({'Measured x (cm)': np.nan, 'Measured y (cm)': np.nan})

    # Construct Vector b
    b = 0.5 * np.array([
        d1 ** 2 - d2 ** 2 + (x2 ** 2 + y2 ** 2) - (x1 ** 2 + y1 ** 2),
        d1 ** 2 - d3 ** 2 + (x3 ** 2 + y3 ** 2) - (x1 ** 2 + y1 ** 2),
        d1 ** 2 - d4 ** 2 + (x4 ** 2 + y4 ** 2) - (x1 ** 2 + y1 ** 2)
    ])

    # Calculate position vector x = [x_t, y_t]
    pos = A_pseudo_inv @ b

    # Round the results to 2 decimal places before returning
    return pd.Series({'Measured x (cm)': round(pos[0], 2), 'Measured y (cm)': round(pos[1], 2)})


def main():
    # Load the dataset
    input_filename = 'uwb_aerodesign_test.csv'
    print(f"Loading data from {input_filename}...")
    df = pd.read_csv(input_filename)

    # Clean up Excel headers
    df.columns = df.columns.str.strip()

    # Apply the multilateration function row by row
    print("Calculating coordinates...")
    results = df.apply(calculate_position, axis=1)

    # Force the results specifically into the exact existing columns
    df['Measured x (cm)'] = results['Measured x (cm)']
    df['Measured y (cm)'] = results['Measured y (cm)']

    # Save the results
    output_filename = 'uwb_aerodesign_processed.csv'

    try:
        df.to_csv(output_filename, index=False)
        print("==================================================")
        print(f"Success! Data has been written directly to the columns.")
        print(f"Open '{output_filename}' to see your filled spreadsheet!")
        print("==================================================")
    except PermissionError:
        print("\n==================================================")
        print(f"🛑 ERROR: Could not save to '{output_filename}'.")
        print("Please CLOSE the file in Excel and run this script again!")
        print("==================================================")


if __name__ == "__main__":
    main()
