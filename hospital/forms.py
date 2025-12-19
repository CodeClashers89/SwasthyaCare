from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Patient, Appointment, MedicalRecord, DoctorAvailability, Doctor
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
        fields = ['date_of_birth', 'gender', 'address', 'blood_group', 'allergies', 
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
#---------------------------------------------------------------------------------------------
def generate_15_min_slots(start_hour=9, end_hour=17):
    slots = []
    for hour in range(start_hour, end_hour):
        for minute in (0, 15, 30, 45):
            t = time(hour, minute)
            slots.append((t, t.strftime('%H:%M')))
    return slots
#--------------------------------------------------------------------------------------------
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
#--------------
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
    class Meta:
        model = DoctorAvailability
        fields = ['availability_type', 'date', 'start_time', 'end_time', 'reason']
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
