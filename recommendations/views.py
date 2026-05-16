from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .forms import RecommendationForm
from .utils import get_recommended_packages


def _split_conditions_by_category(conditions):
    fur_conditions = [
        condition for condition in conditions
        if condition in ["thick_long_fur", "dull_shedding_fur", "matted_fur"]
    ]

    skin_conditions = [
        condition for condition in conditions
        if condition in ["fleas", "fungus_irritation"]
    ]

    additional_conditions = [
        condition for condition in conditions
        if condition in ["long_nails", "dirty_ears", "styling"]
    ]

    return fur_conditions, skin_conditions, additional_conditions


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
        recommendation_input = request.session.get('recommendation_input')

        if recommendation_input:
            conditions = recommendation_input.get('conditions', [])
            fur_conditions, skin_conditions, additional_conditions = _split_conditions_by_category(conditions)

            form = RecommendationForm(initial={
                'animal_type': recommendation_input.get('animal_type'),
                'fur_conditions': fur_conditions,
                'skin_conditions': skin_conditions,
                'additional_conditions': additional_conditions,
            })
        else:
            form = RecommendationForm()

    return render(request, 'recommendations/recommendation_form.html', {
        'form': form
    })
    
@login_required(login_url='login')
def recommendation_start(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden("403 Forbidden")

    request.session.pop('recommendation_input', None)
    return redirect('recommendations:recommendation_form')

CONDITION_LABELS = {
    "thick_long_fur": "Bulu tebal/panjang",
    "dull_shedding_fur": "Bulu rontok/kusam",
    "matted_fur": "Bulu kusut/gimbal",
    "fleas": "Berkutu",
    "fungus_irritation": "Berjamur/iritasi",
    "long_nails": "Kuku panjang",
    "dirty_ears": "Telinga kotor",
    "styling": "Ingin styling/potong model",
}

@login_required(login_url='login')
def recommendation_result(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden("403 Forbidden")

    recommendation_input = request.session.get('recommendation_input')

    if not recommendation_input:
        return HttpResponseForbidden("403 Forbidden")

    animal_type = recommendation_input.get('animal_type')
    selected_conditions = recommendation_input.get('conditions', [])

    if not animal_type or not selected_conditions:
        return HttpResponseForbidden("403 Forbidden")

    recommended_packages = get_recommended_packages(
        animal_type=animal_type,
        selected_conditions=selected_conditions
    )

    selected_condition_labels = [
        CONDITION_LABELS.get(condition, condition)
        for condition in selected_conditions
    ]

    return render(request, 'recommendations/recommendation_result.html', {
        'animal_type': animal_type,
        'selected_conditions': selected_conditions,
        'selected_condition_labels': selected_condition_labels,
        'recommended_packages': recommended_packages,
    })