from database.dbConnection import get_master_db, get_company_db
from helper.helperFunctions import build_response

def get_all_company_admins_controller():
    try:
        master = get_master_db()
        mcur = master.cursor(dictionary=True)

        # 🔹 STEP 1: Get all active companies
        mcur.execute("""
            SELECT 
                id AS company_id,
                company_code,
                company_name,
                company_db_name
            FROM companies
            WHERE is_active = 1
              AND is_deleted = 0
        """)
        companies = mcur.fetchall()

        result = []

        # 🔹 STEP 2: Loop each company DB
        for c in companies:
            try:
                company_db = get_company_db(c["company_db_name"])
                ccur = company_db.cursor(dictionary=True)

                # 🔹 Fetch company admin
                ccur.execute("""
                    SELECT
                        id,
                        user_id,
                        full_name,
                        email,
                        phone_number,
                        address,
                        created_at
                    FROM users
                    WHERE app_role_id = (
                        SELECT id FROM user_roles WHERE role_name = 'companyadmin'
                    )
                    AND is_deleted = 0
                    LIMIT 1
                """)

                admin = ccur.fetchone()

                if admin:
                    result.append({
                        "company_id": c["company_id"],
                        "company_code": c["company_code"],
                        "company_name": c["company_name"],
                        "company_db": c["company_db_name"],

                        "admin_user_id": admin["user_id"],
                        "admin_name": admin["full_name"],
                        "admin_email": admin["email"],
                        "created_at": admin["created_at"],
                        "phone_number": admin["phone_number"],
                        "address": admin["address"],
                        "id": admin["id"]
                    })

                ccur.close()
                company_db.close()

            except Exception as inner_err:
                # 🔥 If company DB missing / corrupted → skip safely
                print(f"Skipping {c['company_db_name']} → {inner_err}")
                continue

        mcur.close()
        master.close()

        return build_response(
            True,
            "Company admin list fetched successfully",
            200,
            data=result
        )

    except Exception as e:
        return build_response(
            False,
            "Server error",
            500,
            data={"error": str(e)}
        )
