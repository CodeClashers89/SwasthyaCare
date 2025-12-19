from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Patient, Doctor, Appointment, MedicalRecord, DoctorAvailability


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom User Admin"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'email', 'first_name', 'last_name')}),
    )


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Patient Admin"""
    list_display = ['patient_id', 'get_full_name', 'date_of_birth', 'blood_group', 'created_at']
    list_filter = ['blood_group', 'gender', 'created_at']
    search_fields = ['patient_id', 'user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['patient_id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Doctor Admin"""
    list_display = ['get_full_name', 'specialization', 'experience_years', 'consultation_fee']
    list_filter = ['specialization']
    search_fields = ['user__first_name', 'user__last_name', 'specialization']
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"
    get_full_name.short_description = 'Doctor Name'


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    """Doctor Availability Admin"""
    list_display = ['doctor', 'availability_type', 'date', 'start_time', 'end_time']
    list_filter = ['availability_type', 'date', 'doctor']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Appointment Admin"""
    list_display = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'is_follow_up']
    list_filter = ['status', 'is_follow_up', 'appointment_date', 'doctor']
    search_fields = ['patient__patient_id', 'patient__user__first_name', 'doctor__user__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Medical Record Admin"""
    list_display = ['patient', 'doctor', 'appointment', 'created_at']
    list_filter = ['created_at', 'doctor']
    search_fields = ['patient__patient_id', 'patient__user__first_name', 'diagnosis']
    readonly_fields = ['created_at', 'updated_at']
