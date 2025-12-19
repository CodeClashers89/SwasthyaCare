from django.urls import path
from . import views

app_name = 'hospital'

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
    
    # Doctor URLs
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/patient/<int:patient_id>/history/', views.patient_history, name='patient_history'),
    path('doctor/appointment/<int:appointment_id>/add-record/', views.add_medical_record, name='add_medical_record'),
    path('doctor/appointment/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('doctor/appointment/<int:appointment_id>/follow-up/', views.create_follow_up, name='create_follow_up'),
    path('doctor/availability/', views.manage_availability, name='manage_availability'),
    path('doctor/availability/<int:availability_id>/delete/', views.delete_availability, name='delete_availability'),
    
    # Receptionist URLs
    path('receptionist/dashboard/', views.receptionist_dashboard, name='receptionist_dashboard'),
    path('receptionist/register-patient/', views.register_patient, name='register_patient'),
    path('receptionist/appointments/', views.receptionist_appointments, name='receptionist_appointments'),
    path('receptionist/appointment/create/', views.create_appointment, name='create_appointment'),
    path('receptionist/appointment/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('receptionist/appointment/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    
    # Patient URLs
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/doctor-availability/', views.check_doctor_availability, name='check_doctor_availability'),
]
