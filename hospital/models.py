from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone


class CustomUser(AbstractUser):
    """Extended User model with role-based access"""
    ROLE_CHOICES = [
        ('DOCTOR', 'Doctor'),
        ('RECEPTIONIST', 'Receptionist'),
        ('PATIENT', 'Patient'),
        ('ADMIN', 'Admin'),
        ('SUPERUSER', 'Superuser'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Patient(models.Model):
    """Patient information with medical history"""
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='patient_profile')
    patient_id = models.CharField(max_length=10, unique=True, editable=False)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')])
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True, help_text="List any allergies")
    chronic_diseases = models.TextField(blank=True, null=True, help_text="List any chronic diseases")
    previous_surgeries = models.TextField(blank=True, null=True, help_text="List any previous surgeries")
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.patient_id:
            # Generate unique patient ID
            last_patient = Patient.objects.all().order_by('id').last()
            if last_patient:
                last_id = int(last_patient.patient_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1
            self.patient_id = f'P{new_id:05d}'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.patient_id} - {self.user.get_full_name()}"
    
    class Meta:
        ordering = ['-created_at']


class Doctor(models.Model):
    """Doctor information and specialization"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200)
    experience_years = models.IntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"


class DoctorAvailability(models.Model):
    """Manage doctor's availability, lunch breaks, and unavailable periods"""
    AVAILABILITY_TYPE_CHOICES = [
        ('UNAVAILABLE', 'Unavailable')
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    availability_type = models.CharField(max_length=20, choices=AVAILABILITY_TYPE_CHOICES)
    date = models.DateField(null=True, blank=True)  # Null for recurring lunch breaks
    is_recurring = models.BooleanField(default=False, help_text="If true, applies every day (for lunch breaks)")
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.is_recurring:
            return f"{self.doctor.user.get_full_name()} - {self.availability_type} (Everyday)"
        return f"{self.doctor.user.get_full_name()} - {self.availability_type} on {self.date}"
    
    class Meta:
        ordering = ['date', 'start_time']
        verbose_name_plural = 'Doctor Availabilities'


class Appointment(models.Model):
    """Appointment booking and management"""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    reminder_sent = models.BooleanField(default=False)
    reason = models.TextField(help_text="Reason for visit")
    is_follow_up = models.BooleanField(default=False)
    parent_appointment = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='follow_ups')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_appointments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.patient.patient_id} - Dr. {self.doctor.user.get_full_name()} on {self.appointment_date} at {self.appointment_time}"
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        unique_together = ['doctor', 'appointment_date', 'appointment_time']


class MedicalRecord(models.Model):
    """Medical records including diagnosis, prescriptions, and reports"""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='medical_records')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='medical_records')
    diagnosis = models.TextField(help_text="Diagnosis notes")
    prescription = models.TextField(help_text="Prescription details")
    report_file = models.FileField(upload_to='medical_reports/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Record for {self.patient.patient_id} by Dr. {self.doctor.user.get_full_name()} on {self.created_at.date()}"
    
    class Meta:
        ordering = ['-created_at']
class UrgentSurgery(models.Model):
    """Urgent surgery scheduling with approval workflow"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='urgent_surgeries')
    surgery_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    surgery_type = models.CharField(max_length=200, help_text="Type/description of surgery")
    patient_name = models.CharField(max_length=200, help_text="Patient name (may not be in system)")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_surgeries')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_surgeries')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.surgery_type} - Dr. {self.doctor.user.get_full_name()} on {self.surgery_date} ({self.get_status_display()})"
    
    def get_conflicting_appointments(self):
        """Get all appointments that conflict with this surgery time"""
        return Appointment.objects.filter(
            doctor=self.doctor,
            appointment_date=self.surgery_date,
            appointment_time__gte=self.start_time,
            appointment_time__lt=self.end_time,
            status='SCHEDULED'
        )
    
    class Meta:
        ordering = ['-surgery_date', '-start_time']
        verbose_name_plural = 'Urgent Surgeries'


class Notification(models.Model):
    """Notification system for doctors and staff"""
    NOTIFICATION_TYPE_CHOICES = [
        ('SURGERY_APPROVAL_PENDING', 'Surgery Approval Pending'),
        ('SURGERY_APPROVED', 'Surgery Approved'),
        ('SURGERY_REJECTED', 'Surgery Rejected'),
        ('APPOINTMENT_RESCHEDULED', 'Appointment Rescheduled'),
    ]
    
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_surgery = models.ForeignKey(UrgentSurgery, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    related_appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username} ({'Read' if self.is_read else 'Unread'})"
    
    class Meta:
        ordering = ['-created_at']


class AppointmentReschedule(models.Model):
    """Track rescheduled appointments due to urgent surgeries"""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reschedule_history')
    original_date = models.DateField()
    original_time = models.TimeField()
    new_date = models.DateField()
    new_time = models.TimeField()
    reason = models.TextField(help_text="Reason for rescheduling")
    urgent_surgery = models.ForeignKey(UrgentSurgery, on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_appointments')
    rescheduled_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='rescheduled_appointments')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Rescheduled: {self.appointment.patient.patient_id} from {self.original_date} {self.original_time} to {self.new_date} {self.new_time}"
    
    class Meta:
        ordering = ['-created_at']