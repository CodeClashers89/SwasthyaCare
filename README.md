# SwasthyaCare Hospital Management System

A comprehensive Django-based hospital management application with role-based access control for Doctors, Receptionists, Patients, and Superusers.

## Features

### 🩺 Doctor Features
- View assigned appointments (today's and upcoming)
- Access patient medical history
- Add diagnosis notes, prescriptions, and upload medical reports
- Mark appointments as complete or no-show
- Create follow-up appointments
- Set lunch breaks (max 1 hour) and mark unavailable dates/times

### 📋 Receptionist Features
- Register new patients with complete medical information
- Auto-generated unique patient IDs (format: P00001, P00002, etc.)
- Create, reschedule, and cancel appointments
- Check doctor availability before booking
- View all booked appointments with filtering options
- Manage doctor availability settings

### 👤 Patient Features
- View appointment history timeline
- Access medical records from past appointments
- Check doctor availability (cannot book appointments directly)
- View personal and medical information

### 👨‍💼 Superuser Features
- Full admin panel access
- Create and manage all users (Doctors, Receptionists, Patients)
- Complete CRUD operations on all models

## Technology Stack

- **Backend**: Django 5.2.8
- **Database**: SQLite (default)
- **Frontend**: Pure HTML & CSS (no JavaScript)
- **Authentication**: Django's built-in auth with custom user roles

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies
```bash
pip install django
```

### Step 2: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Setup Demo Data
```bash
python manage.py setup_demo_data
```

This command creates:
- 1 Superuser
- 3 Doctors (General Physician, Cardiologist, Orthopedic)
- 1 Receptionist
- 3 Patients
- Sample appointments
- Sample doctor availability records

### Step 4: Run Development Server
```bash
python manage.py runserver
```

The application will be available at: **http://127.0.0.1:8000/**

## Demo Credentials

### Superuser (Admin Panel)
- **Username**: admin
- **Password**: admin123
- **Access**: http://127.0.0.1:8000/admin/

### Doctor
- **Username**: doctor
- **Password**: password
- **Role**: General Physician

### Receptionist
- **Username**: receptionist
- **Password**: password

### Patient
- **Username**: patient
- **Password**: password
- **Patient ID**: P00001

## Additional Demo Users

### Doctors
1. **doctor2** / password - Cardiologist
2. **doctor3** / password - Orthopedic Specialist

### Patients
1. **patient2** / password - Patient ID: P00002
2. **patient3** / password - Patient ID: P00003

## Application Structure

```
SwasthyaCare/
├── hospital/                 # Main application
│   ├── models.py            # Database models
│   ├── views.py             # View functions
│   ├── forms.py             # Django forms
│   ├── admin.py             # Admin configuration
│   ├── decorators.py        # Role-based access decorators
│   └── urls.py              # URL routing
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   ├── hospital/
│   │   ├── login.html
│   │   ├── doctor/         # Doctor templates
│   │   ├── receptionist/   # Receptionist templates
│   │   └── patient/        # Patient templates
├── static/
│   └── css/
│       └── style.css       # Application styles
├── swasthyacare/           # Project settings
│   ├── settings.py
│   └── urls.py
└── manage.py
```

## Database Models

### CustomUser
Extended Django user model with role field (DOCTOR, RECEPTIONIST, PATIENT, SUPERUSER)

### Patient
- Auto-generated unique patient ID
- Personal information (DOB, gender, address, phone)
- Medical information (blood group, allergies, chronic diseases, previous surgeries)
- Emergency contact details

### Doctor
- Specialization and qualification
- Years of experience
- Consultation fee

### Appointment
- Links patient and doctor
- Date and time
- Status (SCHEDULED, COMPLETED, NO_SHOW, CANCELLED)
- Support for follow-up appointments

### MedicalRecord
- Diagnosis notes
- Prescription details
- File upload for medical reports
- Additional notes

### DoctorAvailability
- Lunch breaks (max 1 hour)
- Unavailable dates and times
- Reason for unavailability

## Key Features Implementation

### Patient ID Generation
- Automatically generated in format P00001, P00002, etc.
- Sequential numbering
- Unique constraint enforced

### Appointment Booking
- Checks doctor availability before booking
- Prevents double-booking (same doctor, date, time)
- Validates against doctor's unavailable periods

### Doctor Availability
- Doctors can set lunch breaks (limited to 1 hour)
- Mark specific dates/times as unavailable
- System checks availability during appointment booking

### Role-Based Access Control
- Custom decorator `@role_required()` for view protection
- Automatic redirection based on user role after login
- Role-specific navigation menus

## Usage Guide

### For Receptionists

1. **Register a New Patient**
   - Navigate to "Register Patient"
   - Fill in personal, medical, and emergency contact information
   - System auto-generates unique patient ID

2. **Create Appointment**
   - Select patient and doctor
   - Choose date and time
   - System validates doctor availability
   - Prevents double-booking

3. **Manage Appointments**
   - View all appointments with filters
   - Reschedule appointments
   - Cancel appointments

### For Doctors

1. **View Appointments**
   - Dashboard shows today's appointments
   - Filter by status (scheduled, completed, no-show)

2. **Add Medical Records**
   - Click "Add Record" on appointment
   - Enter diagnosis and prescription
   - Upload medical reports (optional)

3. **Manage Availability**
   - Set lunch breaks (max 1 hour)
   - Mark unavailable dates/times
   - Add reason for unavailability

4. **Create Follow-ups**
   - From any appointment, create follow-up
   - Automatically links to parent appointment

### For Patients

1. **View History**
   - Timeline view of all appointments
   - Access medical records
   - View prescriptions and reports

2. **Check Doctor Availability**
   - Select doctor and date
   - View unavailable times and booked slots
   - Note: Cannot book directly (contact receptionist)

## Design Features

- **Modern UI**: Clean, professional medical theme
- **Responsive Design**: Works on desktop and mobile
- **Color-Coded Status**: Visual badges for appointment status
- **Timeline View**: Patient history in chronological order
- **Card-Based Layout**: Information organized in cards
- **Gradient Buttons**: Modern, interactive buttons
- **Alert Messages**: User feedback for all actions

## Security Features

- Role-based access control
- Password hashing (Django default)
- CSRF protection
- Login required for all views (except login page)
- Permission checks on all sensitive operations

## Future Enhancements

- Email notifications for appointments
- SMS reminders
- Online appointment booking for patients
- Prescription printing
- Medical report analytics
- Billing and payment integration
- Multi-language support

## Troubleshooting

### Issue: Static files not loading
```bash
python manage.py collectstatic
```

### Issue: Database errors
```bash
# Delete db.sqlite3 and migrations
python manage.py makemigrations
python manage.py migrate
python manage.py setup_demo_data
```

### Issue: Port already in use
```bash
python manage.py runserver 8001
```

## License

This project is created for educational purposes.

## Support

For issues or questions, please contact the development team.

---

**SwasthyaCare** - Caring for your health, managing with ease! 🏥
