# ports/user_repository.py

from abc import ABC, abstractmethod


class UserRepository(ABC):

    @abstractmethod
    def get_all_users(self):
        pass
