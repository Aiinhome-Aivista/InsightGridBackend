from datetime import datetime

def company_registered_email(data):
    subject = f"{data['company_name']} Successfully Registered | Sahajinsight"

    today = datetime.now().strftime("%d %B %Y")

    html = f"""
    <div style="font-family: Arial, sans-serif; line-height:1.6; color:#333;">

        <h2 style="color:#2c3e50;">
             Company Registration Successful
        </h2>

        <p>
            Hello <b>{data['company_name']}</b> Team,
        </p>

        <p>
            We are happy to inform you that your company
            <b>{data['company_name']}</b> has been
            <b>successfully registered</b> on the
            <b>Sahajinsight Platform</b>.
        </p>

        <p>
            Here are the key details of your registration:
        </p>

        <p>
            🔹 <b>Company Code:</b> {data['company_code']}<br/>
            🔹 <b>Registered Email:</b> {data['company_email']}<br/>
            🔹 <b>Contact Number:</b> {data['phone_number']}<br/>
            🔹 <b>Subscription Plan:</b> {data['subscription_type']}<br/>
            🔹 <b>Subscription Validity:</b>
            {data['from_date']} <b>to</b> {data['to_date']}
        </p>

        <p>
          Our team will now proceed with creating the
    <b>Company Administrator</b> account for your organization.
    You will receive a separate email containing the administrator
    login details once the setup is completed.
        </p>

        <p>
            If you need any assistance, feel free to reach out to our
            support team.
        </p>

        <br/>

        <p style="font-size: 13px; color:#666;">
            Registered on {today}<br/>
            <b>Regards,</b><br/>
            Sahajinsight Team
        </p>

    </div>
    """

    return subject, html



def company_admin_created_company_mail(data):
    subject = f"Company Administrator Created | {data['company_name']}"

    today = datetime.now().strftime("%d %B %Y")

    html = f"""
    <div style="font-family:Arial,sans-serif; line-height:1.6; color:#333;">

        <h3>Company Administrator Setup Completed</h3>

        <p>
            This is to inform you that a
            <b>Company Administrator</b> has been successfully created
            for <b>{data['company_name']}</b>.
        </p>

        <p>
            <b>Administrator Name:</b> {data['admin_name']}<br/>
            <b>Administrator Email:</b> {data['admin_email']}
        </p>

        <p>
            The administrator will now be able to manage users and
            operations for your organization.
        </p>

        <p style="font-size:13px; color:#666;">
            Updated on {today}<br/>
            Regards,<br/>
            Sahajinsight Team
        </p>

    </div>
    """

    return subject, html


def company_admin_created_admin_mail(data):
    subject = f"Your Company Admin Login Details | {data['company_name']}"

    html = f"""
    <div style="font-family:Arial,sans-serif; line-height:1.6; color:#333;">

        <h3>Welcome to Sahajinsight</h3>

        <p>Hello <b>{data['admin_name']}</b>,</p>

        <p>
            You have been appointed as the
            <b>Company Administrator</b> for
            <b>{data['company_name']}</b>.
        </p>

        <p>
            As a Company Administrator, you will now be able to
            <b>access and manage your organization’s workspace</b>,
            including creating and managing users within your company.
        </p>

        <p><b>Login Credentials:</b></p>

        <p>
            🔹 <b>Login URL:</b>
            <a href="{data['login_url']}" target="_blank">
                {data['login_url']}
            </a>
        </p>

        <p>
            🔹 <b>Email:</b> {data['admin_email']}<br/>
            🔹 <b>Password:</b> {data['admin_password']}<br/>
            🔹 <b>Company Code:</b> {data['company_code']}
        </p>

        <p style="color:#b30000;">
            For security reasons, please change your password
            immediately after logging in.
        </p>

        <p>
            Once logged in, you can start by creating users and
            assigning appropriate roles to manage daily operations
            within your organization.
        </p>

        <p>
            If you face any issues, please contact the Super Administrator
            or our support team for assistance.
        </p>

        <p style="font-size:13px; color:#666;">
            Regards,<br/>
            Sahajinsight Team
        </p>

    </div>
    """

    return subject, html


def company_user_created_mail(data):
    subject = f"Your Login Details | {data['company_name']}"

    html = f"""
    <div style="font-family:Arial,sans-serif; line-height:1.6; color:#333;">

        <p>Hello <b>{data['user_name']}</b>,</p>

        <p>
            You have been added as a user to
            <b>{data['company_name']}</b> on the Sahajinsights platform.
        </p>

        <p><b>Your login details:</b></p>

        <p>
            🔹 <b>Login URL:</b>
            <a href="{data['login_url']}" target="_blank">
                {data['login_url']}
            </a>
        </p>

        <p>
            🔹 <b>Email:</b> {data['user_email']}<br/>
            🔹 <b>Password:</b> {data['user_password']}
        </p>

        <p>
            You can now log in to view dashboards and access
            insights shared with you by your administrator.
        </p>

        <p style="color:#b30000;">
            Please change your password after first login.
        </p>

        <p style="font-size:13px; color:#666;">
            Regards,<br/>
            Sahajinsights Team
        </p>

    </div>
    """
    return subject, html
