import json
import pandas as pd
from utils.column_detector import build_full_response

# ------------------------------- Cleaning config -------------------------------
DROP_ROWS_WHICH_ARE_ALL_NULL = True
DROP_ROWS_WITH_ANY_NULL = False
STRIP_STRING_VALUES = True
CONVERT_NUMERIC = True
REMOVE_DUPLICATES = True


def normalize_rows_list(rows_list):
    if rows_list is None or not isinstance(rows_list, list):
        return []
    normalized = []
    for r in rows_list:
        if isinstance(r, dict):
            normalized.append(r)
        else:
            try:
                normalized.append(dict(r))
            except:
                continue
    return normalized


def clean_dataframe_from_rows(rows_list):
    norm_rows = normalize_rows_list(rows_list)
    raw_row_count = len(norm_rows)

    if raw_row_count == 0:
        empty_df = pd.DataFrame()
        meta = {"raw_row_count": 0, "cleaned_rows": 0, "cleaned_columns": 0, "remarks": "empty_input"}
        return empty_df, meta

    df = pd.DataFrame(norm_rows)
    df = df.replace(r'^\s*$', pd.NA, regex=True)

    if STRIP_STRING_VALUES:
        for c in df.select_dtypes(include=["object"]).columns:
            df[c] = df[c].astype(object).where(df[c].notna(), pd.NA)
            df[c] = df[c].apply(lambda x: x.strip() if isinstance(x, str) else x)

    if CONVERT_NUMERIC:
        for col in df.columns:
            try:
                converted = pd.to_numeric(df[col], errors="ignore")
                if converted.notna().sum() > 0:
                    df[col] = converted
            except:
                pass

    if DROP_ROWS_WHICH_ARE_ALL_NULL:
        df = df.dropna(how="all")

    if DROP_ROWS_WITH_ANY_NULL:
        df = df.dropna(how="any")

    if REMOVE_DUPLICATES:
        df = df.drop_duplicates()

    cleaned_rows, cleaned_cols = df.shape
    remarks = []
    if cleaned_rows != raw_row_count:
        remarks.append(f"rows_reduced:{raw_row_count}->{cleaned_rows}")
    else:
        remarks.append("rows_unchanged")
    if cleaned_cols == 0:
        remarks.append("no_columns")

    meta = {"raw_row_count": raw_row_count, "cleaned_rows": cleaned_rows, "cleaned_columns": cleaned_cols,
            "remarks": ";".join(remarks)}

    return df, meta


def build_cleaned_json_for_sheets(sheets_dict):
    """
    sheets_dict = {"Orders": cleaned_df1, "Customers": cleaned_df2}
    """
    return json.dumps(build_full_response(sheets_dict))
