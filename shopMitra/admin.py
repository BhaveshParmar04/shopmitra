from django.contrib import admin
from .models import *

# change django admin name
admin.site.site_header = "ShopMitra Admin"
admin.site.site_title = "ShopMitra Admin Portal"
admin.site.index_title = "ShopMitra Administration"



# Register your models here.

admin.site.register(Product)
admin.site.register(Contact)
admin.site.register(Orders)
admin.site.register(OrderUpdate)