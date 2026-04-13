from fastapi import Request, HTTPException
import os


async def get_current_user(request: Request) -> str:
    # Minimal stub to allow the app to run without Clerk properly configured
    # In production, this would verify JWT tokens from Clerk
    # For now, it returns 'guest_user' if CLERK_SECRET_KEY is missing
    auth_header = request.headers.get("Authorization")
    if not auth_header and not os.environ.get("CLERK_SECRET_KEY"):
        return "guest_user"

    # Simple logic to extract user_id if token is present (placeholder)
    # Real implementation would use clerk_client.authenticate_request(request)
    return "guest_user"
