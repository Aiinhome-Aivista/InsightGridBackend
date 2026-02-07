from flask import request, g
from helper.helperFunctions import build_response

# ======================================================
# COMMON SESSION VALIDATION
# ======================================================
def _validate_session(cursor, created_by, session_id):
    cursor.execute("""
        SELECT 1
        FROM users
        WHERE user_id = %s AND session_id = %s
        LIMIT 1
    """, (created_by, session_id))
    return cursor.fetchone() is not None


# ======================================================
# 1️ GET ADDRESS BOOKS
# CALLS: sp_get_address_books(p_user_id)
# ======================================================
def get_address_books_controller():
    try:
        body = request.get_json() or {}
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor(dictionary=True)

        if not _validate_session(cursor, created_by, session_id):
            cursor.close()
            return build_response(False, "Invalid session", 401)

        cursor.callproc("sp_get_address_books", (created_by,))

        address_books = []
        for rs in cursor.stored_results():
            address_books = rs.fetchall()

        cursor.close()

        return build_response(
            True,
            "Address books retrieved",
            200,
            address_books
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to retrieve address books",
            500,
            {"error": str(e)}
        )


# ======================================================
#  CREATE ADDRESS BOOK
# CALLS: sp_create_address_book(p_name, p_user_id)
# ======================================================
def create_address_book_controller():
    try:
        body = request.get_json() or {}
        name = body.get("name")
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not name or not created_by or not session_id:
            return build_response(False, "name, created_by & session_id required", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor()

        if not _validate_session(cursor, created_by, session_id):
            cursor.close()
            return build_response(False, "Invalid session", 401)

        cursor.callproc("sp_create_address_book", (name, created_by))
        db.commit()
        cursor.close()

        return build_response(True, "Address book created successfully", 200)

    except Exception as e:
        return build_response(
            False,
            "Failed to create address book",
            500,
            {"error": str(e)}
        )


# ======================================================
#  ADD EMAIL TO ADDRESS BOOK
# CALLS: sp_add_email_to_address_book(p_address_book_id, p_email)
# ======================================================
def add_email_to_address_book_controller():
    try:
        body = request.get_json() or {}

        address_book_id = body.get("address_book_id")
        email = body.get("email")
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not address_book_id or not email or not created_by or not session_id:
            return build_response(False, "Missing required fields", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor()

        if not _validate_session(cursor, created_by, session_id):
            cursor.close()
            return build_response(False, "Invalid session", 401)

        try:
            #NO OUT PARAM
            cursor.callproc(
                "sp_add_email_to_address_book",
                (address_book_id, email)
            )
            db.commit()

        except Exception as e:
            db.rollback()

            # DUPLICATE EMAIL (UNIQUE constraint)
            if "1062" in str(e) or "Duplicate entry" in str(e):
                cursor.close()
                return build_response(
                    False,
                    "Email already exists in this address book",
                    409
                )

            raise e

        cursor.close()
        return build_response(True, "Email added successfully", 200)

    except Exception as e:
        return build_response(
            False,
            "Failed to add email",
            500,
            {"error": str(e)}
        )
# ======================================================
#  REMOVE EMAIL FROM ADDRESS BOOK
# CALLS: sp_remove_email_from_address_book(p_address_book_id, p_email)
# ======================================================
def remove_email_from_address_book_controller():
    try:
        body = request.get_json() or {}
        address_book_id = body.get("address_book_id")
        email = body.get("email")
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not address_book_id or not email or not created_by or not session_id:
            return build_response(False, "Missing required fields", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor(dictionary=True)

        if not _validate_session(cursor, created_by, session_id):
            cursor.close()
            return build_response(False, "Invalid session", 401)

        cursor.callproc(
            "sp_remove_email_from_address_book",
            (address_book_id, email)
        )

        result = None
        for rs in cursor.stored_results():
            result = rs.fetchone()

        db.commit()
        cursor.close()

        if not result:
            return build_response(False, "Unexpected response from server", 500)

        # ❌ DELETE BLOCKED
        if result["can_delete"] == 0:
            return build_response(
                False,
                result["message"],
                409
            )

        # ✅ DELETE SUCCESS
        return build_response(
            True,
            result["message"],
            200,
            {
                "can_delete": 1
            }
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to remove email",
            500,
            {"error": str(e)}
        )


def remove_address_book_controller():
    try:
        body = request.get_json() or {}
        address_book_id = body.get("address_book_id")
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not address_book_id or not created_by or not session_id:
            return build_response(False, "Missing required fields", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor(dictionary=True)

        if not _validate_session(cursor, created_by, session_id):
            cursor.close()
            return build_response(False, "Invalid session", 401)

        # 🔥 Call stored procedure
        cursor.callproc(
            "sp_remove_address_book",
            (address_book_id,)
        )

        result = None
        for rs in cursor.stored_results():
            result = rs.fetchone()

        db.commit()
        cursor.close()

        if not result:
            return build_response(
                False,
                "Unexpected response from server",
                500
            )

        # ❌ DELETE BLOCKED
        if result["can_delete"] == 0:
            return build_response(
                False,
                result["message"],
                409
            )

        # ✅ DELETE SUCCESS
        return build_response(
            True,
            result["message"],
            200
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to remove address book",
            500,
            {"error": str(e)}
        )
