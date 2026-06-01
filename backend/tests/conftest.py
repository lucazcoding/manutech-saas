"""
Fixtures globais compartilhadas por E2E e testes unitários.
Gera par RSA de teste uma única vez por sessão.
"""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from shared.shared.auth.jwt import create_access_token, hash_token, create_refresh_token_value


@pytest.fixture(scope="session")
def rsa_keys():
    """Par de chaves RSA gerado uma vez por sessão de testes."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return {"private": private_pem, "public": public_pem}


def make_token(private_key: str, user_id: int, role: str, name: str = "Test User") -> str:
    return create_access_token(
        payload={"sub": str(user_id), "role": role, "name": name},
        private_key=private_key,
    )


@pytest.fixture
def admin_token(rsa_keys) -> str:
    return make_token(rsa_keys["private"], user_id=1, role="admin", name="Admin Test")


@pytest.fixture
def supervisor_token(rsa_keys) -> str:
    return make_token(rsa_keys["private"], user_id=2, role="supervisor", name="Supervisor Test")


@pytest.fixture
def technician_token(rsa_keys) -> str:
    return make_token(rsa_keys["private"], user_id=3, role="technician", name="Technician Test")


@pytest.fixture
def attendant_token(rsa_keys) -> str:
    return make_token(rsa_keys["private"], user_id=4, role="attendant", name="Attendant Test")
