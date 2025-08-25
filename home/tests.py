from django.test import TestCase, Client
from django.urls import reverse
from home.models import Student, Payment

class HostelAppTests(TestCase):
    def setUp(self):
        # Test client
        self.client = Client()

        # Create a test student
        self.student = Student.objects.create(
            fullname="Test Student",
            fathername="Father Name",
            email="test@student.com",
            phone="1234567890",
            password="1234"  # assuming plain password for simplicity
        )

        # Admin credentials (hardcoded)
        self.admin_username = "admin"
        self.admin_password = "1234"

    # ----------------- Admin Tests -----------------
    def test_admin_login_redirect(self):
        response = self.client.post(
            reverse("admin_login"),
            {"username": self.admin_username, "password": self.admin_password},
            follow=True
        )
        self.assertRedirects(response, reverse("admin_student_list"))

    def test_invalid_admin_login(self):
        response = self.client.post(
            reverse("admin_login"),
            {"username": "wrong", "password": "wrong"},
            follow=True
        )
        self.assertContains(response, "Invalid admin credentials")

    def test_admin_can_see_students(self):
        # login admin
        session = self.client.session
        session['admin_id'] = 1
        session.save()

        response = self.client.get(reverse("admin_student_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Student")

    def test_admin_add_payment_for_student(self):
        session = self.client.session
        session['admin_id'] = 1
        session.save()

        response = self.client.post(
            reverse("manage_payment", args=[self.student.id]),
            {"amount": 5000, "month": "August"},
            follow=True
        )
        self.assertRedirects(response, reverse("admin_student_payments", args=[self.student.id]))
        self.assertTrue(Payment.objects.filter(student=self.student, month="August").exists())

    def test_admin_delete_payment(self):
        session = self.client.session
        session['admin_id'] = 1
        session.save()

        payment = Payment.objects.create(student=self.student, amount=5000, month="August")
        response = self.client.get(
            reverse("delete_payment", args=[payment.id]),
            follow=True
        )
        self.assertRedirects(response, reverse("admin_student_payments", args=[self.student.id]))
        self.assertFalse(Payment.objects.filter(id=payment.id).exists())

    # ----------------- Student Tests -----------------
    def test_student_login_success(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.student.email, "password": "1234"},
            follow=True
        )
        self.assertRedirects(response, reverse("student_payments_self"))

    def test_invalid_student_login(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.student.email, "password": "wrong"},
            follow=True
        )
        self.assertContains(response, "Invalid credentials")

    def test_student_payment_display(self):
        Payment.objects.create(student=self.student, amount=5000, month="August")
        self.client.post(reverse("login"), {"username": self.student.email, "password": "1234"}, follow=True)
        response = self.client.get(reverse("student_payments_self"))
        self.assertContains(response, "August")
        self.assertContains(response, "5000")
