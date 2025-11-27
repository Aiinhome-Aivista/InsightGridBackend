import pandas as pd
import json
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json


# def process_session_data_controller():
#     try:
#         data = request.get_json() or {}
#         session_id = data.get("session_id")
#         session_name = data.get("session_name")

#         if not session_id or not session_name:
#             return build_response(False, "session_id and session_name are required", 400)

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name])

#         result = []
#         for res in cursor.stored_results():
#             result.extend(res.fetchall())
#         print("Fetched Data:", result)
#         cursor.close()
#         conn.close()

#         return build_response(True, "Raw data fetched successfully", 200, data=result)

#     except Exception as e:
#         return build_response(False, f"Error fetching data: {str(e)}", 500)
    
    

import pandas as pd
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

# -----------------------------
# Helper: Fetch raw data from DB
# -----------------------------
def fetch_raw_data(session_id, session_name):
    """
    Fetch data using stored procedure for a given session_id and session_name
    Returns a list of dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name])

        result = []
        for res in cursor.stored_results():
            result.extend(res.fetchall())

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        raise Exception(f"Error fetching data: {str(e)}")



# -----------------------------
# Helper: Clean raw data
# -----------------------------
def clean_data(raw_data):
    if not raw_data:
        return pd.DataFrame()

    df = pd.DataFrame(raw_data)

    # Remove duplicates
    df = df.drop_duplicates()

    # Handle missing values
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = df[col].fillna(0)

    # Trim string columns
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip()
        df[col] = df[col].str.replace(r'\s+', ' ', regex=True)

    # Convert date columns
    for col in df.columns:
        if 'date' in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Numeric outlier handling (IQR capping only)
    numeric_cols = df.select_dtypes(include='number').columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # Optional: log-transform if highly skewed
        if (df[col] > 0).all() and df[col].skew() > 1:
            df[col] = np.log1p(df[col])

    # Categorical outliers
    cat_cols = df.select_dtypes(include='object').columns
    for col in cat_cols:
        counts = df[col].value_counts()
        rare = counts[counts < 5].index
        df[col] = df[col].replace(rare, 'Other')

    # Remove constant columns
    df = df.loc[:, df.nunique() > 1]

    return df
# -----------------------------
# Controller: Return raw data only
# -----------------------------
def process_session_data_controller():
    try:
        # 1️⃣ Get request data
        data = request.get_json() or {}
        session_id = data.get("session_id")
        session_name = data.get("session_name")

        if not session_id or not session_name:
            return build_response(False, "session_id and session_name are required", 400)

        # 2️⃣ Fetch raw data
        raw_data = fetch_raw_data(session_id, session_name)
        if not raw_data:
            return build_response(False, "No data found for this session", 404)

          # Clean the data
        df_cleaned = clean_data(raw_data)
        print("Cleaned Data:", df_cleaned)
        # 3️⃣ Return raw data in response
        return build_response(True, "Raw data fetched successfully", 200, data=df_cleaned.to_dict(orient='records'))

    except Exception as e:
        return build_response(False, f"Error fetching data: {str(e)}", 500)

