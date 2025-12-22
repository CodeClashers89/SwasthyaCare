from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Patient, Appointment, MedicalRecord, DoctorAvailability, Doctor, UrgentSurgery
from datetime import datetime, time


class PatientRegistrationForm(forms.ModelForm):
    """Form for registering new patients"""
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = Patient
        fields = ['date_of_birth', 'gender', 'address', 'phone_number', 'blood_group', 'allergies', 
                  'chronic_diseases', 'previous_surgeries', 'emergency_contact_name', 
                  'emergency_contact_phone']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'chronic_diseases': forms.Textarea(attrs={'rows': 2}),
            'previous_surgeries': forms.Textarea(attrs={'rows': 2}),
        }
    
    def save(self, commit=True):
        # Create user first
        user = CustomUser.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            role='PATIENT'
        )
        
        # Create patient profile
        patient = super().save(commit=False)
        patient.user = user
        if commit:
            patient.save()
        return patient

def generate_15_min_slots(start_hour=9, end_hour=17):
    slots = []
    for hour in range(start_hour, end_hour):
        for minute in (0, 15, 30, 45):
            t = time(hour, minute)
            slots.append((t, t.strftime('%H:%M')))
    return slots

class AppointmentForm(forms.ModelForm):
    """Form for creating appointments"""
    appointment_time = forms.ChoiceField(
        choices=generate_15_min_slots(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'reason']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            #'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        slots = kwargs.pop('slots',[])
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('patient_id')
        self.fields['doctor'].queryset = Doctor.objects.all().order_by('user__first_name')
#--------
        self.fields['appointment_time'].choices = [(slot,slot)for slot in slots]
    def clean_appointment_time(self):
        value = self.cleaned_data['appointment_time']
        hour,minute = map(int,value.split(':'))
        return time(hour,minute)


class FollowUpAppointmentForm(forms.ModelForm):
    """Form for creating follow-up appointments"""
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time', 'reason']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }


class MedicalRecordForm(forms.ModelForm):
    """Form for adding medical records"""
    class Meta:
        model = MedicalRecord
        fields = ['diagnosis', 'prescription', 'report_file', 'notes']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 4}),
            'prescription': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class DoctorAvailabilityForm(forms.ModelForm):
    """Form for managing doctor availability"""
    is_recurring = forms.BooleanField(
        required=False,
        initial=False,
        label='Recurring (Everyday)',
        help_text='Check this for daily lunch breaks'
    )
    
    class Meta:
        model = DoctorAvailability
        fields = ['availability_type', 'is_recurring', 'date', 'start_time', 'end_time', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        availability_type = cleaned_data.get('availability_type')
        is_recurring = cleaned_data.get('is_recurring')
        date = cleaned_data.get('date')
        
        # If not recurring, date is required
        if not is_recurring and not date:
            raise forms.ValidationError('Date is required for non-recurring unavailability.')
        
        # If recurring, date should be None
        if is_recurring:
            cleaned_data['date'] = None
        
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('End time must be after start time.')
            
            # Check lunch break duration (max 1 hour)
            if availability_type == 'LUNCH':
                start_datetime = datetime.combine(datetime.today(), start_time)
                end_datetime = datetime.combine(datetime.today(), end_time)
                duration = (end_datetime - start_datetime).seconds / 3600
                if duration > 1:
                    raise forms.ValidationError('Lunch break cannot exceed 1 hour.')
        
        return cleaned_data


class RescheduleAppointmentForm(forms.ModelForm):
    """Form for rescheduling appointments"""
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class UrgentSurgeryForm(forms.ModelForm):
    """Form for creating urgent surgeries"""
    class Meta:
        model = UrgentSurgery
        fields = ['doctor', 'surgery_date', 'start_time', 'end_time', 'surgery_type', 'patient_name', 'notes']
        widgets = {
            'surgery_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If user is a doctor, hide doctor field and set it automatically
        if user and hasattr(user, 'doctor_profile'):
            self.fields['doctor'].widget = forms.HiddenInput()
            self.fields['doctor'].initial = user.doctor_profile
        else:
            # For receptionist, show all doctors
            self.fields['doctor'].queryset = Doctor.objects.all().order_by('user__first_name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        surgery_date = cleaned_data.get('surgery_date')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('End time must be after start time.')
        
        if surgery_date:
            from datetime import date
            if surgery_date < date.today():
                raise forms.ValidationError('Surgery date cannot be in the past.')
        
        return cleaned_data


class SurgeryApprovalForm(forms.Form):
    """Form for approving or rejecting urgent surgeries"""
    STATUS_CHOICES = [
        ('APPROVED', 'Approve Surgery'),
        ('REJECTED', 'Reject Surgery'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect,
        label='Decision'
    )
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Rejection Reason (if rejecting)',
        help_text='Please provide a reason if rejecting the surgery request'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if status == 'REJECTED' and not rejection_reason:
            raise forms.ValidationError('Rejection reason is required when rejecting a surgery.')
        
        return cleaned_data


class AppointmentRescheduleFormSingle(forms.Form):
    """Form for rescheduling a single appointment"""
    new_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='New Date'
    )
    new_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label='New Time'
    )
    
    def __init__(self, *args, **kwargs):
        self.appointment = kwargs.pop('appointment', None)
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        new_date = cleaned_data.get('new_date')
        new_time = cleaned_data.get('new_time')
        
        if new_date and new_time and self.doctor:
            from datetime import date
            
            # Check if date is not in the past
            if new_date < date.today():
                raise forms.ValidationError('Cannot reschedule to a past date.')
            
            # Check if doctor is available at this time
            from .models import DoctorAvailability, Appointment
            from django.db.models import Q
            
            unavailable = DoctorAvailability.objects.filter(
                Q(doctor=self.doctor, date=new_date, start_time__lte=new_time, end_time__gt=new_time) |
                Q(doctor=self.doctor, is_recurring=True, start_time__lte=new_time, end_time__gt=new_time)
            ).exists()
            
            if unavailable:
                raise forms.ValidationError('Doctor is not available at this time.')
            
            # Check for duplicate appointments (excluding current appointment)
            duplicate = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=new_date,
                appointment_time=new_time,
                status='SCHEDULED'
            )
            
            if self.appointment:
                duplicate = duplicate.exclude(id=self.appointment.id)
            
            if duplicate.exists():
                raise forms.ValidationError('This time slot is already booked.')
        
        return cleaned_data


class DoctorRegistrationForm(forms.Form):
    """Form for creating doctor users by admin"""
    # User fields
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    phone = forms.CharField(max_length=15, required=False)
    
    # Doctor profile fields
    specialization = forms.CharField(max_length=100, required=True)
    qualification = forms.CharField(max_length=200, required=True)
    experience_years = forms.IntegerField(min_value=0, required=True)
    consultation_fee = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    def save(self, commit=True):
        # Create user first
        user = CustomUser.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data.get('phone', ''),
            role='DOCTOR'
        )
        
        # Create doctor profile
        doctor = Doctor.objects.create(
            user=user,
            specialization=self.cleaned_data['specialization'],
            qualification=self.cleaned_data['qualification'],
            experience_years=self.cleaned_data['experience_years'],
            consultation_fee=self.cleaned_data['consultation_fee']
        )
        return doctor


class ReceptionistRegistrationForm(forms.Form):
    """Form for creating receptionist users by admin"""
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    phone = forms.CharField(max_length=15, required=False)
    
    def save(self, commit=True):
        # Create receptionist user
        user = CustomUser.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data.get('phone', ''),
            role='RECEPTIONIST'
        )
        return user
