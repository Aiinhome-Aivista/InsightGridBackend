from flask import g,request
from database.dbConnection import get_master_db
from helper.helperFunctions import build_response

def get_all_companies_controller():
    try:
        if not hasattr(g, "role"):
            return build_response(False, "Unauthorized", 401)

        if g.role != "superadmin":
            return build_response(False, "Forbidden: Superadmin only", 403)
        
        master = get_master_db()
        cursor = master.cursor(dictionary=True)

        cursor.callproc("sp_get_all_companies")

        data = []
        for result in cursor.stored_results():
            data = result.fetchall()
            

        cursor.close()
        master.close()

        # 🌐 build logo URLs for ALL companies
        base_url = request.host_url.rstrip("/")  # http://127.0.0.1:3008

        for row in data:
            logo_path = row.get("company_logo")
            row["company_logo_url"] = (
                f"{base_url}{logo_path}" if logo_path else None
            )

        # ✅ DIRECT DATA RETURN (NO EXTRA OBJECT)
        return build_response(
            True,
            "Company list fetched successfully",
            200,
            data=data
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to fetch companies",
            500,
            data=str(e)
        )
