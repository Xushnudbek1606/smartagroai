from fastapi import APIRouter

from app.api.v1 import (
    admin,
    agronomists,
    auth,
    chat,
    crops,
    diagnoses,
    farms,
    internal,
    invitations,
    notifications,
    public,
    users,
    weather,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(invitations.router)
api_router.include_router(farms.router)
api_router.include_router(crops.router)
api_router.include_router(diagnoses.router)
api_router.include_router(weather.router)
api_router.include_router(chat.router)
api_router.include_router(agronomists.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(public.router)
api_router.include_router(internal.router)
