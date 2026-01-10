"""Twitter/X API integration for posting weather reports."""
import os
import base64
import httpx
from typing import Optional

from app.config import get_settings
from app.services.wfo_twitter import format_report_tweet, get_wfo_mention

settings = get_settings()


class TwitterService:
    """Service for posting to Twitter/X."""

    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

        self.base_url = "https://api.twitter.com/2"
        self.upload_url = "https://upload.twitter.com/1.1"

    @property
    def is_configured(self) -> bool:
        """Check if Twitter credentials are configured."""
        return bool(self.bearer_token or (self.api_key and self.access_token))

    async def upload_media(self, media_data: bytes, media_type: str) -> Optional[str]:
        """Upload media to Twitter and return media_id."""
        if not self.is_configured:
            return None

        try:
            # Twitter media upload requires OAuth 1.0a
            # For simplicity, we'll use the v1.1 chunked upload
            async with httpx.AsyncClient() as client:
                # INIT
                init_response = await client.post(
                    f"{self.upload_url}/media/upload.json",
                    headers=self._get_oauth_headers(),
                    data={
                        "command": "INIT",
                        "total_bytes": len(media_data),
                        "media_type": media_type,
                    }
                )
                if init_response.status_code != 200:
                    print(f"Twitter media init failed: {init_response.text}")
                    return None

                media_id = init_response.json()["media_id_string"]

                # APPEND (chunked)
                chunk_size = 5 * 1024 * 1024  # 5MB chunks
                for i, chunk_start in enumerate(range(0, len(media_data), chunk_size)):
                    chunk = media_data[chunk_start:chunk_start + chunk_size]
                    append_response = await client.post(
                        f"{self.upload_url}/media/upload.json",
                        headers=self._get_oauth_headers(),
                        data={
                            "command": "APPEND",
                            "media_id": media_id,
                            "segment_index": i,
                        },
                        files={"media": chunk}
                    )
                    if append_response.status_code not in [200, 204]:
                        print(f"Twitter media append failed: {append_response.text}")
                        return None

                # FINALIZE
                finalize_response = await client.post(
                    f"{self.upload_url}/media/upload.json",
                    headers=self._get_oauth_headers(),
                    data={
                        "command": "FINALIZE",
                        "media_id": media_id,
                    }
                )
                if finalize_response.status_code != 200:
                    print(f"Twitter media finalize failed: {finalize_response.text}")
                    return None

                return media_id

        except Exception as e:
            print(f"Twitter media upload error: {e}")
            return None

    async def post_tweet(
        self,
        text: str,
        media_ids: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Post a tweet with optional media."""
        if not self.is_configured:
            print("Twitter not configured - skipping post")
            return None

        try:
            async with httpx.AsyncClient() as client:
                payload = {"text": text}

                if media_ids:
                    payload["media"] = {"media_ids": media_ids}

                response = await client.post(
                    f"{self.base_url}/tweets",
                    headers={
                        "Authorization": f"Bearer {self.bearer_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload
                )

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    print(f"Twitter post failed: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Twitter post error: {e}")
            return None

    async def post_weather_report(
        self,
        report_type: str,
        description: str,
        latitude: float,
        longitude: float,
        wfo_code: Optional[str] = None,
        severity: Optional[int] = None,
        hail_size: Optional[float] = None,
        wind_speed: Optional[int] = None,
        media_data: Optional[bytes] = None,
        media_type: Optional[str] = None,
    ) -> Optional[dict]:
        """Post a weather report to Twitter."""

        # Format the tweet
        tweet_text = format_report_tweet(
            report_type=report_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            wfo_code=wfo_code,
            severity=severity,
            hail_size=hail_size,
            wind_speed=wind_speed,
        )

        # Upload media if provided
        media_ids = None
        if media_data and media_type:
            media_id = await self.upload_media(media_data, media_type)
            if media_id:
                media_ids = [media_id]

        # Post the tweet
        return await self.post_tweet(tweet_text, media_ids)

    def _get_oauth_headers(self) -> dict:
        """Get OAuth 1.0a headers for media upload."""
        # Simplified - in production use proper OAuth signing
        return {
            "Authorization": f"Bearer {self.bearer_token}",
        }


# Singleton instance
twitter_service = TwitterService()
