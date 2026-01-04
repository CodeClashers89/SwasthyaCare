from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q
from .models import Patient, Doctor, Appointment, DoctorAvailability
from .decorators import role_required
import json
import re


@login_required
@role_required('PATIENT')
@require_http_methods(["POST"])
def chatbot_message(request):
    """
    Main chatbot endpoint that processes user messages and returns appropriate responses
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').lower().strip()
        
        # Get patient profile
        patient = request.user.patient_profile
        
        # Intent detection based on keywords
        response = detect_intent_and_respond(message, patient, request.user)
        
        return JsonResponse(response)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Sorry, I encountered an error: {str(e)}',
            'type': 'error'
        })


def detect_intent_and_respond(message, patient, user):
    """
    Detect user intent from message and generate appropriate response
    """
    
    # Intent: View Appointments
    if any(keyword in message for keyword in ['appointment', 'appointments', 'show my appointment', 'my appointment', 'scheduled']):
        return get_appointments_response(patient)
    
    # Intent: List Doctors
    elif any(keyword in message for keyword in ['doctor', 'doctors', 'list doctor', 'show doctor', 'available doctor', 'find doctor']):
        return get_doctors_response()
    
    # Intent: Check Availability
    elif any(keyword in message for keyword in ['availability', 'available', 'free', 'when can i', 'book']):
        return get_availability_prompt()
    
    # Intent: Help/Greeting
    elif any(keyword in message for keyword in ['hi', 'hello', 'hey', 'help', 'what can you do', 'start']):
        return get_welcome_response(patient)
    
    # Default response
    else:
        return {
            'success': True,
            'message': "I can help you with:\n• View your appointments\n• Check doctor availability\n• List all doctors\n• Book appointments\n\nWhat would you like to do?",
            'type': 'text',
            'quick_actions': [
                {'label': 'My Appointments', 'action': 'appointments'},
                {'label': 'List Doctors', 'action': 'doctors'},
                {'label': 'Book Appointment', 'action': 'book'}
            ]
        }


def get_welcome_response(patient):
    """Welcome message with quick actions"""
    return {
        'success': True,
        'message': f"Hello {patient.user.get_full_name()}! 👋\n\nI'm your healthcare assistant. I can help you:\n• View your appointments\n• Check doctor availability\n• Find and book appointments with doctors\n\nHow can I assist you today?",
        'type': 'text',
        'quick_actions': [
            {'label': 'My Appointments', 'action': 'appointments'},
            {'label': 'List Doctors', 'action': 'doctors'},
            {'label': 'Book Appointment', 'action': 'book'}
        ]
    }


def get_appointments_response(patient):
    """Get patient's appointments"""
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-appointment_time')[:10]
    
    if not appointments:
        return {
            'success': True,
            'message': "You don't have any appointments yet. Would you like to book one?",
            'type': 'text',
            'quick_actions': [
                {'label': 'Book Appointment', 'action': 'book'},
                {'label': 'List Doctors', 'action': 'doctors'}
            ]
        }
    
    # Separate upcoming and past appointments
    today = timezone.now().date()
    upcoming = []
    past = []
    
    for apt in appointments:
        apt_data = {
            'id': apt.id,
            'doctor': f"Dr. {apt.doctor.user.get_full_name()}",
            'specialization': apt.doctor.specialization,
            'date': apt.appointment_date.strftime('%B %d, %Y'),
            'time': apt.appointment_time.strftime('%I:%M %p'),
            'reason': apt.reason,
            'status': apt.get_status_display()
        }
        
        if apt.appointment_date >= today and apt.status == 'SCHEDULED':
            upcoming.append(apt_data)
        else:
            past.append(apt_data)
    
    return {
        'success': True,
        'type': 'appointments',
        'upcoming': upcoming,
        'past': past,
        'message': f"Found {len(upcoming)} upcoming and {len(past)} past appointments."
    }


def get_doctors_response():
    """Get list of all doctors"""
    doctors = Doctor.objects.select_related('user').all()
    
    if not doctors:
        return {
            'success': True,
            'message': "No doctors are currently available in the system.",
            'type': 'text'
        }
    
    doctors_list = []
    for doctor in doctors:
        doctors_list.append({
            'id': doctor.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization,
            'qualification': doctor.qualification,
            'experience': f"{doctor.experience_years} years",
            'fee': f"₹{doctor.consultation_fee}"
        })
    
    return {
        'success': True,
        'type': 'doctors',
        'doctors': doctors_list,
        'message': f"Here are {len(doctors_list)} available doctors:"
    }


def get_availability_prompt():
    """Prompt user to select doctor for availability check"""
    doctors = Doctor.objects.select_related('user').all()
    
    doctors_list = []
    for doctor in doctors:
        doctors_list.append({
            'id': doctor.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization
        })
    
    return {
        'success': True,
        'type': 'availability_prompt',
        'doctors': doctors_list,
        'message': "Please select a doctor to check availability:"
    }


@login_required
@role_required('PATIENT')
@require_http_methods(["POST"])
def check_doctor_availability_api(request):
    """
    Check availability for a specific doctor on a specific date
    """
    try:
        data = json.loads(request.body)
        doctor_id = data.get('doctor_id')
        date_str = data.get('date')
        
        if not doctor_id or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Doctor ID and date are required'
            })
        
        doctor = Doctor.objects.get(id=doctor_id)
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Check if date is in the past
        if check_date < timezone.now().date():
            return JsonResponse({
                'success': False,
                'message': 'Cannot book appointments in the past'
            })
        
        # Generate time slots (9 AM to 5 PM, 15-minute intervals)
        available_slots = []
        current_time = time(9, 0)
        end_time = time(17, 0)
        
        while current_time < end_time:
            # Check if slot is available
            is_available = is_slot_available(doctor, check_date, current_time)
            
            if is_available:
                available_slots.append({
                    'time': current_time.strftime('%I:%M %p'),
                    'value': current_time.strftime('%H:%M')
                })
            
            # Increment by 15 minutes
            hour = current_time.hour
            minute = current_time.minute + 15
            if minute >= 60:
                hour += 1
                minute = 0
            current_time = time(hour, minute)
        
        return JsonResponse({
            'success': True,
            'doctor': f"Dr. {doctor.user.get_full_name()}",
            'date': check_date.strftime('%B %d, %Y'),
            'available_slots': available_slots,
            'type': 'availability'
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Doctor not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error checking availability: {str(e)}'
        })


def is_slot_available(doctor, date, time_slot):
    """
    Check if a time slot is available for a doctor
    """
    # Check existing appointments
    existing_appointment = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=date,
        appointment_time=time_slot,
        status='SCHEDULED'
    ).exists()
    
    if existing_appointment:
        return False
    
    # Check doctor unavailability
    unavailable = DoctorAvailability.objects.filter(
        doctor=doctor,
        availability_type='UNAVAILABLE'
    ).filter(
        Q(date=date) | Q(is_recurring=True)
    ).filter(
        start_time__lte=time_slot,
        end_time__gt=time_slot
    ).exists()
    
    if unavailable:
        return False
    
    return True


@login_required
@role_required('PATIENT')
@require_http_methods(["POST"])
def book_appointment_api(request):
    """
    Book an appointment through the chatbot
    """
    try:
        data = json.loads(request.body)
        doctor_id = data.get('doctor_id')
        date_str = data.get('date')
        time_str = data.get('time')
        reason = data.get('reason', 'General consultation')
        
        if not all([doctor_id, date_str, time_str]):
            return JsonResponse({
                'success': False,
                'message': 'Doctor, date, and time are required'
            })
        
        doctor = Doctor.objects.get(id=doctor_id)
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()
        patient = request.user.patient_profile
        
        # Verify slot is still available
        if not is_slot_available(doctor, appointment_date, appointment_time):
            return JsonResponse({
                'success': False,
                'message': 'This time slot is no longer available. Please choose another time.'
            })
        
        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status='SCHEDULED',
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Appointment booked successfully!\n\n📅 Date: {appointment_date.strftime('%B %d, %Y')}\n🕐 Time: {appointment_time.strftime('%I:%M %p')}\n👨‍⚕️ Doctor: Dr. {doctor.user.get_full_name()}\n🏥 Specialization: {doctor.specialization}",
            'type': 'booking_success',
            'appointment_id': appointment.id
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Doctor not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error booking appointment: {str(e)}'
        })
