import pandas as pd

def detect_column_type(value):
    if pd.isna(value):
        return "text"
    if str(value).lower() in ["true", "false", "yes", "no", "0", "1"]:
        return "boolean"
    try:
        float(value)
        return "number"
    except:
        pass
    try:
        pd.to_datetime(value)
        return "date"
    except:
        pass
    return "text"


OPERATIONS_MAP = {
    "number": ["equal", "not_equal", "greater_than", "less_than", "range"],
    "text": ["contains", "not_contains", "starts_with", "ends_with", "equal", "not_equal"],
    "date": ["before", "after", "between"]
}


def build_columns_metadata(df):
    columns_meta = []
    for i, col in enumerate(df.columns, start=1):
        col_values = df[col].dropna()
        if len(col_values) > 0:
            sample_val = col_values.iloc[0]
            col_type = detect_column_type(sample_val)
        else:
            col_type = "text"
        columns_meta.append({"column_id": f"col_{i}", "column_name": col, "column_type": col_type})
    return columns_meta


def build_sheet_output(sheet_name, df):
    return {sheet_name: {"rows": df.to_dict(orient="records"), "columns": build_columns_metadata(df)}}


def build_full_response(all_sheets_dfs):
    final = {"data": {}, "operations": OPERATIONS_MAP}
    for sheet_name, df in all_sheets_dfs.items():
        final["data"].update(build_sheet_output(sheet_name, df))
    return final
