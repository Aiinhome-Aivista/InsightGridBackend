# controller/admin_company_register.py

from flask import request
import mysql.connector
import os
from database.dbConnection import get_master_db
from helper.helperFunctions import build_response,allowed_logo
from datetime import datetime
import re
from werkzeug.utils import secure_filename


MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB

def generate_company_code(company_name, cursor):
    clean = re.sub(r'[^a-zA-Z ]', '', company_name).upper()
    words = clean.split()

    prefix = words[0][:3]

    domain_map = {
        "RETAIL": "RTL",
        "TECH": "TEC",
        "TECHNOLOGY": "TEC",
        "SOLUTIONS": "SOL",
        "SERVICES": "SRV"
    }

    domain = "GEN"
    for w in words:
        if w in domain_map:
            domain = domain_map[w]
            break

    year = datetime.now().strftime("%y")  # 25

    cursor.execute("""
        SELECT company_code
        FROM companies
        WHERE company_code LIKE %s
        ORDER BY id DESC
        LIMIT 1
    """, (f"{prefix}{domain}{year}%",))

    last = cursor.fetchone()

    seq = int(last["company_code"][-3:]) + 1 if last else 1

    return f"{prefix}{domain}{year}{str(seq).zfill(3)}"

# ==========================================================
# ENV CONFIG
# ==========================================================
MASTER_DB_HOST = os.getenv("DB_HOST")
MASTER_DB_USER = os.getenv("DB_USER")
MASTER_DB_PASS = os.getenv("DB_PASSWORD")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")


# ==========================================================
# CREATE ALL STORED PROCEDURES INSIDE COMPANY DB
# ==========================================================
def create_stored_procedures(db_name):
    conn = mysql.connector.connect(
        host=MASTER_DB_HOST,
        user=MASTER_DB_USER,
        password=MASTER_DB_PASS,
        database=db_name
    )
    c = conn.cursor()

    c.execute(f"USE `{db_name}`")

    # =====================================================
    # sp_delete_uploaded_file
    # =====================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_delete_uploaded_file")
    c.execute("""
    CREATE PROCEDURE sp_delete_uploaded_file(
        IN p_session_id VARCHAR(100),
        IN p_created_by VARCHAR(100),
        IN p_file_name VARCHAR(255)
        )
        proc_block:
        BEGIN
            DECLARE v_table_name VARCHAR(255);
            DECLARE v_user_exists INT DEFAULT 0;
            DECLARE v_table_exists INT DEFAULT 0;
            DECLARE v_query_dep INT DEFAULT 0;
            DECLARE v_report_dep INT DEFAULT 0;

            /* Validate session + user */
            SELECT COUNT(*) INTO v_user_exists
            FROM users
            WHERE user_id = p_created_by
            AND session_id = p_session_id;

            IF v_user_exists = 0 THEN
                SELECT 'Invalid session_id or created_by' AS status;
                LEAVE proc_block;
            END IF;

            /*Resolve table_name */
            SELECT table_name
            INTO v_table_name
            FROM uploaded_files
            WHERE session_id = p_session_id
            AND created_by = p_created_by
            AND file_name = p_file_name
            LIMIT 1;

            IF v_table_name IS NULL THEN
                SELECT 'No file metadata found' AS status;
                LEAVE proc_block;
            END IF;

            /* QUERY dependency check */
            SELECT COUNT(*) INTO v_query_dep
            FROM query_history
            WHERE session_id = p_session_id
            AND created_by = p_created_by
            AND table_names IS NOT NULL
            AND JSON_CONTAINS(table_names, JSON_QUOTE(v_table_name))
            AND is_execute = 1;

            IF v_query_dep > 0 THEN
                -- Result set 1: status
                SELECT CONCAT(
                    'Table "', v_table_name,
                    '" is already used in ', v_query_dep,
                    ' queries'
                ) AS status;

                -- Result set 2: query dependency list
                SELECT
                    id,
                    query_title,
                    created_by,
                    created_at
                FROM query_history
                WHERE session_id = p_session_id
                AND created_by = p_created_by
                AND table_names IS NOT NULL
                AND JSON_CONTAINS(table_names, JSON_QUOTE(v_table_name))
                AND is_execute = 1
                ORDER BY created_at DESC;

                LEAVE proc_block;
            END IF;

            /* REPORT dependency check */
            SELECT COUNT(*) INTO v_report_dep
            FROM saved_reports sr
            JOIN query_history q
            ON q.id = sr.query_history_id
            WHERE sr.session_id = p_session_id
            AND sr.user_id = p_created_by
            AND q.table_names IS NOT NULL
            AND JSON_CONTAINS(q.table_names, JSON_QUOTE(v_table_name));

            IF v_report_dep > 0 THEN
                -- Result set 1: status
                SELECT CONCAT(
                    'Table "', v_table_name,
                    '" is already used in ', v_report_dep,
                    ' reports'
                ) AS status;

                -- Result set 2: report dependency list
                SELECT
                    sr.report_id,
                    sr.report_name,
                    sr.created_at
                FROM saved_reports sr
                JOIN query_history q
                ON q.id = sr.query_history_id
                WHERE sr.session_id = p_session_id
                AND sr.user_id = p_created_by
                AND q.table_names IS NOT NULL
                AND JSON_CONTAINS(q.table_names, JSON_QUOTE(v_table_name))
                ORDER BY sr.created_at DESC;

                LEAVE proc_block;
            END IF;

            /*Table MUST exist */
            SELECT COUNT(*) INTO v_table_exists
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = v_table_name;

            IF v_table_exists = 0 THEN
                SELECT 'Table does not exist - delete operation aborted' AS status;
                LEAVE proc_block;
            END IF;

            /* Safe delete */
            START TRANSACTION;

            SET @drop_sql = CONCAT('DROP TABLE `', v_table_name, '`');
            PREPARE stmt FROM @drop_sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;

            DELETE FROM uploaded_files
            WHERE session_id = p_session_id
            AND created_by = p_created_by
            AND table_name = v_table_name;

            COMMIT;

            SELECT 'Table and all related metadata deleted successfully' AS status;
    END
    """)

    # =====================================================
    # sp_get_dashboard_data
    # =====================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_get_dashboard_data")
    c.execute("""
    CREATE PROCEDURE sp_get_dashboard_data(
        IN p_session_id VARCHAR(50),
        IN p_created_by VARCHAR(50)
    )
    BEGIN
            -- TOTAL FILE UPLOADS
        SELECT 
            COUNT(*) AS total_uploaded_files
        FROM uploaded_files
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND table_extraction_status = 'done'
        AND column_extraction_status = 'done'
        AND data_insights_status = 'done';

        -- TOTAL FILE EXTRACTED
        SELECT 
            COUNT(*) AS table_extract_status
        FROM uploaded_files
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND table_extraction_status = 'done';

        -- TOTAL REPORTS GENERATED
    SELECT 
        COUNT(*) AS total_reports_generated
    FROM saved_reports
    WHERE user_id = p_created_by
    AND session_id = p_session_id;

        -- TOTAL QUERIES GENERATED
        SELECT 
            COUNT(*) AS total_queries
        FROM query_history
        WHERE created_by = p_created_by 
        AND session_id = p_session_id;

        -- WORKING QUERIES (executed)
        SELECT 
            COUNT(*) AS working_queries
        FROM query_history
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND is_execute = 1;

        -- MOST RECENTLY UPLOADED FILE DETAILS
        SELECT *
        FROM uploaded_files
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND table_extraction_status = 'done'
        AND column_extraction_status = 'done'
        AND data_insights_status = 'done'
        -- ORDER BY updated_at DESC
        ORDER BY  COALESCE(updated_at, created_at) DESC
        LIMIT 1;
    END
    """)

    # =====================================================
    # sp_get_full_table_info
    # =====================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_get_full_table_info")
    c.execute("""
    CREATE PROCEDURE sp_get_full_table_info(
        IN p_created_by VARCHAR(100),
        IN p_session_id VARCHAR(100)
    )
    BEGIN
            SELECT DISTINCT
            table_name AS label,
            table_name AS value
        FROM uploaded_files
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND table_extraction_status = 'done'
        AND column_extraction_status = 'done'
        AND data_insights_status = 'done';


        --  COLUMN METADATA FOR ALL TABLES (FIXED, LOGIC SAME)
        SELECT
            t.table_name,
            c.ORDINAL_POSITION AS column_id,
            c.COLUMN_NAME,
            c.DATA_TYPE
        FROM (
            SELECT DISTINCT table_name
            FROM uploaded_files
            WHERE created_by = p_created_by
            AND session_id = p_session_id
            AND table_extraction_status = 'done'
            AND column_extraction_status = 'done'
            AND data_insights_status = 'done'
        ) t
        JOIN INFORMATION_SCHEMA.COLUMNS c
        ON c.TABLE_NAME = t.table_name
        AND c.TABLE_SCHEMA = DATABASE()
        ORDER BY t.table_name, c.ORDINAL_POSITION;


        --  INSIGHTS FOR EACH TABLE (NO CHANGE)
        SELECT
            table_name,
            insights
        FROM uploaded_files
        WHERE created_by = p_created_by
        AND session_id = p_session_id
        AND table_extraction_status = 'done'
        AND column_extraction_status = 'done'
        AND data_insights_status = 'done';
    END
    """)

    # =====================================================
    # sp_get_query_details_by_user_session_id
    # =====================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_get_query_details_by_user_session_id")
    c.execute("""
    CREATE PROCEDURE sp_get_query_details_by_user_session_id(
        IN p_created_by VARCHAR(100),
        IN p_session_id VARCHAR(100)
    )
    BEGIN
         SELECT 
        q.id,
        q.query_title,
        q.user_query AS `query`,
        q.ai_response,

        q.is_execute,
        q.row_count AS rows_effected,
        q.query_time,

        q.mode,
        q.parent_query_id,
        q.version_no,
        q.is_latest,

		TIME_FORMAT(q.created_at, '%h:%i %p') AS created_at,
        DATE_FORMAT(q.created_at, '%d-%m-%Y') AS created_date,
        q.created_at AS actual_created_at,
         q.created_by,
        q.session_id,
        q.updated_by,
        q.updated_at
     FROM query_history q
    WHERE q.created_by = p_created_by
      AND q.session_id = p_session_id
      AND q.mode IN ('NEW','EDIT','CONTEXT')
    ORDER BY 
      q.created_at DESC;     
    END
    """)
    #  COALESCE(q.parent_query_id, q.id),
    #   q.version_no DESC,
    # ============================================================
    # sp_get_report_list
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_get_report_list")
    c.execute("""
    CREATE PROCEDURE sp_get_report_list(
        IN p_session_id VARCHAR(100),
        IN p_user_id VARCHAR(100)
    )
    BEGIN
            SELECT
            r.report_id,
            r.report_name,
            r.query_history_id,          -- VERY IMPORTANT
            r.row_affected,
            r.created_at,
            TIME_FORMAT(r.created_at, '%h:%i %p') AS actual_created_at,
            DATE_FORMAT(r.created_at, '%d-%m-%Y') AS actual_created_date,

            q.query_title,
            q.ai_response

        FROM saved_reports r
        INNER JOIN query_history q 
            ON q.id = r.query_history_id

        WHERE r.session_id = p_session_id
        AND r.user_id = p_user_id

        ORDER BY r.created_at DESC;
    END
    """)

    
    # ============================================================
    # sp_get_uploaded_files_status
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_get_uploaded_files_status")
    c.execute("""
    CREATE PROCEDURE sp_get_uploaded_files_status(
        IN p_created_by VARCHAR(100),
        IN p_session_id VARCHAR(100)
    )
    BEGIN
        -- Normal Data
        SELECT 
            uf.id AS file_id,
            uf.file_name,
            uf.table_name,
            uf.file_size_mb,
            uf.file_type,
            -- uf.total_rows as rows_effected,
			uf.last_inserted_rows as rows_effected,
            uf.total_columns,

            COALESCE(uf.table_extraction_status, 'pending') AS table_extraction_status,
            COALESCE(uf.column_extraction_status, 'pending') AS column_extraction_status,
            COALESCE(uf.data_insights_status, 'pending') AS data_insights_status,
			COALESCE(uf.data_insert_status, 'pending') AS data_insert_status,

            uf.insights,
--  CONNECTED QUERY COUNT
        (
            SELECT COUNT(*)
            FROM query_history qh
            WHERE qh.session_id = uf.session_id
              AND qh.created_by = uf.created_by
              AND JSON_CONTAINS(qh.table_names, JSON_QUOTE(uf.table_name))
        ) AS connected_queries,

        --  CONNECTED REPORT COUNT
        (
            SELECT COUNT(*)
            FROM saved_reports sr
            JOIN query_history qh ON qh.id = sr.query_history_id
            WHERE qh.session_id = uf.session_id
              AND qh.created_by = uf.created_by
              AND JSON_CONTAINS(qh.table_names, JSON_QUOTE(uf.table_name))
        ) AS connected_reports,

        --  QUERY TITLES (JSON)
        (
            SELECT JSON_ARRAYAGG(qh.query_title)
            FROM query_history qh
            WHERE qh.session_id = uf.session_id
              AND qh.created_by = uf.created_by
              AND JSON_CONTAINS(qh.table_names, JSON_QUOTE(uf.table_name))
        ) AS query_titles,

        --  REPORT NAMES (JSON)
        (
            SELECT JSON_ARRAYAGG(sr.report_name)
            FROM saved_reports sr
            JOIN query_history qh ON qh.id = sr.query_history_id
            WHERE qh.session_id = uf.session_id
              AND qh.created_by = uf.created_by
              AND JSON_CONTAINS(qh.table_names, JSON_QUOTE(uf.table_name))
        ) AS report_names,

            TIME_FORMAT(uf.created_at, '%H:%i:%s') AS created_at,
            DATE_FORMAT(uf.created_at, '%d-%m-%Y') AS created_date,
            uf.updated_at

        FROM uploaded_files uf
        WHERE uf.created_by = p_created_by
          AND uf.session_id = p_session_id
        -- ORDER BY uf.created_at DESC;
        ORDER BY  COALESCE(uf.updated_at, uf.created_at) DESC;


    END
    """)

    # ============================================================
    # sp_insert_uploaded_file
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_insert_uploaded_file")
    c.execute("""
    CREATE PROCEDURE sp_insert_uploaded_file(
            IN p_session_id VARCHAR(100),
            IN p_file_name VARCHAR(255),
            IN p_table_name VARCHAR(255),
            IN p_file_size_mb VARCHAR(255),
            IN p_file_type VARCHAR(20),
            IN p_actual_rows INT,
            IN p_actual_columns INT,
            IN p_total_rows INT,
            IN p_total_columns INT,
            IN p_created_by VARCHAR(100),
            IN p_table_status VARCHAR(20),
            IN p_column_status VARCHAR(20),
            IN p_insights LONGTEXT,
            IN p_insights_status VARCHAR(20),
            IN p_data_insert_status VARCHAR(20),
            IN p_last_inserted_rows INT
        )
        proc_main: BEGIN

            DECLARE v_pending_id INT DEFAULT NULL;

            /* ------------------------------------------------
            STEP 1: Find pending row (table created, no data yet)
            ------------------------------------------------ */
            SELECT id
            INTO v_pending_id
            FROM uploaded_files
            WHERE session_id = p_session_id
            AND table_name = p_table_name
            AND data_insert_status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1;

            /* ------------------------------------------------
            STEP 2: FIRST DATA INSERT → UPDATE pending row
            ------------------------------------------------ */
            IF v_pending_id IS NOT NULL AND p_data_insert_status = 'done' THEN

                UPDATE uploaded_files
                SET
                    file_name = p_file_name,
                    file_size_mb = p_file_size_mb,
                    actual_rows = p_actual_rows,
                    actual_columns = p_actual_columns,
                    total_rows = p_total_rows,
                    total_columns = p_total_columns,
                    last_inserted_rows = p_last_inserted_rows,
                    insights = p_insights,
                    data_insights_status = p_insights_status,
                    data_insert_status = 'done',
                    updated_at = NOW()
                WHERE id = v_pending_id;

                SELECT v_pending_id AS file_id, 'UPDATED' AS status_flag;
                LEAVE proc_main;
            END IF;

            /* ------------------------------------------------
            STEP 3: INSERT NEW ROW
            - Table create
            - OR re-insert history
            ------------------------------------------------ */
            INSERT INTO uploaded_files (
                session_id,
                file_name,
                table_name,
                file_size_mb,
                file_type,
                actual_rows,
                actual_columns,
                total_rows,
                total_columns,
                last_inserted_rows,
                created_by,
                created_at,
                table_extraction_status,
                column_extraction_status,
                insights,
                data_insights_status,
                data_insert_status
            )
            VALUES (
                p_session_id,
                p_file_name,
                p_table_name,
                p_file_size_mb,
                p_file_type,
                p_actual_rows,
                p_actual_columns,
                p_total_rows,
                p_total_columns,
                p_last_inserted_rows,
                p_created_by,
                NOW(),
                p_table_status,
                p_column_status,
                p_insights,
                p_insights_status,
                p_data_insert_status
            );

            SELECT LAST_INSERT_ID() AS file_id, 'NEW' AS status_flag;
    END
    """)

    # ============================================================
    # sp_save_or_update_report
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_save_or_update_report")
    c.execute("""
    CREATE PROCEDURE sp_save_or_update_report(
           IN p_report_id VARCHAR(100),
        IN p_session_id VARCHAR(100),
        IN p_user_id VARCHAR(100),
        IN p_report_name VARCHAR(255),
        IN p_query_history_id INT,
        IN p_row_affected INT,
        OUT p_action VARCHAR(20)   -- INSERT / UPDATE / EXISTS
    )
    BEGIN
        DECLARE v_existing_query INT;
        DECLARE v_existing_name VARCHAR(255); -- new

        
        SELECT query_history_id, report_name
        INTO v_existing_query, v_existing_name

        FROM saved_reports
        WHERE report_id = p_report_id
        AND session_id = p_session_id
        AND user_id = p_user_id
        LIMIT 1;

        -- CASE 1: No report → INSERT
        IF v_existing_query IS NULL THEN

            INSERT INTO saved_reports
            (report_id, session_id, user_id, report_name, query_history_id, row_affected)
            VALUES
            (p_report_id, p_session_id, p_user_id, p_report_name, p_query_history_id, p_row_affected);

            SET p_action = 'INSERT';

        -- CASE 2: Same query → EXISTS
       
       ELSEIF v_existing_query = p_query_history_id
       AND v_existing_name = p_report_name THEN
       SET p_action = 'EXISTS';


        -- CASE 3: Different query → UPDATE
        ELSE
            UPDATE saved_reports
            SET
                report_name = p_report_name,
                query_history_id = p_query_history_id,
                row_affected = p_row_affected,
                updated_at = NOW()
            WHERE report_id = p_report_id
            AND session_id = p_session_id
            AND user_id = p_user_id;

            SET p_action = 'UPDATE';
        END IF;

    END
    """)

    # ============================================================
    # sp_save_query
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_save_query")
    c.execute("""
    CREATE PROCEDURE sp_save_query(
        IN p_session_id VARCHAR(100),
        IN p_created_by VARCHAR(100),
        IN p_query_title VARCHAR(150),

        IN p_message_query_id BIGINT,
        IN p_user_query TEXT,
        IN p_ai_response LONGTEXT,
        IN p_executable_sql LONGTEXT,
        IN p_table_names JSON,

        IN p_is_execute TINYINT,
        IN p_is_success TINYINT,
        IN p_row_count INT,
        IN p_query_time VARCHAR(50),

        IN p_mode VARCHAR(20),
        IN p_parent_query_id INT
    )
    BEGIN
        INSERT INTO query_history (
            session_id,
            created_by,
            query_title,
            message_query_id,
            user_query,
            ai_response,
            executable_sql,
            table_names,
            is_execute,
            is_success,
            row_count,
            query_time,
            mode,
            version_no,
            parent_query_id,
            is_latest,
            created_at
        )
        VALUES (
            p_session_id,
            p_created_by,
            p_query_title,
            p_message_query_id,
            p_user_query,
            p_ai_response,
            p_executable_sql,
            p_table_names,
            p_is_execute,
            p_is_success,
            p_row_count,
            p_query_time,
            'NEW',
            1,
            p_parent_query_id,
            1,
            NOW()
        );

        SELECT LAST_INSERT_ID() AS saved_id;
    END
    """)



    # ============================================================
    # sp_refresh_query_row_counts
    # ============================================================
    c.execute("DROP PROCEDURE IF EXISTS sp_refresh_query_row_counts")
    c.execute("""
        CREATE PROCEDURE sp_refresh_query_row_counts()
        BEGIN
            DECLARE done INT DEFAULT 0;
            DECLARE v_query_id INT;
            DECLARE v_sql LONGTEXT;
            DECLARE v_row_count INT;

            DECLARE cur CURSOR FOR
                SELECT id, executable_sql
                FROM query_history
                WHERE executable_sql IS NOT NULL
                AND is_execute = 1
                AND is_latest = 1;

            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

            -- TEMP TABLE must be created AFTER DECLAREs
            DROP TEMPORARY TABLE IF EXISTS tmp_cnt;
            CREATE TEMPORARY TABLE tmp_cnt (cnt INT);

            OPEN cur;

            read_loop: LOOP
                FETCH cur INTO v_query_id, v_sql;
                IF done = 1 THEN
                    LEAVE read_loop;
                END IF;

                DELETE FROM tmp_cnt;

                SET @dyn_sql = CONCAT(
                    'INSERT INTO tmp_cnt ',
                    'SELECT COUNT(*) FROM (', v_sql, ') t'
                );

                PREPARE stmt FROM @dyn_sql;
                EXECUTE stmt;
                DEALLOCATE PREPARE stmt;

                SELECT cnt INTO v_row_count FROM tmp_cnt LIMIT 1;

                UPDATE query_history
                SET row_count = v_row_count,
                    updated_at = NOW()
                WHERE id = v_query_id;

                UPDATE saved_reports
                SET row_affected = v_row_count,
                    updated_at = NOW()
                WHERE query_history_id = v_query_id;
            END LOOP;

            CLOSE cur;
            DROP TEMPORARY TABLE IF EXISTS tmp_cnt;
        END
    """)

# ==========================================================
# SUPER ADMIN → COMPANY REGISTER CONTROLLER
# ==========================================================
def admin_company_register_controller():
    try:
        # data = request.get_json()

        # company_name = data.get("company_name")
        # # company_code = data.get("company_code")
        # company_email = data.get("company_email")
        # address = data.get("address")
        # subscription_type = data.get("subscription_type")
        # from_date = data.get("from_date")
        # to_date = data.get("to_date")

        # if not company_name or  not company_email:
        #     return build_response(False, "Required fields missing", 400)

# 🔹 FORM DATA
        company_name = request.form.get("company_name")
        company_email = request.form.get("company_email")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        subscription_type = request.form.get("subscription_type")
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")

        logo_file = request.files.get("company_logo")
        print("FORM DATA =>", request.form)

        if not company_name or not company_email or not phone_number:
            return build_response(False, "Required fields missing", 400)

        # 🔒 LOGO VALIDATION
        logo_path = None
        if logo_file:
            if not allowed_logo(logo_file.filename):
                return build_response(False, "Only PNG/JPEG allowed", 400)

            if len(logo_file.read()) > MAX_LOGO_SIZE:
                return build_response(False, "Logo must be < 2MB", 400)

            logo_file.seek(0)  # VERY IMPORTANT

        master = get_master_db()
        master_cursor = master.cursor(dictionary=True)
        # compute company code
        company_code = generate_company_code(company_name, master_cursor)
        company_db_name = f"sahaj_cmp_{company_code}"

        # check duplicate company
        # master_cursor.execute(
        #     "SELECT id FROM companies WHERE company_code=%s",
        #     (company_code,)
        # )
        # if master_cursor.fetchone():
        #     return build_response(False, "Company already exists", 400)
        master_cursor.execute("""
        SELECT id FROM companies
        WHERE company_name = %s
        AND YEAR(created_at) = YEAR(CURDATE())
        """, (company_name,))
        if master_cursor.fetchone():
            return build_response(False, "Company already registered this year", 400)

        # insert company
        master_cursor.execute("""
            INSERT INTO companies
            (company_name, company_code, company_email, phone_number, address,
             subscription_type, from_date, to_date, company_db_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
           company_name,
            company_code,
            company_email,
            phone_number,
            address,
            subscription_type,
            from_date,
            to_date,
            company_db_name
        ))
        master.commit()
        company_id = master_cursor.lastrowid
       # 🔹 SAVE LOGO
        if logo_file:
            company_folder = os.path.join(
                UPLOAD_FOLDER,
                "companies",
                company_db_name,
                "logo"
            )
            os.makedirs(company_folder, exist_ok=True)

            ext = secure_filename(logo_file.filename).rsplit(".", 1)[1].lower()
            filename = f"logo.{ext}"

            full_path = os.path.join(company_folder, filename)
            logo_file.save(full_path)

            # ✅ UI-FRIENDLY PATH (RELATIVE URL)
            logo_path = f"/uploads/companies/{company_db_name}/logo/{filename}"

            master_cursor.execute("""
                UPDATE companies
                SET company_logo=%s
                WHERE id=%s
            """, (logo_path, company_id))

            master.commit()

        # create company database
        master_cursor.execute(f"CREATE DATABASE `{company_db_name}`")
        master.commit()

        master_cursor.close()
        master.close()

        # ==================================================
        # CREATE COMPANY TABLES
        # ==================================================
        company_conn = mysql.connector.connect(
            host=MASTER_DB_HOST,
            user=MASTER_DB_USER,
            password=MASTER_DB_PASS,
            database=company_db_name
        )
        c = company_conn.cursor()

               # ---------------- USER ROLES ----------------
        c.execute("""
CREATE TABLE IF NOT EXISTS user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Default roles
        c.execute("""
        INSERT IGNORE INTO user_roles (id, role_name)
        VALUES
        (1, 'companyadmin'),
        (2, 'user')
""")

    # Insert default Admin role
    #     c.execute("""
    # INSERT IGNORE INTO user_roles (id, role_name)
    # VALUES (1, 'Admin')
    # """)

    # ---------------- USERS ----------------
        # ---------------- USERS (COMPANY DB) ----------------
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id VARCHAR(50) UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    app_role_id INT NOT NULL,
    company_id INT NOT NULL,

    session_id VARCHAR(36),

    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_by VARCHAR(50),
    updated_at DATETIME DEFAULT NULL
)
""")
    
    # ---------------- UPLOADED FILES ----------------
        c.execute("""
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(100),
        file_name VARCHAR(255),
        table_name VARCHAR(255),
        file_size_mb varchar(100),
        file_type VARCHAR(20),

        actual_rows INT,
        actual_columns INT,
        total_rows INT,
        total_columns INT,
        last_inserted_rows INT DEFAULT 0,

        created_by VARCHAR(100),
        updated_by VARCHAR(100),

        insights LONGTEXT,

        table_extraction_status VARCHAR(20),
        column_extraction_status VARCHAR(20),
        data_insights_status VARCHAR(20),
        data_insert_status VARCHAR(20),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NULL
    )
    """)

    # ---------------- QUERY HISTORY ----------------
        c.execute("""
    CREATE TABLE IF NOT EXISTS query_history (
           id INT AUTO_INCREMENT PRIMARY KEY,

            session_id VARCHAR(100) NOT NULL,
            created_by VARCHAR(100) NOT NULL,

            query_title VARCHAR(150),
            message_query_id BIGINT,          

            user_query TEXT,
            ai_response LONGTEXT,
            executable_sql LONGTEXT,
            table_names JSON,

            is_execute TINYINT DEFAULT 0,
            is_success TINYINT DEFAULT 0,
            row_count INT DEFAULT 0,
            query_time VARCHAR(50),

            mode VARCHAR(20),                 
            version_no INT DEFAULT 1,
            parent_query_id INT NULL,
            is_latest TINYINT DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL,
            updated_by VARCHAR(100) NULL
        )
        """)

    # ---------------- SAVED REPORTS ----------------
        c.execute("""
    CREATE TABLE IF NOT EXISTS saved_reports (
        id INT AUTO_INCREMENT PRIMARY KEY,
        report_id VARCHAR(100),
        report_name VARCHAR(255),
        query_history_id INT,
        row_affected INT,

        user_id VARCHAR(100),
        session_id VARCHAR(100),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NULL
    )
    """)
        company_conn.commit()
        c.close()
        company_conn.close()

        # CREATE STORED PROCEDURES
        create_stored_procedures(company_db_name)

        return build_response(
            True,
            "Company registered successfully",
            200,
            extra={"company_db": company_db_name}
        )

    except Exception as e:
        return build_response(False, "Server error", 500, data={"error": str(e)})
