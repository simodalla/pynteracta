import time
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, SecretStr, field_serializer


class JwtTokenPayload(BaseModel):
    jti: str
    aud: str
    iss: str
    iat: float
    exp: float


class JwtTokenHeaders(BaseModel):
    kid: int
    typ: str | None = None


class ServiceAccountModel(BaseModel):
    type: str = "service_account"
    private_key_id: int = Field(serialization_alias="kid")
    private_key: SecretStr
    client_id: int = Field(serialization_alias="iss")
    aud: str = "injenia/portal-authenticator"
    algorithm: str = Field("RS512", serialization_alias="alg")
    token_expiration: int = 9
    jti: UUID = Field(default_factory=uuid4)

    @field_serializer("client_id")
    def serialize_client_id(self, client_id: int, _info) -> str:
        return str(client_id)

    @property
    def jwt_token_payload(self) -> dict:
        data = self.model_dump(mode="json", include=["jti", "aud", "client_id"], by_alias=True)
        now = datetime.now()
        current_timestamp = time.mktime(now.timetuple())
        expiration_timestamp = time.mktime(
            (now + timedelta(seconds=60 * self.token_expiration)).timetuple()
        )
        data.update({"iat": current_timestamp, "exp": expiration_timestamp})
        jwt_token_payload = JwtTokenPayload(**data)
        return jwt_token_payload.model_dump(mode="json")

    @property
    def jwt_token_headers(self) -> dict:
        data = self.model_dump(mode="json", include=["private_key_id"], by_alias=True)
        jwt_headers = JwtTokenHeaders(**data).model_dump(mode="json")
        return jwt_headers
