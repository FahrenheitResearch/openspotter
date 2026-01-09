from typing import Dict, Set
from uuid import UUID
import json

from fastapi import WebSocket

from app.models.user import User, UserRole
from app.models.location import Location
from app.models.message import Message


class LocationManager:
    """Manages WebSocket connections for location sharing."""

    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.user_data: Dict[UUID, User] = {}

    async def connect(self, websocket: WebSocket, user: User):
        """Register a new WebSocket connection."""
        self.active_connections[user.id] = websocket
        self.user_data[user.id] = user

    def disconnect(self, websocket: WebSocket, user: User):
        """Remove a WebSocket connection."""
        if user.id in self.active_connections:
            del self.active_connections[user.id]
        if user.id in self.user_data:
            del self.user_data[user.id]

    async def broadcast_location(self, user: User, location: Location):
        """Broadcast a location update to relevant connected clients."""
        message = {
            "type": "location_update",
            "data": {
                "user_id": str(user.id),
                "callsign": user.callsign,
                "role": user.role.value,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "altitude": location.altitude,
                "heading": location.heading,
                "speed": location.speed,
                "timestamp": location.timestamp.isoformat(),
            },
        }

        for client_id, ws in list(self.active_connections.items()):
            if client_id == user.id:
                continue

            # Check visibility permissions
            client_user = self.user_data.get(client_id)
            if not client_user:
                continue

            can_see = False
            if location.visibility == "public":
                can_see = True
            elif location.visibility == "verified" and client_user.role in [
                UserRole.VERIFIED_SPOTTER,
                UserRole.COORDINATOR,
                UserRole.ADMIN,
            ]:
                can_see = True
            elif location.visibility == "coordinators" and client_user.role in [
                UserRole.COORDINATOR,
                UserRole.ADMIN,
            ]:
                can_see = True

            if can_see:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(ws, client_user)

    async def stop_sharing(self, user: User):
        """Broadcast that a user has stopped sharing their location."""
        message = {
            "type": "location_stopped",
            "data": {"user_id": str(user.id)},
        }

        for client_id, ws in list(self.active_connections.items()):
            if client_id != user.id:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


class ChatManager:
    """Manages WebSocket connections for chat."""

    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.user_data: Dict[UUID, User] = {}
        self.channel_subscriptions: Dict[UUID, Set[UUID]] = {}  # channel_id -> set of user_ids

    async def connect(self, websocket: WebSocket, user: User):
        """Register a new WebSocket connection."""
        self.active_connections[user.id] = websocket
        self.user_data[user.id] = user

    def disconnect(self, websocket: WebSocket, user: User):
        """Remove a WebSocket connection."""
        if user.id in self.active_connections:
            del self.active_connections[user.id]
        if user.id in self.user_data:
            del self.user_data[user.id]

        # Remove from all channel subscriptions
        for channel_id, subscribers in self.channel_subscriptions.items():
            subscribers.discard(user.id)

    async def join_channel(self, websocket: WebSocket, channel_id: UUID):
        """Subscribe to a channel."""
        user_id = None
        for uid, ws in self.active_connections.items():
            if ws == websocket:
                user_id = uid
                break

        if user_id:
            if channel_id not in self.channel_subscriptions:
                self.channel_subscriptions[channel_id] = set()
            self.channel_subscriptions[channel_id].add(user_id)

    async def leave_channel(self, websocket: WebSocket, channel_id: UUID):
        """Unsubscribe from a channel."""
        user_id = None
        for uid, ws in self.active_connections.items():
            if ws == websocket:
                user_id = uid
                break

        if user_id and channel_id in self.channel_subscriptions:
            self.channel_subscriptions[channel_id].discard(user_id)

    async def broadcast_message(self, sender: User, message: Message):
        """Broadcast a message to relevant connected clients."""
        msg_data = {
            "type": "chat_message",
            "data": {
                "id": str(message.id),
                "content": message.content,
                "sender": {
                    "id": str(sender.id),
                    "callsign": sender.callsign,
                    "role": sender.role.value,
                },
                "channel_id": str(message.channel_id) if message.channel_id else None,
                "recipient_id": str(message.recipient_id) if message.recipient_id else None,
                "latitude": message.latitude,
                "longitude": message.longitude,
                "created_at": message.created_at.isoformat(),
            },
        }

        if message.channel_id:
            # Broadcast to channel subscribers
            subscribers = self.channel_subscriptions.get(message.channel_id, set())
            for user_id in subscribers:
                ws = self.active_connections.get(user_id)
                if ws:
                    try:
                        await ws.send_json(msg_data)
                    except Exception:
                        pass
        elif message.recipient_id:
            # Send to DM recipient
            ws = self.active_connections.get(message.recipient_id)
            if ws:
                try:
                    await ws.send_json(msg_data)
                except Exception:
                    pass

            # Also send confirmation to sender
            sender_ws = self.active_connections.get(sender.id)
            if sender_ws:
                try:
                    await sender_ws.send_json(msg_data)
                except Exception:
                    pass


# Global instances
location_manager = LocationManager()
chat_manager = ChatManager()
