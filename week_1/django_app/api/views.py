# django_app/views.py

from django.http import JsonResponse
from adapters.django_user_repo import DjangoUserRepository
from application.get_users import get_users


def get_users_view(request):
    repo = DjangoUserRepository()

    users = get_users(repo)

    data = [{"id": u.id, "name": u.name} for u in users]

    return JsonResponse(data, safe=False)
