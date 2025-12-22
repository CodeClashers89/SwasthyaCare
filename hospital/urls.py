from django.urls import path
from . import views

app_name = 'hospital'

urlpatterns = [
    # Authentication
    path('', views.start, name='start'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
    
    # Doctor URLs
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/patient/<int:patient_id>/history/', views.patient_history, name='patient_history'),
    path('doctor/appointment/<int:appointment_id>/add-record/', views.add_medical_record, name='add_medical_record'),
    path('doctor/medical-record/<int:record_id>/download-pdf/', views.download_medical_record_pdf, name='download_medical_record_pdf'),
    path('doctor/appointment/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('doctor/appointment/<int:appointment_id>/follow-up/', views.create_follow_up, name='create_follow_up'),
    path('doctor/availability/', views.manage_availability, name='manage_availability'),
    path('doctor/availability/<int:availability_id>/delete/', views.delete_availability, name='delete_availability'),
    
    # Doctor URLs - Urgent Surgery
    path('doctor/surgery/create/', views.create_urgent_surgery_doctor, name='create_urgent_surgery_doctor'),
    path('doctor/surgery/pending/', views.view_pending_surgeries, name='view_pending_surgeries'),
    path('doctor/surgery/<int:surgery_id>/approve/', views.approve_surgery, name='approve_surgery'),
    path('doctor/surgery/<int:surgery_id>/reschedule/', views.bulk_reschedule_appointments, name='bulk_reschedule_appointments'),
    path('doctor/surgeries/', views.view_surgeries, name='view_surgeries'),
    
    # Receptionist URLs
    path('receptionist/dashboard/', views.receptionist_dashboard, name='receptionist_dashboard'),
    path('receptionist/register-patient/', views.register_patient, name='register_patient'),
    path('receptionist/appointments/', views.receptionist_appointments, name='receptionist_appointments'),
    path('receptionist/appointment/create/', views.create_appointment, name='create_appointment'),
    path('receptionist/appointment/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('receptionist/appointment/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    
    # Receptionist URLs - Urgent Surgery
    path('receptionist/surgery/create/', views.create_urgent_surgery_receptionist, name='create_urgent_surgery_receptionist'),
    
    # Patient URLs
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/doctor-availability/', views.check_doctor_availability, name='check_doctor_availability'),
    
    # Notification URLs (accessible to all logged-in users)
    path('notifications/', views.view_notifications, name='view_notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Admin Panel URLs (using 'panel' prefix to avoid conflict with Django admin)
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/create-doctor/', views.create_doctor, name='create_doctor'),
    path('panel/create-receptionist/', views.create_receptionist, name='create_receptionist'),
    path('panel/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
]
