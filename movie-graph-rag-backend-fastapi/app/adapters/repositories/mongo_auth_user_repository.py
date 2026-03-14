from datetime import datetime

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.domain.entities.auth_user import AuthUser
from app.domain.ports.auth_user_repository import AuthUserRepositoryPort


class MongoAuthUserRepositoryAdapter(AuthUserRepositoryPort):
    def __init__(self, db: Database) -> None:
        self.collection: Collection = db["user"]
        self.collection.create_index("email", unique=True)

    def _to_entity(self, document: dict) -> AuthUser:
        return AuthUser(
            id=str(document["_id"]),
            email=document["email"],
            name=document["name"],
            role=document.get("role", "user"),
            password_hash=document["password_hash"],
            created_at=document.get("created_at", datetime.utcnow()),
        )

    def find_by_email(self, email: str) -> AuthUser | None:
        document = self.collection.find_one({"email": email.lower()})
        if not document:
            return None
        return self._to_entity(document)

    def find_by_id(self, user_id: str) -> AuthUser | None:
        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None

        document = self.collection.find_one({"_id": object_id})
        if not document:
            return None
        return self._to_entity(document)

    def create(
        self,
        email: str,
        name: str,
        password_hash: str,
        role: str = "user",
    ) -> AuthUser:
        now = datetime.utcnow()
        document = {
            "email": email.lower(),
            "name": name,
            "role": role,
            "password_hash": password_hash,
            "created_at": now,
        }

        try:
            result = self.collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise ValueError("Email already registered") from exc

        created = self.collection.find_one({"_id": result.inserted_id})
        if not created:
            raise RuntimeError("Failed to create user")
        return self._to_entity(created)
