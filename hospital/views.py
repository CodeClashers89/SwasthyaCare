from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, date, timedelta, time
from .models import (CustomUser, Patient, Doctor, Appointment, MedicalRecord, 
                     DoctorAvailability, UrgentSurgery, Notification, AppointmentReschedule)
from .forms import (PatientRegistrationForm, AppointmentForm, MedicalRecordForm, 
                    DoctorAvailabilityForm, RescheduleAppointmentForm, FollowUpAppointmentForm,
                    UrgentSurgeryForm, SurgeryApprovalForm, AppointmentRescheduleFormSingle,
                    DoctorRegistrationForm, ReceptionistRegistrationForm)
from .decorators import role_required
from django.db import IntegrityError


# Authentication Views
def start(request):
    return render(request, 'hospital/home.html')

def login_view(request):
    """Login view for all users"""
    if request.user.is_authenticated:
        return redirect('hospital:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('hospital:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'hospital/login.html')


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('hospital:login')


@login_required
def home_view(request):
    """Home view - redirects based on user role"""
    if request.user.role == 'DOCTOR':
        return redirect('hospital:doctor_dashboard')
    elif request.user.role == 'RECEPTIONIST':
        return redirect('hospital:receptionist_dashboard')
    elif request.user.role == 'PATIENT':
        return redirect('hospital:patient_dashboard')
    elif request.user.role == 'ADMIN':
        return redirect('hospital:admin_dashboard')
    elif request.user.is_superuser:
        return redirect('/admin/')
    else:
        return render(request, 'hospital/home.html')



# Doctor Views
@login_required
@role_required('DOCTOR')
def doctor_dashboard(request):
    """Doctor dashboard showing today's appointments"""
    doctor = request.user.doctor_profile
    today = date.today()
    
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today,
        status='SCHEDULED'
    ).order_by('appointment_time')
    
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__gt=today,
        status='SCHEDULED'
    ).order_by('appointment_date', 'appointment_time')[:5]
    
    # Get unread notifications count
    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Get pending surgery approvals count
    pending_surgeries_count = UrgentSurgery.objects.filter(
        doctor=doctor,
        status='PENDING'
    ).count()
    
    context = {
        'doctor': doctor,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'unread_notifications': unread_notifications,
        'pending_surgeries_count': pending_surgeries_count,
    }
    return render(request, 'hospital/doctor/dashboard.html', context)


@login_required
@role_required('DOCTOR')
def doctor_appointments(request):
    """View all doctor's appointments"""
    doctor = request.user.doctor_profile
    status_filter = request.GET.get('status', 'all')
    
    appointments = Appointment.objects.filter(doctor=doctor)
    
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter.upper())
    
    appointments = appointments.order_by('-appointment_date', '-appointment_time')
    
    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'doctor': doctor,
    }
    return render(request, 'hospital/doctor/appointments.html', context)


@login_required
@role_required('DOCTOR')
def patient_history(request, patient_id):
    """View patient's medical history"""
    patient = get_object_or_404(Patient, id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'medical_records': medical_records,
    }
    return render(request, 'hospital/doctor/patient_history.html', context)


@login_required
@role_required('DOCTOR')
def add_medical_record(request, appointment_id):
    """Add medical record for an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = request.user.doctor_profile
    
    # Verify this appointment belongs to the logged-in doctor
    if appointment.doctor != doctor:
        messages.error(request, 'You can only add records for your own appointments.')
        return redirect('hospital:doctor_appointments')
    
    # Get the action parameter (complete or followup)
    action = request.GET.get('action', '')
    
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES)
        if form.is_valid():
            medical_record = form.save(commit=False)
            medical_record.appointment = appointment
            medical_record.patient = appointment.patient
            medical_record.doctor = doctor
            medical_record.save()
            messages.success(request, 'Medical record added successfully.')
            
            # Check if we need to perform an action after saving
            action = request.POST.get('action', '')
            
            if action == 'complete':
                # Mark appointment as completed
                appointment.status = 'COMPLETED'
                appointment.save()
                messages.success(request, 'Appointment marked as completed.')
                return redirect('hospital:doctor_appointments')
            elif action == 'followup':
                # Redirect to follow-up creation page
                return redirect('hospital:create_follow_up', appointment_id=appointment.id)
            else:
                # Default: redirect back to appointments
                return redirect('hospital:doctor_appointments')
    else:
        form = MedicalRecordForm()
    
    # Check if a medical record already exists for this appointment
    existing_record = MedicalRecord.objects.filter(appointment=appointment).first()
    
    context = {
        'form': form,
        'appointment': appointment,
        'medical_record': existing_record,  # Pass existing record if available
        'doctor': doctor,  # Add doctor to context
        'action': action,  # Pass action to template
    }
    return render(request, 'hospital/doctor/add_record.html', context)



@login_required
@role_required('DOCTOR')
def update_appointment_status(request, appointment_id):
    """Update appointment status (complete/no-show)"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = request.user.doctor_profile
    
    if appointment.doctor != doctor:
        messages.error(request, 'You can only update your own appointments.')
        return redirect('hospital:doctor_appointments')
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['COMPLETED', 'NO_SHOW']:
            appointment.status = status
            appointment.save()
            messages.success(request, f'Appointment marked as {status.lower().replace("_", " ")}.')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('hospital:doctor_appointments')


@login_required
@role_required('DOCTOR')
def create_follow_up(request, appointment_id):
    """Create follow-up appointment"""
    parent_appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = request.user.doctor_profile
    
    if parent_appointment.doctor != doctor:
        messages.error(request, 'You can only create follow-ups for your own appointments.')
        return redirect('hospital:doctor_appointments')
    
    if request.method == 'POST':
        form = FollowUpAppointmentForm(request.POST)
        if form.is_valid():
            follow_up = form.save(commit=False)
            follow_up.patient = parent_appointment.patient
            follow_up.doctor = doctor
            follow_up.is_follow_up = True
            follow_up.parent_appointment = parent_appointment
            follow_up.created_by = request.user
            
            # Check doctor availability (both date-specific and recurring)
            app_date = follow_up.appointment_date
            app_time = follow_up.appointment_time
            
            # Check if appointment time is within hospital operating hours (9:00 AM to 8:00 PM)
            hospital_open = time(9, 0)  # 9:00 AM
            hospital_close = time(20, 0)  # 8:00 PM
            
            if app_time < hospital_open or app_time >= hospital_close:
                messages.error(request, 'Appointments can only be made between 9:00 AM and 8:00 PM.')
                return render(request, 'hospital/doctor/create_follow_up.html', 
                            {'form': form, 'parent_appointment': parent_appointment})
            
            unavailable = DoctorAvailability.objects.filter(
                Q(doctor=doctor, date=app_date, start_time__lte=app_time, end_time__gt=app_time) |
                Q(doctor=doctor, is_recurring=True, start_time__lte=app_time, end_time__gt=app_time)
            ).exists()
            
            if unavailable:
                messages.error(request, 'Doctor is not available at this time.')
                return render(request, 'hospital/doctor/create_follow_up.html', 
                            {'form': form, 'parent_appointment': parent_appointment})
            
            # Check for slot conflicts (15-minute slots)
            slot_start = get_slot_start(app_time)
            if slot_start.minute == 0:
                slot_end = time(slot_start.hour, 14)
            elif slot_start.minute == 15:
                slot_end = time(slot_start.hour, 29)
            elif slot_start.minute == 30:
                slot_end = time(slot_start.hour, 44)
            else:  # minute == 45
                slot_end = time(slot_start.hour, 59)
            
            # Check if there's already an appointment in this 15-minute slot
            slot_conflict = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=app_date,
                appointment_time__gte=slot_start,
                appointment_time__lte=slot_end,
                status='SCHEDULED'
            ).exists()
            
            if slot_conflict:
                messages.error(request, f'This time slot ({slot_start.strftime("%H:%M")}-{slot_end.strftime("%H:%M")}) is already booked.')
                return render(request, 'hospital/doctor/create_follow_up.html', 
                            {'form': form, 'parent_appointment': parent_appointment})
            
            follow_up.save()
            messages.success(request, 'Follow-up appointment created successfully.')
            return redirect('hospital:doctor_appointments')
    else:
        form = FollowUpAppointmentForm()
    
    context = {
        'form': form,
        'parent_appointment': parent_appointment,
    }
    return render(request, 'hospital/doctor/create_follow_up.html', context)


@login_required
@role_required('DOCTOR')
def manage_availability(request):
    """Manage doctor's availability (lunch breaks and unavailable times)"""
    doctor = request.user.doctor_profile
    
    if request.method == 'POST':
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.doctor = doctor
            availability.save()
            messages.success(request, 'Availability updated successfully.')
            return redirect('hospital:manage_availability')
    else:
        form = DoctorAvailabilityForm()
    
    # Get upcoming availability records (both recurring and date-specific)
    from django.db.models import Q
    availabilities = DoctorAvailability.objects.filter(
        Q(doctor=doctor, is_recurring=True) | 
        Q(doctor=doctor, date__gte=date.today())
    ).order_by('is_recurring', 'date', 'start_time')
    
    context = {
        'form': form,
        'availabilities': availabilities,
        'doctor': doctor,
    }
    return render(request, 'hospital/doctor/availability.html', context)


@login_required
@role_required('DOCTOR')
def delete_availability(request, availability_id):
    """Delete availability record"""
    availability = get_object_or_404(DoctorAvailability, id=availability_id)
    doctor = request.user.doctor_profile
    
    if availability.doctor != doctor:
        messages.error(request, 'You can only delete your own availability records.')
        return redirect('hospital:manage_availability')
    
    availability.delete()
    messages.success(request, 'Availability record deleted.')
    return redirect('hospital:manage_availability')

#Patient Views
@login_required
@role_required('PATIENT')
def patient_dashboard(request):
    """Patient dashboard with appointment history"""
    patient = request.user.patient_profile
    
    # Get appointment history
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-appointment_time')
    
    # Get medical records
    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'medical_records': medical_records,
    }
    return render(request, 'hospital/patient/dashboard.html', context)


@login_required
@role_required('PATIENT')
def check_doctor_availability(request):
    """Check doctor availability"""
    doctors = Doctor.objects.all().order_by('user__first_name')
    
    selected_doctor_id = request.GET.get('doctor')
    selected_date = request.GET.get('date')
    
    availability_info = None
    
    if selected_doctor_id and selected_date:
        try:
            doctor = Doctor.objects.get(id=selected_doctor_id)
            check_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            
            # Get unavailable times (both date-specific and recurring)
            unavailable_times = DoctorAvailability.objects.filter(
                Q(doctor=doctor, date=check_date) |
                Q(doctor=doctor, is_recurring=True)
            ).order_by('start_time')
            
            # Get booked appointments
            booked_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=check_date,
                status='SCHEDULED'
            ).order_by('appointment_time')
            
            availability_info = {
                'doctor': doctor,
                'date': check_date,
                'unavailable_times': unavailable_times,
                'booked_appointments': booked_appointments,
            }
        except (Doctor.DoesNotExist, ValueError):
            messages.error(request, 'Invalid doctor or date.')
    
    context = {
        'doctors': doctors,
        'selected_doctor_id': selected_doctor_id,
        'selected_date': selected_date,
        'availability_info': availability_info,
    }
    return render(request, 'hospital/patient/doctor_availability.html', context)

# Receptionist Views
@login_required
@role_required('RECEPTIONIST')
def receptionist_dashboard(request):
    """Receptionist dashboard"""
    today = date.today()
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).order_by('appointment_time')
    
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]
    
    context = {
        'today_appointments': today_appointments,
        'recent_patients': recent_patients,
    }
    return render(request, 'hospital/receptionist/dashboard.html', context)


@login_required
@role_required('RECEPTIONIST')
def register_patient(request):
    """Register new patient"""
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient registered successfully! Patient ID: {patient.patient_id}')
            return redirect('hospital:receptionist_dashboard')
    else:
        form = PatientRegistrationForm()
    
    context = {'form': form}
    return render(request, 'hospital/receptionist/register_patient.html', context)


@login_required
@role_required('RECEPTIONIST')
def receptionist_appointments(request):
    """View all appointments"""
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', 'all')
    
    appointments = Appointment.objects.all()
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            appointments = appointments.filter(appointment_date=filter_date)
        except ValueError:
            pass
    
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter.upper())
    
    appointments = appointments.order_by('-appointment_date', '-appointment_time')
    
    context = {
        'appointments': appointments,
        'date_filter': date_filter,
        'status_filter': status_filter,
    }
    return render(request, 'hospital/receptionist/appointments.html', context)

def get_slot_start(t):
    #return time(t.hour, 0 if t.minute < 30 else 30)
    if isinstance(t, str):
        t = datetime.strptime(t, "%H:%M:%S").time()

    return time(t.hour, (t.minute // 15) * 15)
#--------------------------------------------------------------------------------------------
# def generate_time_slots():
#         slots = []
#         hour = 9
#         minute = 0

#         while hour < 17:
#             slots.append(time(hour, minute).strftime("%H:%M"))
#             minute += 15
#             if minute == 60:
#                 minute = 0
#                 hour += 1

#         return slots


#--------------------------------------------------------------------------------------------
@login_required
@role_required('RECEPTIONIST')
def create_appointment(request):
    """Create new appointment"""
    slots = [
    "09:00","09:15","09:30","09:45",
    "10:00","10:15","10:30","10:45",
    "11:00","11:15","11:30","11:45",
    "12:00","12:15","12:30","12:45",
    "13:00","13:15","13:30","13:45",
    "14:00","14:15","14:30","14:45",
    "15:00","15:15","15:30","15:45",
    "16:00","16:15","16:30","16:45",
    "17:00","17:15","17:30","17:45",
    "18:00","18:15","18:30","18:45",
    "19:00","19:15","19:30","19:45",
    ]
    if request.method == 'POST':
        form = AppointmentForm(request.POST,slots=slots)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            #--------------------------------------------------------------
            doctor = form.cleaned_data['doctor']
            appointment_date = form.cleaned_data['appointment_date']
            appointment_time = form.cleaned_data['appointment_time']

            # Check if appointment time is within hospital operating hours (9:00 AM to 8:00 PM)
            hospital_open = time(9, 0)  # 9:00 AM
            hospital_close = time(20, 0)  # 8:00 PM
            
            if appointment_time < hospital_open or appointment_time >= hospital_close:
                messages.error(request, 'Appointments can only be made between 9:00 AM and 8:00 PM.')
                return render(request, 'hospital/receptionist/create_appointment.html', {'form': form})

            slot_start = get_slot_start(appointment_time)

            if slot_start.minute == 0:
                slot_end = time(slot_start.hour, 29)
            else:
                slot_end = time(slot_start.hour, 59)

            slot_count = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time__gte=slot_start,
                appointment_time__lte=slot_end,
                status='SCHEDULED',
                
            ).count()

            if slot_count >= 2:
                messages.error(request,"This time slot is full. Only 2 appointments are allowed per 30 minutes.")
                return render(
                    request,
                        'hospital/receptionist/create_appointment.html',
                        {'form': form}
                )
               #---------------------------------------------------------------
            # Check doctor availability
            doctor = appointment.doctor
            app_date = appointment.appointment_date
            app_time = appointment.appointment_time
            
            # Check if doctor has marked this time as unavailable (both date-specific and recurring)
            unavailable = DoctorAvailability.objects.filter(
                Q(doctor=doctor, date=app_date, start_time__lte=app_time, end_time__gt=app_time) |
                Q(doctor=doctor, is_recurring=True, start_time__lte=app_time, end_time__gt=app_time)
            ).exists()
            
            if unavailable:
                messages.error(request, 'Doctor is not available at this time.')
                return render(request, 'hospital/receptionist/create_appointment.html', {'form': form})
            
            # Check for if doctor already has appointments
            duplicate = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=app_date,
                appointment_time=app_time,
                status='SCHEDULED'
            ).exists()
            
            if duplicate:
                messages.error(request, 'This time slot is already booked.')
                return render(request, 'hospital/receptionist/create_appointment.html', {'form': form})
            
            appointment.save()
            messages.success(request, 'Appointment created successfully.')
            return redirect('hospital:receptionist_appointments')
    else:
        form = AppointmentForm(slots=slots)
    # slots = generate_time_slots()
    slots = slots
    context = {'form': form,'slots':slots}
    return render(request, 'hospital/receptionist/create_appointment.html', context)


@login_required
@role_required('RECEPTIONIST')
def reschedule_appointment(request, appointment_id):
    """Reschedule an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        form = RescheduleAppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_appointment = form.save(commit=False)
            
            # Check availability (both date-specific and recurring)
            doctor = updated_appointment.doctor
            app_date = updated_appointment.appointment_date
            app_time = updated_appointment.appointment_time
            
            # Check if appointment time is within hospital operating hours (9:00 AM to 8:00 PM)
            hospital_open = time(9, 0)  # 9:00 AM
            hospital_close = time(20, 0)  # 8:00 PM
            
            if app_time < hospital_open or app_time >= hospital_close:
                messages.error(request, 'Appointments can only be made between 9:00 AM and 8:00 PM.')
                return render(request, 'hospital/receptionist/reschedule_appointment.html', 
                            {'form': form, 'appointment': appointment})
            
            unavailable = DoctorAvailability.objects.filter(
                Q(doctor=doctor, date=app_date, start_time__lte=app_time, end_time__gt=app_time) |
                Q(doctor=doctor, is_recurring=True, start_time__lte=app_time, end_time__gt=app_time)
            ).exists()
            
            if unavailable:
                messages.error(request, 'Doctor is not available at this time.')
                return render(request, 'hospital/receptionist/reschedule_appointment.html', 
                            {'form': form, 'appointment': appointment})
            
            # Check for slot conflicts (15-minute slots)
            slot_start = get_slot_start(app_time)
            if slot_start.minute == 0:
                slot_end = time(slot_start.hour, 14)
            elif slot_start.minute == 15:
                slot_end = time(slot_start.hour, 29)
            elif slot_start.minute == 30:
                slot_end = time(slot_start.hour, 44)
            else:  # minute == 45
                slot_end = time(slot_start.hour, 59)
            
            # Check if there's already an appointment in this 15-minute slot (excluding current appointment)
            slot_conflict = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=app_date,
                appointment_time__gte=slot_start,
                appointment_time__lte=slot_end,
                status='SCHEDULED'
            ).exclude(id=appointment.id).exists()
            
            if slot_conflict:
                messages.error(request, f'This time slot ({slot_start.strftime("%H:%M")}-{slot_end.strftime("%H:%M")}) is already booked.')
                return render(request, 'hospital/receptionist/reschedule_appointment.html', 
                            {'form': form, 'appointment': appointment})
            
            updated_appointment.save()
            messages.success(request, 'Appointment rescheduled successfully.')
            return redirect('hospital:receptionist_appointments')
    else:
        form = RescheduleAppointmentForm(instance=appointment)
    
    context = {
        'form': form,
        'appointment': appointment,
    }
    return render(request, 'hospital/receptionist/reschedule_appointment.html', context)


@login_required
@role_required('RECEPTIONIST')
def cancel_appointment(request, appointment_id):
    """Cancel an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'CANCELLED'
    appointment.save()
    messages.success(request, 'Appointment cancelled successfully.')
    return redirect('hospital:receptionist_appointments')



# Urgent Surgery Views
@login_required
@role_required('DOCTOR')
def create_urgent_surgery_doctor(request):
    """Doctor creates urgent surgery (auto-approved)"""
    doctor = request.user.doctor_profile
    
    if request.method == 'POST':
        form = UrgentSurgeryForm(request.POST, user=request.user)
        if form.is_valid():
            surgery = form.save(commit=False)
            surgery.created_by = request.user
            surgery.status = 'APPROVED'  # Doctor's own surgeries are auto-approved
            surgery.approved_by = request.user
            surgery.save()
            
            # Check for conflicting appointments
            conflicting_appointments = surgery.get_conflicting_appointments()
            
            if conflicting_appointments.exists():
                messages.warning(request, f'Surgery created! You have {conflicting_appointments.count()} conflicting appointment(s) that need rescheduling.')
                return redirect('hospital:bulk_reschedule_appointments', surgery_id=surgery.id)
            else:
                messages.success(request, 'Urgent surgery scheduled successfully with no conflicts.')
                return redirect('hospital:doctor_dashboard')
    else:
        form = UrgentSurgeryForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'hospital/doctor/create_urgent_surgery.html', context)


@login_required
@role_required('RECEPTIONIST')
def create_urgent_surgery_receptionist(request):
    """Receptionist creates urgent surgery (requires doctor approval)"""
    if request.method == 'POST':
        form = UrgentSurgeryForm(request.POST, user=request.user)
        if form.is_valid():
            surgery = form.save(commit=False)
            surgery.created_by = request.user
            surgery.status = 'PENDING'  # Requires doctor approval
            surgery.save()
            
            # Create notification for the doctor
            Notification.objects.create(
                recipient=surgery.doctor.user,
                notification_type='SURGERY_APPROVAL_PENDING',
                title='Urgent Surgery Approval Required',
                message=f'Receptionist {request.user.get_full_name()} has scheduled an urgent surgery ({surgery.surgery_type}) on {surgery.surgery_date} from {surgery.start_time} to {surgery.end_time}. Please review and approve.',
                related_surgery=surgery
            )
            
            messages.success(request, f'Surgery request sent to Dr. {surgery.doctor.user.get_full_name()} for approval.')
            return redirect('hospital:receptionist_dashboard')
    else:
        form = UrgentSurgeryForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'hospital/receptionist/create_urgent_surgery.html', context)


@login_required
@role_required('DOCTOR')
def view_pending_surgeries(request):
    """Doctor views pending surgery approval requests"""
    doctor = request.user.doctor_profile
    
    pending_surgeries = UrgentSurgery.objects.filter(
        doctor=doctor,
        status='PENDING'
    ).order_by('surgery_date', 'start_time')
    
    # Add conflict count to each surgery
    for surgery in pending_surgeries:
        surgery.conflict_count = surgery.get_conflicting_appointments().count()
    
    context = {'pending_surgeries': pending_surgeries}
    return render(request, 'hospital/doctor/pending_surgeries.html', context)


@login_required
@role_required('DOCTOR')
def approve_surgery(request, surgery_id):
    """Doctor approves or rejects a surgery request"""
    surgery = get_object_or_404(UrgentSurgery, id=surgery_id)
    doctor = request.user.doctor_profile
    
    # Verify this surgery is for the logged-in doctor
    if surgery.doctor != doctor:
        messages.error(request, 'You can only approve surgeries assigned to you.')
        return redirect('hospital:view_pending_surgeries')
    
    if surgery.status != 'PENDING':
        messages.error(request, 'This surgery has already been processed.')
        return redirect('hospital:view_pending_surgeries')
    
    conflicting_appointments = surgery.get_conflicting_appointments()
    
    if request.method == 'POST':
        form = SurgeryApprovalForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            surgery.status = status
            surgery.approved_by = request.user
            
            if status == 'REJECTED':
                surgery.rejection_reason = form.cleaned_data['rejection_reason']
                surgery.save()
                
                # Notify receptionist of rejection
                Notification.objects.create(
                    recipient=surgery.created_by,
                    notification_type='SURGERY_REJECTED',
                    title='Surgery Request Rejected',
                    message=f'Dr. {request.user.get_full_name()} has rejected the surgery request for {surgery.surgery_type} on {surgery.surgery_date}. Reason: {surgery.rejection_reason}',
                    related_surgery=surgery
                )
                
                messages.success(request, 'Surgery request rejected.')
                return redirect('hospital:view_pending_surgeries')
            else:
                surgery.save()
                
                # Notify receptionist of approval
                Notification.objects.create(
                    recipient=surgery.created_by,
                    notification_type='SURGERY_APPROVED',
                    title='Surgery Request Approved',
                    message=f'Dr. {request.user.get_full_name()} has approved the surgery request for {surgery.surgery_type} on {surgery.surgery_date}.',
                    related_surgery=surgery
                )
                
                if conflicting_appointments.exists():
                    messages.success(request, f'Surgery approved! Please reschedule {conflicting_appointments.count()} conflicting appointment(s).')
                    return redirect('hospital:bulk_reschedule_appointments', surgery_id=surgery.id)
                else:
                    messages.success(request, 'Surgery approved with no conflicts.')
                    return redirect('hospital:view_pending_surgeries')
    else:
        form = SurgeryApprovalForm()
    
    context = {
        'form': form,
        'surgery': surgery,
        'conflicting_appointments': conflicting_appointments,
    }
    return render(request, 'hospital/doctor/approve_surgery.html', context)


@login_required
@role_required('DOCTOR')
def bulk_reschedule_appointments(request, surgery_id):
    """Doctor reschedules all conflicting appointments"""
    surgery = get_object_or_404(UrgentSurgery, id=surgery_id)
    doctor = request.user.doctor_profile
    
    # Verify this surgery is for the logged-in doctor
    if surgery.doctor != doctor:
        messages.error(request, 'You can only reschedule appointments for your own surgeries.')
        return redirect('hospital:doctor_dashboard')
    
    if surgery.status != 'APPROVED':
        messages.error(request, 'This surgery has not been approved yet.')
        return redirect('hospital:doctor_dashboard')
    
    conflicting_appointments = surgery.get_conflicting_appointments()
    
    if not conflicting_appointments.exists():
        messages.info(request, 'No conflicting appointments to reschedule.')
        return redirect('hospital:doctor_dashboard')
    
    if request.method == 'POST':
        all_valid = True
        reschedule_data = []
        
        # Validate all forms
        for appointment in conflicting_appointments:
            form = AppointmentRescheduleFormSingle(
                request.POST,
                prefix=f'appointment_{appointment.id}',
                appointment=appointment,
                doctor=doctor
            )
            if form.is_valid():
                new_date = form.cleaned_data['new_date']
                new_time = form.cleaned_data['new_time']
                
                # Check if appointment time is within hospital operating hours (9:00 AM to 8:00 PM)
                hospital_open = time(9, 0)
                hospital_close = time(20, 0)
                
                if new_time < hospital_open or new_time >= hospital_close:
                    all_valid = False
                    messages.error(request, f'Error with appointment for {appointment.patient.user.get_full_name()}: Appointments can only be made between 9:00 AM and 8:00 PM.')
                    continue
                
                # Check doctor availability (both date-specific and recurring)
                unavailable = DoctorAvailability.objects.filter(
                    Q(doctor=doctor, date=new_date, start_time__lte=new_time, end_time__gt=new_time) |
                    Q(doctor=doctor, is_recurring=True, start_time__lte=new_time, end_time__gt=new_time)
                ).exists()
                
                if unavailable:
                    all_valid = False
                    messages.error(request, f'Error with appointment for {appointment.patient.user.get_full_name()}: Doctor is not available at {new_time.strftime("%H:%M")} on {new_date}.')
                    continue
                
                # Check for slot conflicts (15-minute slots)
                slot_start = get_slot_start(new_time)
                if slot_start.minute == 0:
                    slot_end = time(slot_start.hour, 14)
                elif slot_start.minute == 15:
                    slot_end = time(slot_start.hour, 29)
                elif slot_start.minute == 30:
                    slot_end = time(slot_start.hour, 44)
                else:  # minute == 45
                    slot_end = time(slot_start.hour, 59)
                
                # Check if there's already an appointment in this 15-minute slot (excluding current appointment)
                slot_conflict = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=new_date,
                    appointment_time__gte=slot_start,
                    appointment_time__lte=slot_end,
                    status='SCHEDULED'
                ).exclude(id=appointment.id).exists()
                
                if slot_conflict:
                    all_valid = False
                    messages.error(request, f'Error with appointment for {appointment.patient.user.get_full_name()}: Time slot ({slot_start.strftime("%H:%M")}-{slot_end.strftime("%H:%M")}) is already booked.')
                    continue
                
                reschedule_data.append({
                    'appointment': appointment,
                    'new_date': new_date,
                    'new_time': new_time
                })
            else:
                all_valid = False
                messages.error(request, f'Error with appointment for {appointment.patient.user.get_full_name()}: {form.errors}')

        
        if all_valid:
            # Process all rescheduling
            for data in reschedule_data:
                appointment = data['appointment']
                
                # Create reschedule record
                AppointmentReschedule.objects.create(
                    appointment=appointment,
                    original_date=appointment.appointment_date,
                    original_time=appointment.appointment_time,
                    new_date=data['new_date'],
                    new_time=data['new_time'],
                    reason=f"Rescheduled due to urgent surgery: {surgery.surgery_type}",
                    urgent_surgery=surgery,
                    rescheduled_by=request.user
                )
                
                # Update appointment
                appointment.appointment_date = data['new_date']
                appointment.appointment_time = data['new_time']
                appointment.save()
                
                # Notify patient via in-app notification
                Notification.objects.create(
                    recipient=appointment.patient.user,
                    notification_type='APPOINTMENT_RESCHEDULED',
                    title='Appointment Rescheduled',
                    message=f'Your appointment with Dr. {doctor.user.get_full_name()} has been rescheduled from {data["new_date"]} at {data["new_time"]} due to an urgent surgery. We apologize for the inconvenience.',
                    related_appointment=appointment
                )
                
                # Send email notification to patient
                try:
                    from django.core.mail import EmailMultiAlternatives
                    from django.template.loader import render_to_string
                    from django.conf import settings
                    
                    patient_email = appointment.patient.user.email
                    
                    if patient_email:
                        # Prepare email context
                        reschedule_record = AppointmentReschedule.objects.filter(appointment=appointment).latest('created_at')
                        
                        email_context = {
                            'patient_name': appointment.patient.user.get_full_name(),
                            'doctor_name': doctor.user.get_full_name(),
                            'doctor_specialization': doctor.specialization,
                            'original_date': reschedule_record.original_date.strftime('%d %B %Y'),
                            'original_time': reschedule_record.original_time.strftime('%I:%M %p'),
                            'new_date': data['new_date'].strftime('%d %B %Y'),
                            'new_time': data['new_time'].strftime('%I:%M %p'),
                            'surgery_reason': f"Urgent surgery: {surgery.surgery_type}",
                        }
                        
                        # Render HTML email
                        html_content = render_to_string('hospital/emails/appointment_rescheduled.html', email_context)
                        
                        # Send email via Brevo SMTP
                        subject = 'Your Appointment Has Been Rescheduled - SwasthyaCare'
                        email = EmailMultiAlternatives(
                            subject=subject,
                            body=f"Dear {email_context['patient_name']},\n\nYour appointment has been rescheduled. Please see the details in the HTML version of this email.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[patient_email]
                        )
                        email.attach_alternative(html_content, "text/html")
                        email.send(fail_silently=True)
                        
                except Exception as e:
                    # Log error but don't block the reschedule process
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to send email to {appointment.patient.user.email}: {str(e)}")
            
            messages.success(request, f'Successfully rescheduled {len(reschedule_data)} appointment(s). Patients have been notified via email and in-app notification.')
            return redirect('hospital:doctor_dashboard')
    
    # Create forms for each appointment
    forms = []
    for appointment in conflicting_appointments:
        form = AppointmentRescheduleFormSingle(
            prefix=f'appointment_{appointment.id}',
            appointment=appointment,
            doctor=doctor
        )
        forms.append({
            'appointment': appointment,
            'form': form
        })
    
    context = {
        'surgery': surgery,
        'forms': forms,
    }
    return render(request, 'hospital/doctor/bulk_reschedule.html', context)


@login_required
def view_notifications(request):
    """View all notifications for the logged-in user"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark all as read
    unread_notifications = notifications.filter(is_read=False)
    unread_notifications.update(is_read=True)
    
    context = {'notifications': notifications}
    return render(request, 'hospital/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect('hospital:view_notifications')


@login_required
@role_required('DOCTOR')
def view_surgeries(request):
    """View all surgeries for the logged-in doctor"""
    doctor = request.user.doctor_profile
    today = date.today()
    
    # Get upcoming surgeries (approved and pending)
    upcoming_surgeries = UrgentSurgery.objects.filter(
        doctor=doctor,
        surgery_date__gte=today,
        status__in=['APPROVED', 'PENDING']
    ).order_by('surgery_date', 'start_time')
    
    # Get past surgeries
    past_surgeries = UrgentSurgery.objects.filter(
        doctor=doctor,
        surgery_date__lt=today
    ).order_by('-surgery_date', '-start_time')[:10]
    
    context = {
        'doctor': doctor,
        'upcoming_surgeries': upcoming_surgeries,
        'past_surgeries': past_surgeries,
    }
    return render(request, 'hospital/doctor/surgeries.html', context)


@login_required
@role_required('DOCTOR', 'PATIENT')
def download_medical_record_pdf(request, record_id):
    """Download medical record as PDF"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from django.http import HttpResponse
    from io import BytesIO
    
    medical_record = get_object_or_404(MedicalRecord, id=record_id)
    
    # Verify this record belongs to the logged-in doctor or patient
    if request.user.role == 'DOCTOR':
        doctor = request.user.doctor_profile
        if medical_record.doctor != doctor:
            messages.error(request, 'You can only download your own medical records.')
            return redirect('hospital:doctor_appointments')
    elif request.user.role == 'PATIENT':
        patient = request.user.patient_profile
        if medical_record.patient != patient:
            messages.error(request, 'You can only download your own medical records.')
            return redirect('hospital:patient_dashboard')
    
    # Create the PDF object
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50,
                            topMargin=30, bottomMargin=30)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles for prescription
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subheader_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=25,  # Significantly increased spacing after address
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=colors.HexColor('#cbd5e1'),
        borderPadding=5,
        backColor=colors.HexColor('#cbd5e1')
    )
    
    rx_style = ParagraphStyle(
        'Rx',
        parent=styles['Normal'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    prescription_style = ParagraphStyle(
        'Prescription',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    small_text_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        fontName='Helvetica'
    )
    
    # Add logo and hospital header
    try:
        from reportlab.platypus import Image
        import os
        from django.conf import settings
        
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'hospital_logo.jpg')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=80, height=80)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 5))  # Reduced spacing after logo
    except:
        pass  # If logo doesn't exist, continue without it
    
    # Hospital name and details
    hospital_name = Paragraph("<b>SWASTHYA CARE HOSPITAL</b>", header_style)
    elements.append(hospital_name)
    
    hospital_details = Paragraph(
        "Address: 123 Medical Street, Healthcare City<br/>Phone: +91 1234567890<br/>Email: info@swasthyacare.com",
        subheader_style
    )
    elements.append(hospital_details)
    
    # Horizontal line
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e3a8a'), 
                               spaceAfter=10, spaceBefore=3))  # Reduced spacing
    
    # Prescription header - removed background color
    prescription_header = Paragraph("<b>MEDICAL PRESCRIPTION</b>", 
                                   ParagraphStyle('PrescHeader', parent=header_style, 
                                                fontSize=16, alignment=TA_CENTER, 
                                                textColor=colors.HexColor('#1e3a8a'),
                                                spaceAfter=10))
    elements.append(prescription_header)
    
    # Date and prescription number
    date_info = Table([
        ['Date:', medical_record.created_at.strftime('%d %B %Y')],
        ['Prescription No:', f'RX-{medical_record.id:05d}']
    ], colWidths=[1.5*inch, 3*inch])
    date_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(date_info)
    elements.append(Spacer(1, 15))
    
    # Patient Information Box
    patient_info_data = [
        ['Patient Name:', medical_record.patient.user.get_full_name(), 'Patient ID:', medical_record.patient.patient_id],
        ['Age/Gender:', f'{medical_record.patient.date_of_birth.strftime("%d/%m/%Y")} / {medical_record.patient.get_gender_display()}', 
         'Blood Group:', medical_record.patient.blood_group or 'N/A'],
        ['Phone:', medical_record.patient.user.phone or 'N/A', 'Email:', medical_record.patient.user.email or 'N/A']
    ]
    
    patient_table = Table(patient_info_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#475569')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 15))
    
    # Diagnosis Section
    elements.append(Paragraph("Clinical Diagnosis", section_heading_style))
    diagnosis_text = medical_record.diagnosis.replace('\n', '<br/>')
    elements.append(Paragraph(diagnosis_text, prescription_style))
    elements.append(Spacer(1, 15))
    
    # Rx Symbol and Prescription - removed symbol, using text only
    elements.append(Paragraph("<b>Rx:</b>", section_heading_style))
    elements.append(Spacer(1, 5))
    
    # Format prescription with line breaks - don't add numbers if already numbered
    prescription_lines = medical_record.prescription.split('\n')
    formatted_lines = []
    for line in prescription_lines:
        line = line.strip()
        if line:
            # Check if line already starts with a number
            if line[0].isdigit() and '. ' in line[:5]:
                formatted_lines.append(line)  # Already numbered
            else:
                formatted_lines.append(line)  # Keep as is
    prescription_html = '<br/>'.join(formatted_lines)
    elements.append(Paragraph(prescription_html, prescription_style))
    elements.append(Spacer(1, 15))
    
    # Additional Notes (if any)
    if medical_record.notes:
        elements.append(Paragraph("Additional Notes", section_heading_style))
        notes_text = medical_record.notes.replace('\n', '<br/>')
        elements.append(Paragraph(notes_text, prescription_style))
        elements.append(Spacer(1, 15))
    
    # Doctor Information Section (No Signature - Computer Generated)
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Prescribed By:", section_heading_style))
    doctor_info = Paragraph(
        f"<b>Dr. {medical_record.doctor.user.get_full_name()}</b><br/>"
        f"{medical_record.doctor.specialization}<br/>"
        f"{medical_record.doctor.qualification}",
        prescription_style
    )
    elements.append(doctor_info)
    elements.append(Spacer(1, 15))
    
    # Computer Generated Notice
    computer_notice = Paragraph(
        "<i>*** This is a computer-generated prescription and does not require a physical signature ***</i>",
        ParagraphStyle('Notice', parent=small_text_style, alignment=TA_CENTER, 
                      textColor=colors.HexColor('#475569'), fontSize=9)
    )
    elements.append(computer_notice)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1')))
    footer_text = Paragraph(
        f"<i>This is a computer-generated prescription. Generated on {medical_record.created_at.strftime('%d %B %Y at %I:%M %p')}</i>",
        small_text_style
    )
    elements.append(Spacer(1, 5))
    elements.append(footer_text)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{medical_record.patient.patient_id}_{medical_record.created_at.strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    
    return response


# Admin Panel Views
@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    """Admin dashboard with navigation to create doctors and receptionists"""
    # Get statistics
    total_doctors = Doctor.objects.count()
    total_receptionists = CustomUser.objects.filter(role='RECEPTIONIST').count()
    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    
    # Get user lists
    doctors = Doctor.objects.all().select_related('user').order_by('user__first_name')
    receptionists = CustomUser.objects.filter(role='RECEPTIONIST').order_by('first_name')
    
    context = {
        'total_doctors': total_doctors,
        'total_receptionists': total_receptionists,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'doctors': doctors,
        'receptionists': receptionists,
    }
    return render(request, 'hospital/admin/admin_dashboard.html', context)


@login_required
@role_required('ADMIN')
def create_doctor(request):
    """Create new doctor user"""
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            try:
                doctor = form.save()
                messages.success(request, f'Doctor {doctor.user.get_full_name()} created successfully!')
                return redirect('hospital:admin_dashboard')
            except IntegrityError:
                messages.error(request, 'Username already exists. Please choose a different username.')
    else:
        form = DoctorRegistrationForm()
    
    context = {'form': form}
    return render(request, 'hospital/admin/create_doctor.html', context)


@login_required
@role_required('ADMIN')
def create_receptionist(request):
    """Create new receptionist user"""
    if request.method == 'POST':
        form = ReceptionistRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'Receptionist {user.get_full_name()} created successfully!')
                return redirect('hospital:admin_dashboard')
            except IntegrityError:
                messages.error(request, 'Username already exists. Please choose a different username.')
    else:
        form = ReceptionistRegistrationForm()
    
    context = {'form': form}
    return render(request, 'hospital/admin/create_receptionist.html', context)


@login_required
@role_required('ADMIN')
def delete_user(request, user_id):
    """Delete a doctor or receptionist user"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent deleting admin users
    if user.role == 'ADMIN':
        messages.error(request, 'Cannot delete admin users.')
        return redirect('hospital:admin_dashboard')
    
    # Prevent deleting patients
    if user.role == 'PATIENT':
        messages.error(request, 'Cannot delete patients from this panel.')
        return redirect('hospital:admin_dashboard')
    
    # Only allow deleting doctors and receptionists
    if user.role not in ['DOCTOR', 'RECEPTIONIST']:
        messages.error(request, 'Invalid user type.')
        return redirect('hospital:admin_dashboard')
    
    username = user.get_full_name()
    user.delete()
    messages.success(request, f'User {username} deleted successfully.')
    return redirect('hospital:admin_dashboard')

