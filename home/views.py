from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError, models
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from .models import Student, AdminUser, Payment, MONTH_CHOICES
import qrcode
import base64
from io import BytesIO
from urllib.parse import quote
from django.views.decorators.cache import never_cache


# ---------------------------
# Helpers / Guards
# ---------------------------
def _is_logged_in(request):
    return request.session.get("role") in {"student", "admin"}

def _is_admin(request):
    return request.session.get("role") == "admin"

def _is_student(request):
    return request.session.get("role") == "student"

def require_role(role):
    """Tiny guard decorator for 'student' or 'admin' role."""
    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if request.session.get("role") != role:
                messages.error(request, "Unauthorized. Please log in with the correct account.")
                return redirect("login")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# ---------------------------
# Static pages
# ---------------------------
def home(request):
    return render(request, "home.html")

def about(request):
    return render(request, "about.html")

def contact(request):
    return render(request, "contact.html")

def rooms(request):
    return render(request, "rooms.html")

def booking(request):
    return render(request, "booking.html")


# ---------------------------
# Signup
# ---------------------------
def signup(request):
    if request.method == "POST":
        # --- Student signup ---
        if "fullname" in request.POST:
            fullname = request.POST.get("fullname", "").strip()
            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password", "")
            fathername = request.POST.get("fathername", "").strip()
            address = request.POST.get("address", "").strip()
            aadhar = request.POST.get("aadhar", "").strip()
            college = request.POST.get("college", "").strip()
            studentphone = request.POST.get("studentphone", "").strip()
            fatherphone = request.POST.get("fatherphone", "").strip()
            joiningdate = request.POST.get("joiningdate", "").strip()

            # Required fields
            required = [
                ("fullname", fullname), ("fathername", fathername), ("address", address),
                ("aadhar", aadhar), ("college", college), ("studentphone", studentphone),
                ("fatherphone", fatherphone), ("joiningdate", joiningdate),
                ("email", email), ("password", password)
            ]
            for label, val in required:
                if not val:
                    messages.error(request, f"{label.capitalize()} is required.")
                    return redirect("signup")

            # Email format
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
                return redirect("signup")

            # Aadhar basic length check
            if len(aadhar) != 12 or not aadhar.isdigit():
                messages.error(request, "Aadhar must be exactly 12 digits.")
                return redirect("signup")

            # Phone quick checks
            if not (10 <= len(studentphone.replace("+", "")) <= 15):
                messages.error(request, "Student phone must be 10 to 15 digits.")
                return redirect("signup")
            if not (10 <= len(fatherphone.replace("+", "")) <= 15):
                messages.error(request, "Father phone must be 10 to 15 digits.")
                return redirect("signup")

            # Joining date sanity
            try:
                datetime.strptime(joiningdate, "%Y-%m-%d")
            except ValueError:
                messages.error(request, "Joining date must be in YYYY-MM-DD format.")
                return redirect("signup")

            # Unique checks
            if Student.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return redirect("signup")
            if Student.objects.filter(aadhar=aadhar).exists():
                messages.error(request, "Aadhar already registered.")
                return redirect("signup")

            # Photo validations
            photo = request.FILES.get("photo")
            if photo:
                if photo.size > (2 * 1024 * 1024):
                    messages.error(request, "Photo must be less than 2 MB.")
                    return redirect("signup")
                if not str(photo.content_type).lower().startswith(("image/")):
                    messages.error(request, "Only image files are allowed for photo.")
                    return redirect("signup")

            # Create student
            student = Student(
                fullname=fullname,
                fathername=fathername,
                address=address,
                aadhar=aadhar,
                college=college,
                studentphone=studentphone,
                fatherphone=fatherphone,
                joiningdate=joiningdate,
                email=email,
                photo=photo,
            )
            student.set_password(password)

            try:
                student.save()
                messages.success(request, "Student account created successfully! Please log in.")
                return redirect("login")
            except IntegrityError:
                messages.error(request, "Duplicate entry. Please check your Email/Aadhar.")
                return redirect("signup")

        # --- Admin signup ---
        elif "adminname" in request.POST:
            adminname = request.POST.get("adminname", "").strip()
            password = request.POST.get("password", "")
            conf = request.POST.get("confirmpassword", "")

            if not adminname or not password:
                messages.error(request, "Admin name and password are required.")
                return redirect("signup")

            if password != conf:
                messages.error(request, "Passwords do not match.")
                return redirect("signup")

            if AdminUser.objects.filter(adminname=adminname).exists():
                messages.error(request, "Admin username already exists.")
                return redirect("signup")

            admin = AdminUser(adminname=adminname)
            admin.set_password(password)
            admin.save()
            messages.success(request, "Admin account created! Please log in.")
            return redirect("login")

        messages.error(request, "Invalid signup request.")
        return redirect("signup")

    return render(request, "signup.html")


# ---------------------------
# Login / Logout
# ---------------------------
def login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Student login
        student = Student.objects.filter(email=username).first() or \
                  Student.objects.filter(fullname=username).first()
        if student and student.check_password(password):
            request.session.flush()  # flush old session
            request.session["role"] = "student"
            request.session["student_id"] = student.id
            return redirect("student_payments_self")

        # Admin login
        # admin = AdminUser.objects.filter(adminname=username).first()
        # if admin and admin.check_password(password):
        #     request.session.flush()  # flush old session
        #     request.session["role"] = "admin"
        #     request.session["admin_id"] = admin.id
        #     admin.last_login = timezone.now()
        #     admin.save(update_fields=["last_login"])
        #     return redirect("admin_student_list")

        messages.error(request, "Invalid username or password.")
        return redirect("login")

    return render(request, "login.html")


def logout(request):
    request.session.flush()  # clear all session
    messages.success(request, "Logged out successfully.")
    return redirect("login")



# ---------------------------
# Student Area
# ---------------------------
@never_cache
@require_role("student")
def student_payments_self(request):
    student_id = request.session.get("student_id")
    if not student_id:
        return redirect("login")

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        month = request.POST.get("month")
        amount = request.POST.get("amount")
        if month and amount:
            Payment.objects.create(student=student, month=month, amount=amount)
            return redirect("student_payments_self")

    payments = student.payments.all().order_by("-date_paid")

    return render(request, "students_payments.html", {
        "student": student,
        "payments": payments,
        "is_admin": False,
        "is_student": True
    })


# ---------------------------
# Admin Area
# ---------------------------
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Example: hard-coded admin credentials
        if username == "1234" and password == "1234":
            request.session["role"] = "admin"
            request.session["admin_id"] = 1
            return redirect("admin_student_list")
        else:
            messages.error(request, "Invalid admin credentials.")

    # Render the combined login page
    return render(request, "login.html")


@never_cache
def manage_payment(request, student_id):
    """Admin Add/Edit payment for a specific student"""
    if "admin_id" not in request.session:
        return redirect("admin_login")

    # Fetch student
    student = get_object_or_404(Student, id=student_id)

    # If editing an existing payment
    payment_id = request.GET.get("payment_id")
    payment = None
    if payment_id:
        payment = get_object_or_404(Payment, id=payment_id, student=student)

    if request.method == "POST":
        month = request.POST.get("month")
        amount = request.POST.get("amount")

        if payment:
            # Update existing payment
            payment.month = month
            payment.amount = amount
            payment.save()
        else:
            # Add new payment
            Payment.objects.create(student=student, month=month, amount=amount)

        # After save → back to student’s payments list
        return redirect("admin_student_payments", student_id=student.id)

    # Fetch all payments for this student (so admin can see history below form)
    payments = Payment.objects.filter(student=student).order_by("-id")

    return render(request, "manage_payment.html", {
        "student": student,
        "payment": payment,
        "payments": payments,
        "student_id": student.id,   # ✅ So template can use in `{% url %}`
    })


# ---------------------------
# Admin – view any student's payments
# ---------------------------
@never_cache
@require_role("admin")
def admin_student_payments(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        month = request.POST.get("month")
        amount = request.POST.get("amount")
        if month and amount:
            Payment.objects.create(student=student, month=month, amount=amount)
            return redirect("admin_student_payments", student_id=student.id)

    payments = student.payments.all().order_by("-date_paid")
    return render(request, "students_payments.html", {
        "student": student,
        "payments": payments,
        "is_admin": True,
        "is_student": False
    })

def delete_payment(request, payment_id):
    """Admin delete a payment"""
    if "admin_id" not in request.session:
        return redirect("admin_login")

    payment = get_object_or_404(Payment, id=payment_id)
    student_id = payment.student.id
    payment.delete()

    return redirect("admin_student_payments", student_id=student_id)

@never_cache
@require_role("admin")
def admin_student_list(request):
    students = Student.objects.all()
    return render(request, "admin_student_list.html", {"students": students})


#payment environment

PLAN_AMOUNTS = {
    "daily": 240,
    "monthly": 5500,
    "yearly": 55000,
}

EDITABLE_PLANS = ["monthly", "yearly"]  # ✅ user can edit only these


def generate_qr_code(data: str) -> str:
    """Generate base64 QR code from given string."""
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def book_now(request, plan):
    if plan not in PLAN_AMOUNTS:
        return HttpResponse("Invalid plan", status=400)

    amount = PLAN_AMOUNTS[plan]
    editable = plan in EDITABLE_PLANS

    # UPI details
    upi_id = "9381422218@naviaxis"   # 👉 replace with your UPI
    payee_name = "Sai Krishna Hostel"
    note = f"{plan.capitalize()} Hostel Fee"

    # Encode note properly
    note_encoded = quote(note)

    # Default UPI link
    upi_link = (
        f"upi://pay?pa={upi_id}"
        f"&pn={quote(payee_name)}"
        f"&am={amount}"
        f"&cu=INR"
        f"&tn={note_encoded}"
    )

    # Generate QR code
    qr_code = generate_qr_code(upi_link)

    context = {
        "plan": plan,
        "amount": amount,
        "editable": editable,
        "upi_link": upi_link,
        "upi_id": upi_id,
        "payee_name": payee_name,
        "note": note,
        "qr_code": qr_code,
    }
    return render(request, "book_payment.html", context)