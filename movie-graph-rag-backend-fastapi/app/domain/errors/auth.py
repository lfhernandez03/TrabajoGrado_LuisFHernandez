class AuthError(Exception):
    pass


class EmailAlreadyRegisteredError(AuthError):
    def __init__(self) -> None:
        super().__init__("Email already registered")


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid credentials")


class UserNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__("User not found")


class PasswordTooLongError(AuthError):
    def __init__(self) -> None:
        super().__init__("Password cannot be longer than 72 bytes (UTF-8) for bcrypt")
