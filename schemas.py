from pydantic import BaseModel, Field


class MemberCheckRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=8, max_length=30)


class MemberCheckResponse(BaseModel):
    is_member: bool
    user_id: int
    message: str

