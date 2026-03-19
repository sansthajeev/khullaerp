from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_request_received_email(email, company_name):
    try:
        subject = f"Registration Request Received - {company_name}"
        message = f"Hello,\n\nThank you for requesting an ERP workspace for {company_name}. Our team is reviewing your request and will get back to you shortly.\n\nBest regards,\nNeponbiz Team"
        print(f"DEBUG: Attempting to send Request Received email to {email}")
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        print(f"DEBUG: Request Received email sent to {email}")
    except Exception as e:
        print(f"DEBUG: Request Received email failed: {str(e)}")

@shared_task
def send_admin_notification_email(company_name, subdomain):
    try:
        subject = f"New Tenant Request: {company_name}"
        message = f"A new ERP tenant request has been submitted for {company_name} (Subdomain: {subdomain}).\n\nPlease login to the SaaS Admin panel to review and approve."
        print(f"DEBUG: Attempting to send Admin Notification for {company_name}")
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER], fail_silently=False)
        print(f"DEBUG: Admin Notification email sent")
    except Exception as e:
        print(f"DEBUG: Admin Notification email failed: {str(e)}")

@shared_task
def send_approval_email(email, company_name, subdomain, username, password):
    try:
        login_url = f"http://{subdomain}.localhost:8000/login/" # Update for production
        subject = f"Your ERP Workspace is Ready - {company_name}"
        message = f"Congratulations!\n\nYour ERP workspace for {company_name} has been approved and is now active.\n\nAccess Link: {login_url}\nUsername: {email}\nTemporary Password: {password}\n\n(Internal Username: {username})\n\nPlease change your password after your first login.\n\nBest regards,\nNeponbiz Team"
        print(f"DEBUG: Attempting to send Approval email to {email}")
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        print(f"DEBUG: Approval email sent to {email}")
    except Exception as e:
        print(f"DEBUG: Approval email failed: {str(e)}")
