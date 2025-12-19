from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
from hospital.models import CustomUser, Patient, Doctor, Appointment, DoctorAvailability


class Command(BaseCommand):
    help = 'Setup demo data for SwasthyaCare Hospital'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up demo data...')
        
        # Create Superuser
        if not CustomUser.objects.filter(username='admin').exists():
            superuser = CustomUser.objects.create_superuser(
                username='admin',
                email='admin@swasthyacare.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role='SUPERUSER'
            )
            self.stdout.write(self.style.SUCCESS('✓ Created superuser: admin / admin123'))
        
        # Create Receptionist
        if not CustomUser.objects.filter(username='receptionist').exists():
            receptionist = CustomUser.objects.create_user(
                username='receptionist',
                email='receptionist@swasthyacare.com',
                password='password',
                first_name='Priya',
                last_name='Sharma',
                role='RECEPTIONIST',
                phone='9876543210'
            )
            self.stdout.write(self.style.SUCCESS('✓ Created receptionist: receptionist / password'))
        
        # Create Doctors
        doctors_data = [
            {
                'username': 'doctor',
                'email': 'doctor@swasthyacare.com',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'phone': '9876543211',
                'specialization': 'General Physician',
                'qualification': 'MBBS, MD',
                'experience_years': 10,
                'consultation_fee': 500
            },
            {
                'username': 'doctor2',
                'email': 'doctor2@swasthyacare.com',
                'first_name': 'Anjali',
                'last_name': 'Verma',
                'phone': '9876543212',
                'specialization': 'Cardiologist',
                'qualification': 'MBBS, MD, DM (Cardiology)',
                'experience_years': 15,
                'consultation_fee': 1000
            },
            {
                'username': 'doctor3',
                'email': 'doctor3@swasthyacare.com',
                'first_name': 'Suresh',
                'last_name': 'Patel',
                'phone': '9876543213',
                'specialization': 'Orthopedic',
                'qualification': 'MBBS, MS (Ortho)',
                'experience_years': 12,
                'consultation_fee': 800
            }
        ]
        
        for doc_data in doctors_data:
            if not CustomUser.objects.filter(username=doc_data['username']).exists():
                user = CustomUser.objects.create_user(
                    username=doc_data['username'],
                    email=doc_data['email'],
                    password='password',
                    first_name=doc_data['first_name'],
                    last_name=doc_data['last_name'],
                    role='DOCTOR',
                    phone=doc_data['phone']
                )
                
                Doctor.objects.create(
                    user=user,
                    specialization=doc_data['specialization'],
                    qualification=doc_data['qualification'],
                    experience_years=doc_data['experience_years'],
                    consultation_fee=doc_data['consultation_fee']
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Created doctor: {doc_data["username"]} / password'))
        
        # Create Patients
        patients_data = [
            {
                'username': 'patient',
                'email': 'patient@example.com',
                'first_name': 'Amit',
                'last_name': 'Singh',
                'phone': '9876543220',
                'date_of_birth': date(1990, 5, 15),
                'gender': 'MALE',
                'address': '123 MG Road, Mumbai, Maharashtra',
                'blood_group': 'O+',
                'allergies': 'Penicillin',
                'chronic_diseases': 'None',
                'previous_surgeries': 'Appendectomy (2015)',
                'emergency_contact_name': 'Sunita Singh',
                'emergency_contact_phone': '9876543221'
            },
            {
                'username': 'patient2',
                'email': 'patient2@example.com',
                'first_name': 'Neha',
                'last_name': 'Gupta',
                'phone': '9876543222',
                'date_of_birth': date(1985, 8, 20),
                'gender': 'FEMALE',
                'address': '456 Park Street, Delhi',
                'blood_group': 'A+',
                'allergies': 'None',
                'chronic_diseases': 'Diabetes Type 2',
                'previous_surgeries': 'None',
                'emergency_contact_name': 'Rahul Gupta',
                'emergency_contact_phone': '9876543223'
            },
            {
                'username': 'patient3',
                'email': 'patient3@example.com',
                'first_name': 'Vikram',
                'last_name': 'Reddy',
                'phone': '9876543224',
                'date_of_birth': date(1995, 3, 10),
                'gender': 'MALE',
                'address': '789 Brigade Road, Bangalore',
                'blood_group': 'B+',
                'allergies': 'Dust, Pollen',
                'chronic_diseases': 'Asthma',
                'previous_surgeries': 'None',
                'emergency_contact_name': 'Lakshmi Reddy',
                'emergency_contact_phone': '9876543225'
            }
        ]
        
        for pat_data in patients_data:
            if not CustomUser.objects.filter(username=pat_data['username']).exists():
                user = CustomUser.objects.create_user(
                    username=pat_data['username'],
                    email=pat_data['email'],
                    password='password',
                    first_name=pat_data['first_name'],
                    last_name=pat_data['last_name'],
                    role='PATIENT',
                    phone=pat_data['phone']
                )
                
                Patient.objects.create(
                    user=user,
                    date_of_birth=pat_data['date_of_birth'],
                    gender=pat_data['gender'],
                    address=pat_data['address'],
                    blood_group=pat_data['blood_group'],
                    allergies=pat_data['allergies'],
                    chronic_diseases=pat_data['chronic_diseases'],
                    previous_surgeries=pat_data['previous_surgeries'],
                    emergency_contact_name=pat_data['emergency_contact_name'],
                    emergency_contact_phone=pat_data['emergency_contact_phone']
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Created patient: {pat_data["username"]} / password'))
        
        # Create some sample appointments
        doctor1 = Doctor.objects.filter(user__username='doctor').first()
        doctor2 = Doctor.objects.filter(user__username='doctor2').first()
        patient1 = Patient.objects.filter(user__username='patient').first()
        patient2 = Patient.objects.filter(user__username='patient2').first()
        
        if doctor1 and patient1:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            # Today's appointment
            if not Appointment.objects.filter(doctor=doctor1, appointment_date=today, appointment_time=time(10, 0)).exists():
                Appointment.objects.create(
                    patient=patient1,
                    doctor=doctor1,
                    appointment_date=today,
                    appointment_time=time(10, 0),
                    reason='Regular checkup',
                    status='SCHEDULED',
                    created_by=CustomUser.objects.filter(role='RECEPTIONIST').first()
                )
                self.stdout.write(self.style.SUCCESS('✓ Created sample appointment for today'))
            
            # Tomorrow's appointment
            if not Appointment.objects.filter(doctor=doctor2, appointment_date=tomorrow, appointment_time=time(14, 0)).exists():
                Appointment.objects.create(
                    patient=patient2,
                    doctor=doctor2,
                    appointment_date=tomorrow,
                    appointment_time=time(14, 0),
                    reason='Heart checkup',
                    status='SCHEDULED',
                    created_by=CustomUser.objects.filter(role='RECEPTIONIST').first()
                )
                self.stdout.write(self.style.SUCCESS('✓ Created sample appointment for tomorrow'))
        
        # Add doctor availability (lunch break)
        if doctor1:
            today = date.today()
            if not DoctorAvailability.objects.filter(doctor=doctor1, date=today, availability_type='LUNCH').exists():
                DoctorAvailability.objects.create(
                    doctor=doctor1,
                    availability_type='LUNCH',
                    date=today,
                    start_time=time(13, 0),
                    end_time=time(14, 0),
                    reason='Lunch break'
                )
                self.stdout.write(self.style.SUCCESS('✓ Created sample doctor availability'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data setup complete!'))
        self.stdout.write('\nLogin credentials:')
        self.stdout.write('  Superuser: admin / admin123')
        self.stdout.write('  Doctor: doctor / password')
        self.stdout.write('  Receptionist: receptionist / password')
        self.stdout.write('  Patient: patient / password')
