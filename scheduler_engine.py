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




# -------------------------------------------------
# MAIL SENDER
# -------------------------------------------------
def send_automated_email(schedule, pdf_buffer, filename):
    try:
        sender_email = "sahajinsightssoluation@gmail.com"
        sender_password = "fjcy vars xpzq nuat"  # Gmail App Password

        msg = MIMEMultipart()
        msg["From"] = f"InsightGrid Reports <{sender_email}>"

        to_list = json.loads(schedule["recipient_to"])
        cc_list = json.loads(schedule.get("recipient_cc") or "[]")

        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        msg["Subject"] = schedule["mail_title"]
        msg.attach(
            MIMEText(
                schedule.get("mail_body") or "Please find the attached report.",
                "plain"
            )
        )

        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_buffer.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        msg.attach(part)

        all_recipients = to_list + cc_list

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, all_recipients, msg.as_string())

        return True

    except Exception as e:
        print(" Mail Error:", e)
        return False


# -------------------------------------------------
# PROCESS ONE COMPANY DB
# -------------------------------------------------
def process_company_schedules(company_db_name):
    conn = get_company_db(company_db_name)
    cur = conn.cursor(dictionary=True)

    now = datetime.now()
    today = now.date()
    current_time = now.time().replace(second=0, microsecond=0)
    current_day = now.strftime("%A")  # Monday, Tuesday...

    cur.execute("""
        SELECT *
        FROM report_schedules
        WHERE is_active = 1
    """)
    schedules = cur.fetchall()

    for schedule in schedules:
        try:
            schedule_time_raw = schedule["schedule_time"]

# 🛠 MySQL TIME → python conversion fix
            if isinstance(schedule_time_raw, timedelta):
                schedule_time = (
                datetime.min + schedule_time_raw
                ).time()
            else:
                schedule_time = schedule_time_raw

            scheduled_dt = datetime.combine(today, schedule_time)
            current_dt = datetime.combine(today, current_time)

# ⏱ ±60 sec tolerance
            if abs((scheduled_dt - current_dt).total_seconds()) > 60:
                continue


            #  duplicate protection
            if schedule["last_run"] and schedule["last_run"].date() == today:
                continue

            freq = schedule["frequency"].lower()
            selected_days = (schedule.get("selected_days") or "").split(",")

            should_send = False

            if freq == "once":
                should_send = True
            elif freq == "daily":
                should_send = True
            elif freq == "weekly" and current_day in selected_days:
                should_send = True
            elif freq == "monthly" and now.day == schedule["created_at"].day:
                should_send = True
            elif freq == "yearly" and (
                now.day == schedule["created_at"].day and
                now.month == schedule["created_at"].month
            ):
                should_send = True

            if not should_send:
                continue

            print(
                f" Generating report {schedule['report_id']} "
                f"for company DB {company_db_name}"
            )

            # 1️ report payload আনো
            cur.execute("""
    SELECT report_config
    FROM saved_reports
    WHERE report_id=%s
      AND session_id=%s
    LIMIT 1
            """, (schedule["report_id"], schedule["user_session_id"]))

            row = cur.fetchone()
            if not row:
                raise Exception("Report config not found")

            # payload = row["report_config"]
            payload = (
                row["report_config"]
                if isinstance(row["report_config"], dict)
                else json.loads(row["report_config"])
            )


# 2️ PDF generate করো (CORRECT CALL)
            filename = generate_report_pdf(
                session_id=schedule["user_session_id"],
                payload=payload,
                company_db=conn
            )

# generate_report_pdf returns filename only
            pdf_buffer = open(
                os.path.join("uploads", "reportpdf", filename),
                "rb"
            )


            if send_automated_email(schedule, pdf_buffer, filename):
                cur.execute(
                    "UPDATE report_schedules SET last_run=%s WHERE id=%s",
                    (now, schedule["id"])
                )

                if freq == "once":
                    cur.execute(
                        "UPDATE report_schedules SET is_active=0 WHERE id=%s",
                        (schedule["id"],)
                    )

                conn.commit()
                print(" Mail sent successfully")

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
        SELECT company_db_name
        FROM companies
        WHERE is_active = 1 AND is_deleted = 0
    """)
    companies = m_cur.fetchall()

    m_cur.close()
    m_conn.close()

    for comp in companies:
        try:
            process_company_schedules(comp["company_db_name"])
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
    print(" Dynamic Report Scheduler Started")