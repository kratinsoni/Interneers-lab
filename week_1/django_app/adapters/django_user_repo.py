# adapters/django_user_repo.py

from ports.user_repository import UserRepository
from api.models import UserModel
from domain.user import User


class DjangoUserRepository(UserRepository):

    def get_all_users(self):
        users = UserModel.objects.all()

        return [User(id=u.id, name=u.name) for u in users]
