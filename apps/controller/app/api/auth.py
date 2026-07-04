from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.security.jwt_auth import create_token, verify_token
from app.security.call_stats import CallStats

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request, session: AsyncSession = Depends(get_db)):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    auth_service = AuthService(session)
    user = await auth_service.authenticate(username, password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session["user_id"] = str(user.id)
    request.session["username"] = user.username
    request.session["role"] = user.role

    token = create_token(str(user.id), user.username, user.role)

    return JSONResponse(content={
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role
        }
    })


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse(content={"message": "Logged out successfully"})


@router.get("/me")
async def get_me(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return JSONResponse(content={
        "id": user_id,
        "username": request.session.get("username"),
        "role": request.session.get("role")
    })


@router.post("/token")
async def get_token(request: Request):
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return JSONResponse(content=payload)


@router.get("/stats")
async def get_stats(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    stats = CallStats()
    result = stats.get_all_stats()
    return JSONResponse(content=result)
