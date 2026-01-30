import json
import os
import smtplib
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler

from database.dbConnection import get_master_db, get_company_db
from helper.pdf_generator import generate_report_pdf
from dotenv import load_dotenv
load_dotenv()
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def build_report_payload(cur, schedule):
    """
    Build FINAL payload from:
    1. saved_reports.report_config
    2. query_history.executable_sql
    """

    # ---------- 1️ saved_reports ----------
    cur.execute("""
        SELECT report_config
        FROM saved_reports
        WHERE report_id=%s
          AND session_id=%s
        LIMIT 1
    """, (schedule["report_id"], schedule["user_session_id"]))

    sr = cur.fetchone()
    if not sr:
        raise Exception("Saved report not found")

    base_payload = (
        sr["report_config"]
        if isinstance(sr["report_config"], dict)
        else json.loads(sr["report_config"])
    )

    # ---------- 2️ query_history (LATEST SUCCESS QUERY) ----------
    cur.execute("""
        SELECT executable_sql, table_names
        FROM query_history
        WHERE session_id=%s
          AND is_execute=1
          AND is_success=1
          AND is_latest=1
        ORDER BY created_at DESC
        LIMIT 1
    """, (schedule["user_session_id"],))

    qh = cur.fetchone()
    if not qh or not qh.get("executable_sql"):
        raise Exception("Executable SQL not found in query_history")

    # ---------- 3️ FINAL PAYLOAD ----------
    payload = {
        "report_title": base_payload.get("report_title", "Scheduled Report"),
        "query": qh["executable_sql"],          #  MOST IMPORTANT
        "charts": base_payload.get("charts", []),
        "filters": base_payload.get("filters", []),
        "group_by": base_payload.get("group_by", []),
        "selected_columns": base_payload.get("selected_columns", []),
        "table_names": qh.get("table_names", [])
    }

    return payload
# -------------------------------------------------
# MAIL SENDER
def send_automated_email(schedule, pdf_buffer, filename, company_name, report_name):
    try:
        sender_email = SMTP_USER

        to_list = json.loads(schedule["recipient_to"])
        cc_list = json.loads(schedule.get("recipient_cc") or "[]")
        all_recipients = to_list + cc_list

        subject = "Scheduled Data Report – Sahajinsight"
        today_str = datetime.now().strftime("%d %b %Y")

        msg = MIMEMultipart("alternative")
        msg["From"] = f"Sahajinsight Reports <{sender_email}>"
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject

        html_body = f"""
         <html>
         <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
           <table width="100%" cellpadding="0" cellspacing="0">
             <tr>
               <td align="center">
                <table width="600" style="background:#ffffff; padding:25px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                  
                   <tr>
                     <td style="font-size:20px; font-weight:bold; color:#2c3e50;">
                       📊 Scheduled Data Report
                     </td>
                   </tr>

                   <tr><td style="height:15px;"></td></tr>

                   <tr>
                     <td style="font-size:14px; color:#333;">
                       Dear Team,<br><br>
                       Please find attached the scheduled data report generated automatically by
                       <b style="color:#0b5ed7;">Sahajinsight</b>.
                     </td>
                   </tr>

                   <tr><td style="height:20px;"></td></tr>

                   <tr>
                     <td>
                       <table width="100%" style="border:1px solid #e0e0e0; border-radius:6px;">
                         <tr style="background:#f1f5ff;">
                           <td colspan="2" style="padding:10px; font-weight:bold; color:#0b5ed7;">
                             Report Details
                           </td>
                         </tr>
                         <tr>
                           <td style="padding:8px; font-weight:bold;">Company</td>
                           <td style="padding:8px;">{company_name}</td>
                         </tr>
                         <tr style="background:#fafafa;">
                             <td style="padding:8px; font-weight:bold;">Report Name</td>
                             <td style="padding:8px;">{report_name}</td>
                         </tr>
                         <tr>
                           <td style="padding:8px; font-weight:bold;">Generated On</td>
                           <td style="padding:8px;">{today_str}</td>
                         </tr>
                       </table>
                     </td>
                   </tr>

                   <tr><td style="height:20px;"></td></tr>
                   <tr>
                     <td style="font-size:13px; color:#555;">
                       This report is <b>system-generated</b> and does not require any manual action.
                       <br><br>
                       For any questions or changes related to scheduling or report configuration,
                       please contact the system administrator.
                     </td>
                   </tr>

                   <tr><td style="height:25px;"></td></tr>

                   <tr>
                    <td style="font-size:12px; color:#888; border-top:1px solid #eaeaea; padding-top:10px;">
                       Regards,<br>
                       <b>Sahajinsight Reporting System</b><br>
                       <span style="font-style:italic;">This is an automated email – please do not reply</span>
                     </td>
                   </tr>

                 </table>
               </td>
             </tr>
           </table>
         </body>
         </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        part = MIMEBase("application", "pdf")
        part.set_payload(pdf_buffer.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"'
        )
        msg.attach(part)

        #  SMTP SSL
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(
                msg,
                from_addr=SMTP_USER,
                to_addrs=all_recipients
            )

        return True

    except Exception as e:
        print("Mail Error:", e)
        return False

 
def get_report_name_by_id(cur, report_id, session_id):
    cur.execute("""
        SELECT report_name
        FROM saved_reports
        WHERE report_id = %s
          AND session_id = %s
        LIMIT 1
    """, (report_id, session_id))

    row = cur.fetchone()
    return row["report_name"] if row and row.get("report_name") else "Scheduled Report"    
# -------------------------------------------------
# PROCESS ONE COMPANY DB
# -------------------------------------------------
def process_company_schedules(company_db_name,company_name):
    conn = get_company_db(company_db_name)
    cur = conn.cursor(dictionary=True)

    now = datetime.now()
    today = now.date()
    current_time = now.time().replace(second=0, microsecond=0)
    current_day = now.strftime("%A")  # Monday, Tuesday...

    # --- active schedules ---
    cur.execute("""
        SELECT *
        FROM report_schedules
        WHERE is_active = 1
    """)
    schedules = cur.fetchall()

    for schedule in schedules:
        try:
            # -------------------------------------------------
            # 1 Schedule time handling
            # -------------------------------------------------
            schedule_time_raw = schedule["schedule_time"]

            # MySQL TIME → python time
            if isinstance(schedule_time_raw, timedelta):
                schedule_time = (datetime.min + schedule_time_raw).time()
            else:
                schedule_time = schedule_time_raw

            scheduled_dt = datetime.combine(today, schedule_time)
            current_dt = datetime.combine(today, current_time)

            #  tolerance (safe)
            if abs((scheduled_dt - current_dt).total_seconds()) > 30:
                continue

            # -------------------------------------------------
            # 2 Duplicate protection (minute-level lock)
            # -------------------------------------------------
            if schedule["last_run"]:
                last_run_min = schedule["last_run"].replace(second=0, microsecond=0)
                if last_run_min == current_dt:
                    continue

            # -------------------------------------------------
            #Frequency check
            # -------------------------------------------------
            freq = schedule["frequency"].lower()
            selected_days = (schedule.get("selected_days") or "").split(",")

            should_send = (
                freq == "once" or
                freq == "daily" or
                (freq == "weekly" and current_day in selected_days) or
                (freq == "monthly" and now.day == schedule["created_at"].day) or
                (freq == "yearly" and
                 now.day == schedule["created_at"].day and
                 now.month == schedule["created_at"].month)
            )

            if not should_send:
                continue

            # -------------------------------------------------
            # Build FINAL payload (saved_reports + query_history)
            # -------------------------------------------------
            report_name = get_report_name_by_id(
                cur,
                schedule["report_id"],
                schedule["user_session_id"]
            )
            payload = build_report_payload(cur, schedule)
            payload["report_title"] = report_name

            # -------------------------------------------------
            #Lock BEFORE heavy operations (important)
            # -------------------------------------------------
            cur.execute(
                "UPDATE report_schedules SET last_run=%s WHERE id=%s",
                (now, schedule["id"])
            )
            conn.commit()

            # -------------------------------------------------
            # Generate PDF
            # -------------------------------------------------
            filename = generate_report_pdf(
                session_id=schedule["user_session_id"],
                payload=payload,
                company_db=conn
            )
           # Generate safe report name
            safe_report_name = (
                report_name
                .strip()
                .replace(" ", "_")
                .replace("/", "-")
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            new_filename = f"{safe_report_name}_{timestamp}.pdf"

            old_path = os.path.join("uploads", "reportpdf", filename)
            new_path = os.path.join("uploads", "reportpdf", new_filename)

            if os.path.exists(old_path):
                os.rename(old_path, new_path)

            filename = new_filename            #  FINAL filename
            pdf_buffer = open(new_path, "rb")  #  OPEN renamed file
            # -------------------------------------------------
            #  Send Mail
            # -------------------------------------------------
            mail_sent = False

            try:
                mail_sent = send_automated_email(
                    schedule,
                    pdf_buffer,
                    filename,
                    company_name,
                    report_name
                )
            finally:
                # 🔥 VERY IMPORTANT: file ALWAYS close
                pdf_buffer.close()

            if mail_sent:

                # once → deactivate
                if freq == "once":
                    cur.execute(
                        "UPDATE report_schedules SET is_active=0 WHERE id=%s",
                        (schedule["id"],)
                    )

                conn.commit()

                # 🧹 delete PDF ONLY if mail sent
                try:
                    if os.path.exists(new_path):
                        os.remove(new_path)
                except Exception as e:
                    print("PDF cleanup failed:", e)
            else:
                # optional log
                print("Mail failed, PDF retained for retry:", new_path)

        except Exception as e:
            print(" Schedule Error:", e)

    cur.close()
    conn.close()
# -------------------------------------------------
# MAIN SCHEDULER JOB (DYNAMIC COMPANY RESOLUTION)
# -------------------------------------------------
def scheduler_job():
    """
    1 master DB → companies
    2 each company DB → report_schedules
    """
    m_conn = get_master_db()
    m_cur = m_conn.cursor(dictionary=True)

    m_cur.execute("""
        SELECT company_db_name, company_name
        FROM companies
        WHERE is_active = 1 AND is_deleted = 0
    """)
    companies = m_cur.fetchall()

    m_cur.close()
    m_conn.close()

    for comp in companies:
        try:
            process_company_schedules(comp["company_db_name"],comp["company_name"])
        except Exception as e:
            print(" Company Scheduler Error:", e)


# -------------------------------------------------
# SCHEDULER STARTER
# -------------------------------------------------
def start_report_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=scheduler_job,
        trigger="interval",
        minutes=1,
        id="dynamic_report_scheduler",
        replace_existing=True
    )

    scheduler.start()
