from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from hospital.models import Appointment
from datetime import timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class Command(BaseCommand):
    help = 'Sends email reminders to patients 24 hours before their appointment'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Get all confirmed appointments for tomorrow
        appointments = Appointment.objects.filter(
            appointment_date=tomorrow,
            status='SCHEDULED',
            reminder_sent=False
        )
        
        self.stdout.write(f"Found {appointments.count()} appointments for tomorrow ({tomorrow})")
        
        success_count = 0
        failure_count = 0
        
        for appointment in appointments:
            try:
                if not appointment.patient.user.email:
                    self.stdout.write(self.style.WARNING(f"Skipping appointment {appointment.id}: Patient has no email"))
                    continue
                    
                subject = f'Appointment Reminder: Tomorrow at {appointment.appointment_time.strftime("%I:%M %p")}'
                # Prepare context for HTML email
                context = {
                    'patient_name': appointment.patient.user.get_full_name(),
                    'appointment_date': appointment.appointment_date.strftime("%B %d, %Y"),
                    'appointment_time': appointment.appointment_time.strftime("%I:%M %p"),
                    'doctor_name': appointment.doctor.user.get_full_name(),
                    'specialization': appointment.doctor.specialization,
                    # Hardcoded domain for local development, in production this should be in settings
                    'login_url': 'http://127.0.0.1:8000/',
                }
                
                html_message = render_to_string('hospital/email/appointment_reminder.html', context)
                plain_message = strip_tags(html_message)
                
                
                # Send email with timeout (60s as requested)
                from django.core.mail import get_connection
                connection = get_connection(timeout=60)  # 60 second timeout
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [appointment.patient.user.email],
                    fail_silently=False,
                    html_message=html_message,
                    connection=connection
                )
                
                success_count += 1
                appointment.reminder_sent = True
                appointment.save()
                self.stdout.write(self.style.SUCCESS(f"Sent reminder to {appointment.patient.user.email}"))
                
            except Exception as e:
                failure_count += 1
                self.stdout.write(self.style.ERROR(f"Failed to send email to appointment {appointment.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"Completed! Successfully sent: {success_count}, Failed: {failure_count}"
        ))
