import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from .models import Menu, Order, OrderItem, Cart, CartItem
from django.db.models import Sum, Count
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from datetime import datetime


# ================= IMAGE =================
def get_food_image(name):
    filename = name.lower().replace(' ', '-')
    return static(f"images/{filename}.jpg")


# ================= HOME =================
@never_cache
@login_required(login_url='/login/')
def home(request):
    items = Menu.objects.all()

    for item in items:
        item.image = get_food_image(item.name)

    return render(request, 'index.html', {'items': items})


# ================= SIGNUP =================
@never_cache
def signup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already exists'})

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('/')

    return render(request, 'signup.html')


# ================= LOGIN =================
@never_cache
def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {'error': 'Invalid Credentials'})

    return render(request, 'login.html')


# ================= LOGOUT =================
@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    return redirect('/login/')


# ================= ADD TO CART =================
@login_required(login_url='/login/')
def add_to_cart(request, item_id):

    item = get_object_or_404(Menu, id=item_id)

    qty = request.GET.get('qty')

    try:
        qty = int(qty)
    except:
        qty = 1

    if qty < 1:
        qty = 1

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        item=item,
        defaults={'quantity': qty}
    )

    if not created:
        cart_item.quantity += qty
        cart_item.save()

    return redirect('/cart/')


# ================= VIEW CART =================
@never_cache
@login_required(login_url='/login/')
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart)

    total = sum(i.item.price * i.quantity for i in items)

    return render(request, 'cart.html', {
        'items': items,
        'total': total
    })


# ================= REMOVE FROM CART =================
@login_required(login_url='/login/')
def remove_from_cart(request, item_id):

    cart, _ = Cart.objects.get_or_create(user=request.user)

    CartItem.objects.filter(
        cart=cart,
        item_id=item_id
    ).delete()

    return redirect('/cart/')


# ================= CHECKOUT =================
@login_required(login_url='/login/')
def checkout(request):

    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart)

    if not items.exists():
        return redirect('/cart/')

    total = 0
    bill_items = []

    order = Order.objects.create(
        user=request.user,
        total=0
    )

    for i in items:

        item_total = i.item.price * i.quantity

        OrderItem.objects.create(
            order=order,
            item=i.item,
            quantity=i.quantity,
            total=item_total
        )

        bill_items.append({
            'name': i.item.name,
            'price': i.item.price,
            'qty': i.quantity,
            'total': item_total
        })

        total += item_total

    gst = total * 0.18
    final_total = total + gst

    order.total = final_total
    order.save()

    request.session['bill'] = {
        'items': bill_items,
        'subtotal': total,
        'gst': round(gst, 2),
        'total': round(final_total, 2)
    }

    request.session['order_id'] = order.id

    items.delete()

    return render(request, 'bill.html', {
        'items': bill_items,
        'base_total': total,
        'gst': round(gst, 2),
        'total': round(final_total, 2)
    })


# ================= PAYMENT =================
@login_required(login_url='/login/')
def payment(request):

    order_id = request.session.get('order_id')

    if not order_id:
        return redirect('/')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except:
        return redirect('/')

    return render(request, 'payment.html', {'order': order})


# ================= PAYMENT SUCCESS =================
@csrf_exempt
@login_required(login_url='/login/')
def payment_success(request):

    if request.method != "POST":
        return JsonResponse({"status": "error"})

    order_id = request.session.get('order_id')

    if not order_id:
        return JsonResponse({"status": "error", "msg": "No order found"})

    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order.status = "Paid"
        order.save()

        request.session.pop('order_id', None)
        request.session.pop('bill', None)

        return JsonResponse({"status": "ok"})

    except:
        return JsonResponse({"status": "error"})


# ================= SUCCESS PAGE =================
@login_required(login_url='/login/')
def success_page(request):
    return render(request, 'success.html')


# ================= ORDER HISTORY =================
@login_required(login_url='/login/')
def order_history(request):

    orders = Order.objects.filter(user=request.user).order_by('-id')

    order_data = []

    for order in orders:
        items = OrderItem.objects.filter(order=order)

        order_data.append({
            'order': order,
            'items': items
        })

    return render(request, 'history.html', {'order_data': order_data})




# ================= REORDER =================
@login_required(login_url='/login/')
def reorder(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    cart, _ = Cart.objects.get_or_create(user=request.user)

    for i in items:
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=i.item,
            defaults={'quantity': i.quantity}
        )

        if not created:
            cart_item.quantity += i.quantity
            cart_item.save()

    return redirect('/cart/')
# ================= Dashboard =================
@staff_member_required
def admin_dashboard(request):
  # Total Orders
    total_orders = Order.objects.count()

    # Total Revenue
    
    revenue = round(Order.objects.aggregate(Sum('total'))['total__sum'] or 0, 2)
    # Recent orders (last 7)
    recent_orders = Order.objects.order_by('-created_at')[:7]
    
    # Simple labels + data for graph
    orders_by_date = Order.objects.values('created_at__date').annotate(count=Count('id')).order_by('created_at__date')

    labels = [str(i['created_at__date']) for i in orders_by_date]
    data = [i['count'] for i in orders_by_date]

    return render(request, 'admin_dashboard.html', {
        'total_orders': total_orders,
        'revenue': revenue,
        'labels': labels,
        'data': data,
        'recent_orders': recent_orders
    })
# ================= INVOICE =================
def download_invoice(request):

    bill = request.session.get('bill')

    if not bill:
        return HttpResponse("No bill found")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("FoodieFlow Invoice", styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))

    data = [["Item", "Price", "Qty", "Total"]]

    for i in bill['items']:
        data.append([i['name'], i['price'], i['qty'], i['total']])

    table = Table(data)
    elements.append(table)

    doc.build(elements)

    return response