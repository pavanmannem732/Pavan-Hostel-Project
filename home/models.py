from django.db import models, IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

# ---------------------------
# Validators
# ---------------------------
aadhar_validator = RegexValidator(r'^\d{12}$', 'Aadhar must be exactly 12 digits.')
phone_validator = RegexValidator(r'^\+?\d{10,15}$', 'Phone number must be between 10 to 15 digits.')

# ---------------------------
# Month choices
# ---------------------------
MONTH_CHOICES = [
    ("January", "January"), ("February", "February"), ("March", "March"), ("April", "April"),
    ("May", "May"), ("June", "June"), ("July", "July"), ("August", "August"),
    ("September", "September"), ("October", "October"), ("November", "November"), ("December", "December")
]

# ---------------------------
# Student Model
# ---------------------------
class Student(models.Model):
    fullname = models.CharField(max_length=100)
    fathername = models.CharField(max_length=100)
    address = models.TextField()
    aadhar = models.CharField(max_length=12, unique=True, validators=[aadhar_validator])
    college = models.CharField(max_length=200)
    studentphone = models.CharField(max_length=15, validators=[phone_validator])
    fatherphone = models.CharField(max_length=15, validators=[phone_validator])
    joiningdate = models.DateField(default=timezone.now)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    password = models.CharField(max_length=128)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000)

    def set_password(self, raw_password):
        """Hashes and sets the password"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Checks a plain password against the stored hash"""
        return check_password(raw_password, self.password)

    def get_paid_amount(self, month):
        """Returns total amount paid for a given month (case-insensitive)"""
        total_paid = self.payments.filter(month__iexact=month).aggregate(Sum("amount"))["amount__sum"] or 0
        return total_paid

    def get_due_amount(self, month):
        """Returns remaining due for a given month"""
        return self.monthly_fee - self.get_paid_amount(month)

    def __str__(self):
        return self.fullname

# ---------------------------
# AdminUser Model
# ---------------------------
class AdminUser(models.Model):
    adminname = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.adminname

# ---------------------------
# Payment Model
# ---------------------------
class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    date_paid = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.student.fullname} • {self.month} • ₹{self.amount}"

    # class Meta:
    #     unique_together = ("student", "month")  # Ensures one record per student per month

# ---------------------------
# Signals
# ---------------------------
@receiver(post_save, sender=Payment)
def payment_made(sender, instance, created, **kwargs):
    if created:
        student = instance.student
        due = student.get_due_amount(instance.month)
        # Log/notify admin or student
        if due <= 0:
            print(f"✅ Payment complete for {student.fullname} in {instance.month}.")
        else:
            print(f"⚠️ {student.fullname} still owes ₹{due} for {instance.month}.")
