"""
Unit tests for auth models and security utilities.
"""
import pytest

from backend.core.security import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_session_token,
    validate_email,
    validate_password,
)
from backend.models.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
    SessionInfo,
    UpdatePreferencesRequest,
)


# ── Security Tests ────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "test_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        password = "test_password_123"
        hashed = hash_password(password)
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self):
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # bcrypt or salted SHA-256 should produce different hashes
        assert hash1 != hash2

    def test_empty_password_verification_fails(self):
        hashed = hash_password("real_password")
        assert not verify_password("", hashed)


class TestSessionToken:
    def test_generate_token(self):
        raw, token_hash = generate_session_token()
        assert raw
        assert token_hash
        assert raw != token_hash
        assert len(token_hash) == 64  # SHA-256 hex

    def test_hash_consistency(self):
        raw, token_hash = generate_session_token()
        assert hash_session_token(raw) == token_hash

    def test_unique_tokens(self):
        tokens = set()
        for _ in range(100):
            raw, _ = generate_session_token()
            tokens.add(raw)
        assert len(tokens) == 100


class TestEmailValidation:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_email_lowercased(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_email_stripped(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_invalid_no_at(self):
        with pytest.raises(ValueError):
            validate_email("not-an-email")

    def test_invalid_no_domain(self):
        with pytest.raises(ValueError):
            validate_email("user@")

    def test_invalid_no_dot(self):
        with pytest.raises(ValueError):
            validate_email("user@localhost")

    def test_invalid_too_long(self):
        with pytest.raises(ValueError):
            validate_email("a" * 250 + "@example.com")


class TestPasswordValidation:
    def test_valid_password(self):
        validate_password("strong_password")  # Should not raise

    def test_short_password(self):
        with pytest.raises(ValueError):
            validate_password("12345")

    def test_minimum_length(self):
        validate_password("123456")  # 6 chars, should pass


# ── Auth Model Tests ──────────────────────────────────────────────────────────

class TestRegisterRequest:
    def test_valid(self):
        req = RegisterRequest(
            email="user@example.com",
            password="password123",
            display_name="Test User",
        )
        assert req.email == "user@example.com"

    def test_password_too_short(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="12345",
                display_name="Test",
            )


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(email="user@example.com", password="password123")
        assert req.email == "user@example.com"


class TestUserResponse:
    def test_no_password_hash(self):
        user = UserResponse(
            id="test-id",
            email="user@example.com",
            display_name="Test User",
        )
        assert not hasattr(user, "password_hash")
        assert user.role == "user"
        assert user.is_active is True


class TestUpdatePreferencesRequest:
    def test_partial_update(self):
        req = UpdatePreferencesRequest(default_symbol="BTCUSDT", theme="dark")
        assert req.default_symbol == "BTCUSDT"
        assert req.theme == "dark"
        assert req.default_timeframe is None
