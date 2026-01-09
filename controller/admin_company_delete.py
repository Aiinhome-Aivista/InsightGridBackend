from flask import request,g
from database.dbConnection import get_master_db
from helper.helperFunctions import build_response


def delete_company():
    try:
        if not hasattr(g, "user_id") or not hasattr(g, "role"):
            return build_response(False, "Unauthorized", 401)

        if g.role != "superadmin":
            return build_response(False, "Forbidden: Superadmin only", 403)
        
        data = request.get_json() or {}

        company_id = data.get("company_id")
        deleted_by = g.user_id 

        if not company_id or not deleted_by:
            return build_response(
                False,
                "company_id and deleted_by are required",
                None,
                400
            )

        conn = get_master_db()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc(
            "sp_delete_company",
            [company_id, deleted_by]
        )

        result = None
        for res in cursor.stored_results():
            result = res.fetchone()

        cursor.close()
        conn.close()

        if result and result.get("isSuccess") == 1:
            return build_response(
                True,
                result.get("message"),
                None,
                200
            )
        else:
            return build_response(
                False,
                result.get("message") if result else "Delete failed",
                None,
                200
            )

    except Exception as e:
        return build_response(
            False,
            str(e),
            None,
            500
        )
