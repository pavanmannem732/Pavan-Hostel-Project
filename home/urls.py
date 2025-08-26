from django.urls import path
from home import views

urlpatterns = [
    # Public
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("rooms/", views.rooms, name="rooms"),
    path("contact/", views.contact, name="contact"),

    # Student
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("booking/", views.booking, name="booking"),
    path("my-payments/", views.student_payments_self, name="student_payments_self"),  # self only

    # Admin
    path("myadmin/login/", views.admin_login, name="admin_login"),
    path("myadmin/students/", views.admin_student_list, name="admin_student_list"),
    path("myadmin/student/<int:student_id>/payments/", views.admin_student_payments, name="admin_student_payments"),
    path("myadmin/manage-payment/<int:student_id>/", views.manage_payment, name="manage_payment"),
    path("delete-payment/<int:payment_id>/", views.delete_payment, name="delete_payment"),
   
    #payment 
    path("book/<str:plan>/", views.book_now, name="book_now"),

]


