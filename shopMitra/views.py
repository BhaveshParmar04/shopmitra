from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from .models import *
from django.core.mail import send_mail
from razorpay import Client
from math import ceil
from django.urls import reverse
from django.conf import settings
import json, razorpay
from .utils import calculate_cart_amount
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        data = json.loads(request.body)
        razorpay_order_id = data.get("razorpay_order_id")
        payment_id = data.get("razorpay_payment_id")
        signature = data.get("razorpay_signature")

        # Verify the payment signature
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            # Payment is successful
            return HttpResponse("Payment successful")
        except Exception as e:
            return HttpResponseBadRequest("Payment verification failed")

    return HttpResponseBadRequest("Invalid request")


razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)
# Create your views here.
def index(request):
    # All unique categories
    categories = Product.objects.values_list('category', flat=True).distinct()

    AllProducts = []

    for cat in categories:
        prods = Product.objects.filter(category=cat)
        n = len(prods)
        nSlides = ceil(n / 4)  

        AllProducts.append([prods, range(1, nSlides), nSlides, cat])

    return render(request, 'shopMitra/index.html', {'AllProducts': AllProducts})

    
def about(request):
    return render(request, 'shopMitra/about.html')


def contact(request):
    thank = False
    if request.method=="POST":
        name=request.POST.get('name','')
        email=request.POST.get('email','')
        phone=request.POST.get('phone','')
        desc=request.POST.get('desc','')
        contact=Contact(name=name, email=email, phone=phone, desc=desc)
        contact.save()
        thank = True
        #return redirect('/contact')
    return render(request, 'shopMitra/contact.html', {'thank': thank})

def search(request):
    query = request.GET.get('query')

    if query:
        products = Product.objects.filter(
            product_name__icontains=query
        )
    else:
        products = Product.objects.none()

    return render(request, "shopMitra/search.html", {
        "products": products,
        "query": query
    })
    
@login_required
def tracker(request):
    if request.method=="POST":
        orderId = request.POST.get('orderid','')
        email = request.POST.get('email','')
        try:
            order = Orders.objects.filter(order_id=orderId, email=email)
            if len(order)>0:
                update = OrderUpdate.objects.filter(order_id=orderId)
                updates = []
                for item in update:
                    updates.append({'text': item.update_desc, 'time': item.timestamp})
                    response = json.dumps([updates, order[0].items_json], default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{}')
        except Exception as e:
           return HttpResponse('{}')
    return render(request, 'shopMitra/tracker.html')


def productview(request, id):
    # Fetch the products using the id
    product = Product.objects.get(id=id)
    print(product)
    return render(request, 'shopMitra/productview.html', {'product': product})
       


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.conf import settings
import razorpay
import os

@login_required
def checkout(request):
    if request.method == "POST":
        
        razorpay_client = razorpay.Client(
            auth=(
                os.environ.get("RAZORPAY_KEY_ID"),
                os.environ.get("RAZORPAY_KEY_SECRET")
            )
        )

        items_json = request.POST.get("itemsjson")
        name = request.POST.get("name")
        email = request.POST.get("email")
        address = request.POST.get("address1", "") + " " + request.POST.get("address2", "")
        city = request.POST.get("city")
        state = request.POST.get("state")
        zip_code = request.POST.get("zip")
        phone = request.POST.get("phone")
        payment_method = request.POST.get("payment_method")

        existing_order_id = request.session.get("razorpay_order_id")

        if existing_order_id:
            order = get_object_or_404(Orders, order_id=existing_order_id)
        else:
            order = Orders.objects.create(
                items_json=items_json,
                name=name,
                email=email,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                payment_method=payment_method,
                payment_status="PENDING"
            )
            request.session["razorpay_order_id"] = order.order_id

        if payment_method == "ONLINE":

            amount = calculate_cart_amount(items_json)

            if amount <= 0:
                return render(request, "shopMitra/checkout.html", {
                    "error": "Cart is empty"
                })

            if not order.razorpay_order_id:
                razorpay_order = razorpay_client.order.create({
                    "amount": amount * 100,  # paise
                    "currency": "INR",
                    "payment_capture": 1
                })

                order.razorpay_order_id = razorpay_order["id"]
                order.save()

            return render(request, "shopMitra/payment.html", {
                "order": order,
                "razorpay_key": os.environ.get("RAZORPAY_KEY_ID"),
                "razorpay_order_id": order.razorpay_order_id,
                "amount": amount * 100
            })

        request.session.pop("razorpay_order_id", None)

        return render(request, "shopMitra/checkout.html", {
            "thank": True,
            "id": order.order_id
        })

    return render(request, "shopMitra/checkout.html")

def signup(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect('signup')
    
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        user.save()

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, 'shopMitra/signup.html')


def send_email(request):
    try:
        send_mail(
            subject='Test email from Django',
            message='This is a plain-text test email.',
            from_email=settings.DEFAULT_FROM_EMAIL, 
            recipient_list=['bhaveshparmar.work@gmail.com'],
            fail_silently=False,
        )
        return HttpResponse("Email sent (check inbox/ spam).")
    except Exception as e:
        return HttpResponse(f"Error sending email: {e}")

@login_required
def custom_logout(request):
    logout(request)
    messages.success(request, "Logout successfully!")
    return redirect('login')


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        try:
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            # Verify signature
            razorpay_client.utility.verify_payment_signature({
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature
            })

            # Fetch order from DB
            order = Orders.objects.get(razorpay_order_id=razorpay_order_id)

            #  Update order
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.payment_status = "PAID"
            order.save()

            return render(request, "shopMitra/payment_success.html", {
                "order": order
            })

        except Exception as e:
            print("PAYMENT ERROR:", e)
            return HttpResponseBadRequest("Payment Failed")

    return HttpResponseBadRequest("Invalid Request")
