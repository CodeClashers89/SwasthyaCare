from django.apps import AppConfig
import threading
import time
import os
import sys

class HospitalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hospital'

def run_scheduler():
    """Background task to send reminders periodically"""
    from django.core.management import call_command
    
    # Wait for server to fully start
    time.sleep(10)
    
    while True:
        try:
            # Run the reminder command
            # For production this should run once a day, e.g. check time
            # For now, we run it every hour (3600 seconds)
            # You can change this interval as needed
            call_command('send_appointment_reminders')
            
            # Sleep for 1 hour
            time.sleep(3600)
            
        except Exception as e:
            print(f"Scheduler Error: {e}")
            time.sleep(60)  # Retry after 1 minute on error

class HospitalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hospital'

    def ready(self):
        # Only check runserver. This prevents it from running during migrations etc.
        # 'runserver' is in sys.argv for the dev server
        
        # Also need to check RUN_MAIN for the autoreloader to prevent double threads
        # Django's reloader runs two processes. RUN_MAIN is set in the child process.
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            print("Background scheduler started...")
