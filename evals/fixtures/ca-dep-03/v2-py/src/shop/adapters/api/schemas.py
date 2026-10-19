from pydantic import BaseModel


class MemberResponse(BaseModel):
    id: str
    email: str
