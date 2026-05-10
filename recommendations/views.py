from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .forms import RecommendationForm


@login_required(login_url='login')
def recommendation_form(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden("403 Forbidden")

    if request.method == 'POST':
        form = RecommendationForm(request.POST)

        if form.is_valid():
            fur_conditions = form.cleaned_data.get('fur_conditions') or []
            skin_conditions = form.cleaned_data.get('skin_conditions') or []
            additional_conditions = form.cleaned_data.get('additional_conditions') or []

            selected_conditions = fur_conditions + skin_conditions + additional_conditions

            request.session['recommendation_input'] = {
                'animal_type': form.cleaned_data['animal_type'],
                'conditions': selected_conditions,
            }

            return redirect('recommendations:recommendation_result')

    else:
        form = RecommendationForm()

    return render(request, 'recommendations/recommendation_form.html', {
        'form': form
    })


@login_required(login_url='login')
def recommendation_result(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden("403 Forbidden")

    recommendation_input = request.session.get('recommendation_input')

    if not recommendation_input:
        return HttpResponseForbidden("403 Forbidden")

    return render(request, 'recommendations/recommendation_result.html', {
        'recommendation_input': recommendation_input
    })