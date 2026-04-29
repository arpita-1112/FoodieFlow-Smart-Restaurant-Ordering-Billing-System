from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path("reorder/<int:order_id>/", views.reorder, name="reorder"),
    path('cart/', views.view_cart, name='view_cart'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('dashboard/', views.admin_dashboard, name='dashboard'),

    path('checkout/', views.checkout, name='checkout'),
    path('payment/', views.payment, name='payment'),
    path("payment-success/", views.payment_success, name="payment_success"),   
    path('history/', views.order_history, name='order_history'),
    path("success/", views.success_page, name="success"),
    path('download/', views.download_invoice, name='download_invoice'),
]