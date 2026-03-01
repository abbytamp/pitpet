from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from pet.models import Pet

@login_required
def add_pet(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        species = request.POST.get('species')
        breed = request.POST.get('breed')
        weight = request.POST.get('weight')
        age = request.POST.get('age')

        Pet.objects.create(
            owner=request.user, # otomatis milik user login
            name=name,
            species=species,
            breed=breed,
            weight=weight,
            age=age
        )
        return redirect('profile')  # balik ke halaman profile

    return render(request, 'user_profile/add_pet.html')