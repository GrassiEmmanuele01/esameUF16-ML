"""Casi d'uso dello user-service.

``UserService`` orchestra le regole di business e dipende esclusivamente
dall'astrazione :class:`UserRepository`. È agnostico rispetto a HTTP e al
backend di persistenza concreto.
"""

from __future__ import annotations

from typing import Any

from common import iso_now, new_uuid

from .errors import EmailAlreadyExists, UserNotFound
from .models import Role, User, normalize_email
from .repository import UserRepository
from .validators import validate_create, validate_update


class UserService:
    """Servizio applicativo per la gestione degli utenti."""

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    # ------------------------------- create ------------------------------- #

    def create_user(self, payload: Any) -> User:
        data = validate_create(payload)
        email = normalize_email(data["email"])

        if self._repo.find_by_email(email) is not None:
            raise EmailAlreadyExists(email)

        now = iso_now()
        user = User(
            id=new_uuid(),
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=email,
            company=data["company"],
            role=data["role"],
            created_at=now,
            updated_at=now,
        )
        self._repo.add(user)
        return user

    # -------------------------------- read -------------------------------- #

    def get_user(self, user_id: str) -> User:
        user = self._repo.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def list_users(
        self,
        *,
        role: Any = None,
        email: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        role_filter = self._coerce_role(role) if role else None
        email_filter = normalize_email(email) if email else None
        return self._repo.list(
            role=role_filter, email=email_filter, page=page, page_size=page_size
        )

    # ------------------------------- update ------------------------------- #

    def replace_user(self, user_id: str, payload: Any) -> User:
        return self._apply_update(user_id, payload, partial=False)

    def update_user(self, user_id: str, payload: Any) -> User:
        return self._apply_update(user_id, payload, partial=True)

    def _apply_update(self, user_id: str, payload: Any, *, partial: bool) -> User:
        existing = self._repo.get(user_id)
        if existing is None:
            raise UserNotFound(user_id)

        data = validate_update(payload, partial=partial)

        # Controllo univocità email escludendo l'utente stesso (REQ-USR-B01).
        if "email" in data:
            new_email = normalize_email(data["email"])
            owner = self._repo.find_by_email(new_email)
            if owner is not None and owner.id != user_id:
                raise EmailAlreadyExists(new_email)

        updated = existing.with_updates(**data, updated_at=iso_now())
        self._repo.update(updated)
        return updated

    # ------------------------------- delete ------------------------------- #

    def delete_user(self, user_id: str) -> None:
        if not self._repo.delete(user_id):
            raise UserNotFound(user_id)

    # ------------------------------- helpers ------------------------------ #

    @staticmethod
    def _coerce_role(role: Any) -> Role:
        from common import ValidationError

        if isinstance(role, Role):
            return role
        try:
            return Role(role)
        except ValueError:
            raise ValidationError(
                f"'role' deve essere uno tra {[r.value for r in Role]}",
                details={"field": "role"},
            ) from None
