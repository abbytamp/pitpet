from django.shortcuts import render
from accounts.models import Groomer

def groomer_list(request):
    groomers = Groomer.objects.select_related("user").all()
    return render(request, "groomer_list.html", {"groomers": groomers})