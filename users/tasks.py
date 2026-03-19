import os
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_verification_email(user_id, domain):
    try:
        user = User.objects.get(pk=user_id)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verify_url = f"http://{domain}{reverse('users:verify_email', kwargs={'uidb64': uid, 'token': token})}"
        
        subject = "Verify your email - Neponbiz"
        message = f"Hello {user.first_name},\n\nPlease click the link below to verify your email address and complete your registration:\n\n{verify_url}\n\nThank you,\nNeponbiz Team"
        
        print(f"DEBUG: Attempting to send email to {user.email} via {settings.EMAIL_HOST}")
        send_mail(
            subject, 
            message, 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False  # Crucial for debugging
        )
        print(f"DEBUG: Email sent successfully to {user.email}")
    except User.DoesNotExist:
        print(f"DEBUG: User with ID {user_id} not found")
    except Exception as e:
        print(f"DEBUG: Email sending failed: {str(e)}")

@shared_task
def send_welcome_email(user_id, password, domain, company_name=None):
    try:
        user = User.objects.get(pk=user_id)
        login_url = f"http://{domain}/login/"
        
        subject = f"Welcome to Neponbiz - {company_name or 'ERP Platform'}"
        
        message = f"Hello {user.first_name or user.username},\n\n"
        if company_name:
            message += f"Your account for {company_name} is ready.\n\n"
        else:
            message += "Welcome to the Neponbiz ERP platform.\n\n"
            
        message += f"You can log in using the following details:\n"
        message += f"Login Link: {login_url}\n"
        message += f"Username: {user.email}\n"
        message += f"Password: {password}\n\n"
        message += "Please change your password after logging in for the first time.\n\n"
        message += "Best regards,\nNeponbiz Team"

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        print(f"DEBUG: Welcome email sent to {user.email}")
    except User.DoesNotExist:
        print(f"DEBUG: User {user_id} not found for welcome email")
    except Exception as e:
        print(f"DEBUG: Failed to send welcome email: {str(e)}")
