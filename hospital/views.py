from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, date, timedelta
from .models import CustomUser, Patient, Doctor, Appointment, MedicalRecord, DoctorAvailability
from .forms import (PatientRegistrationForm, AppointmentForm, MedicalRecordForm, 
                    DoctorAvailabilityForm, RescheduleAppointmentForm, FollowUpAppointmentForm)
from .decorators import role_required
from django.db import IntegrityError
from datetime import time

# Authentication Views
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
    
    context = {
        'doctor': doctor,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
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
    
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES)
        if form.is_valid():
            medical_record = form.save(commit=False)
            medical_record.appointment = appointment
            medical_record.patient = appointment.patient
            medical_record.doctor = doctor
            medical_record.save()
            messages.success(request, 'Medical record added successfully.')
            return redirect('hospital:doctor_appointments')
    else:
        form = MedicalRecordForm()
    
    context = {
        'form': form,
        'appointment': appointment,
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
    
    # Get upcoming availability records
    availabilities = DoctorAvailability.objects.filter(
        doctor=doctor,
        date__gte=date.today()
    ).order_by('date', 'start_time')
    
    context = {
        'form': form,
        'availabilities': availabilities,
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
            
            # Check if doctor has marked this time as unavailable
            unavailable = DoctorAvailability.objects.filter(
                doctor=doctor,
                date=app_date,
                start_time__lte=app_time,
                end_time__gt=app_time
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
            
            # Check availability
            doctor = updated_appointment.doctor
            app_date = updated_appointment.appointment_date
            app_time = updated_appointment.appointment_time
            
            unavailable = DoctorAvailability.objects.filter(
                doctor=doctor,
                date=app_date,
                start_time__lte=app_time,
                end_time__gt=app_time
            ).exists()
            
            if unavailable:
                messages.error(request, 'Doctor is not available at this time.')
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


# Patient Views
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
            
            # Get unavailable times
            unavailable_times = DoctorAvailability.objects.filter(
                doctor=doctor,
                date=check_date
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
