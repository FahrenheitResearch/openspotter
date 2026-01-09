"""Seed script to populate the database with demo data."""
import asyncio
import uuid
from datetime import datetime, timedelta
import random

from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.report import Report, ReportType
from app.models.message import Channel, Message
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo users
DEMO_USERS = [
    {"email": "demo@openspotter.org", "callsign": "DEMO1", "password": "demo123", "role": UserRole.VERIFIED_SPOTTER, "city": "Oklahoma City", "state": "OK"},
    {"email": "storm@openspotter.org", "callsign": "STORM01", "password": "demo123", "role": UserRole.VERIFIED_SPOTTER, "city": "Norman", "state": "OK"},
    {"email": "chase@openspotter.org", "callsign": "CHASE99", "password": "demo123", "role": UserRole.SPOTTER, "city": "Tulsa", "state": "OK"},
    {"email": "coord@openspotter.org", "callsign": "COORD1", "password": "demo123", "role": UserRole.COORDINATOR, "city": "Dallas", "state": "TX"},
    {"email": "wx@openspotter.org", "callsign": "WX-HUNTER", "password": "demo123", "role": UserRole.VERIFIED_SPOTTER, "city": "Wichita", "state": "KS"},
    {"email": "tornado@openspotter.org", "callsign": "TWISTER", "password": "demo123", "role": UserRole.SPOTTER, "city": "Amarillo", "state": "TX"},
    {"email": "hail@openspotter.org", "callsign": "HAILSTONE", "password": "demo123", "role": UserRole.VERIFIED_SPOTTER, "city": "Lubbock", "state": "TX"},
    {"email": "rain@openspotter.org", "callsign": "RAINMAN", "password": "demo123", "role": UserRole.SPOTTER, "city": "Kansas City", "state": "MO"},
    {"email": "admin@openspotter.org", "callsign": "ADMIN", "password": "admin123", "role": UserRole.ADMIN, "city": "Denver", "state": "CO"},
]

# Spotter locations (lat, lng) - spread across Tornado Alley
SPOTTER_LOCATIONS = [
    (35.4676, -97.5164),   # Oklahoma City
    (35.2226, -97.4395),   # Norman
    (36.1540, -95.9928),   # Tulsa
    (32.7767, -96.7970),   # Dallas
    (37.6872, -97.3301),   # Wichita
    (35.2220, -101.8313),  # Amarillo
    (33.5779, -101.8552),  # Lubbock
    (39.0997, -94.5786),   # Kansas City
    (39.7392, -104.9903),  # Denver
    (35.0844, -106.6504),  # Albuquerque
    (36.7280, -98.2890),   # Enid
    (34.7465, -96.0174),   # McAlester
]

# Demo weather reports
DEMO_REPORTS = [
    {"type": ReportType.TORNADO, "lat": 35.35, "lng": -97.60, "title": "Tornado on the ground", "desc": "Large wedge tornado moving NE. Debris cloud visible.", "severity": 5, "verified": True},
    {"type": ReportType.TORNADO, "lat": 35.52, "lng": -97.45, "title": "Brief tornado", "desc": "Rope tornado touched down briefly near highway.", "severity": 3, "verified": True},
    {"type": ReportType.FUNNEL_CLOUD, "lat": 36.10, "lng": -96.05, "title": "Funnel cloud observed", "desc": "Rotating funnel extending from storm base, not touching ground.", "severity": 2, "verified": False},
    {"type": ReportType.WALL_CLOUD, "lat": 35.80, "lng": -97.20, "title": "Rotating wall cloud", "desc": "Persistent lowering with strong rotation. Tornado possible.", "severity": 3, "verified": True},
    {"type": ReportType.HAIL, "lat": 32.85, "lng": -96.70, "title": "Golf ball hail", "desc": "1.75 inch hail falling. Significant damage to vehicles.", "severity": 4, "hail_size": 1.75, "verified": True},
    {"type": ReportType.HAIL, "lat": 33.50, "lng": -101.80, "title": "Quarter size hail", "desc": "Quarter to half dollar size hail for 10 minutes.", "severity": 2, "hail_size": 1.0, "verified": False},
    {"type": ReportType.HAIL, "lat": 37.70, "lng": -97.40, "title": "Ping pong ball hail", "desc": "1.5 inch hail with strong winds.", "severity": 3, "hail_size": 1.5, "verified": True},
    {"type": ReportType.WIND_DAMAGE, "lat": 36.20, "lng": -95.90, "title": "Trees down", "desc": "Multiple trees snapped, power lines down on Main St.", "severity": 3, "wind_speed": 70, "verified": True},
    {"type": ReportType.WIND_DAMAGE, "lat": 35.30, "lng": -97.55, "title": "Roof damage", "desc": "Strong winds removed shingles from several homes.", "severity": 2, "wind_speed": 60, "verified": False},
    {"type": ReportType.FLOODING, "lat": 39.10, "lng": -94.60, "title": "Street flooding", "desc": "Water over roadway at intersection. Several cars stranded.", "severity": 3, "verified": True},
    {"type": ReportType.FLASH_FLOOD, "lat": 35.45, "lng": -97.50, "title": "Flash flood warning area", "desc": "Rapid rise in creek levels. Water entering homes.", "severity": 4, "verified": True},
    {"type": ReportType.HEAVY_RAIN, "lat": 36.75, "lng": -98.30, "title": "Heavy rainfall", "desc": "2+ inches in past hour. Visibility near zero.", "severity": 2, "verified": False},
    {"type": ReportType.ROTATION, "lat": 35.60, "lng": -97.35, "title": "Strong rotation", "desc": "Radar confirmed rotation. Storm producing large hail.", "severity": 3, "verified": True},
    {"type": ReportType.DUST_STORM, "lat": 35.20, "lng": -101.85, "title": "Haboob approaching", "desc": "Large dust wall reducing visibility to zero.", "severity": 3, "verified": True},
    {"type": ReportType.LIGHTNING, "lat": 39.75, "lng": -105.00, "title": "Frequent lightning", "desc": "Cloud to ground lightning every few seconds.", "severity": 2, "verified": False},
]


async def seed_database():
    """Seed the database with demo data."""
    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.execute(
            User.__table__.select().where(User.email == "demo@openspotter.org")
        )
        if existing.first():
            print("Database already seeded. Skipping...")
            return

        print("Creating demo users...")
        users = []
        for u in DEMO_USERS:
            user = User(
                id=uuid.uuid4(),
                email=u["email"],
                password_hash=pwd_context.hash(u["password"]),
                callsign=u["callsign"],
                display_name=u["callsign"],
                role=u["role"],
                is_active=True,
                is_email_verified=True,
                location_city=u["city"],
                location_state=u["state"],
                share_location_with="public",
            )
            session.add(user)
            users.append(user)

        await session.flush()
        print(f"  Created {len(users)} users")

        # Create locations for spotters (simulate active spotters)
        print("Creating spotter locations...")
        locations_created = 0
        for i, (lat, lng) in enumerate(SPOTTER_LOCATIONS):
            if i >= len(users):
                break

            # Add some randomness to positions
            lat_offset = random.uniform(-0.05, 0.05)
            lng_offset = random.uniform(-0.05, 0.05)

            # Create a few location history points
            for minutes_ago in [0, 5, 10, 15]:
                loc = Location(
                    id=uuid.uuid4(),
                    user_id=users[i].id,
                    latitude=lat + lat_offset + random.uniform(-0.01, 0.01),
                    longitude=lng + lng_offset + random.uniform(-0.01, 0.01),
                    altitude=random.uniform(300, 500),
                    accuracy=random.uniform(5, 20),
                    heading=random.uniform(0, 360),
                    speed=random.uniform(0, 30) if minutes_ago == 0 else random.uniform(10, 40),
                    visibility="public",
                    timestamp=datetime.utcnow() - timedelta(minutes=minutes_ago),
                )
                session.add(loc)
                locations_created += 1

        await session.flush()
        print(f"  Created {locations_created} location records")

        # Create weather reports
        print("Creating weather reports...")
        reports_created = 0
        for i, r in enumerate(DEMO_REPORTS):
            # Assign to random verified spotter or coordinator
            reporter = random.choice([u for u in users if u.role in [UserRole.VERIFIED_SPOTTER, UserRole.COORDINATOR]])
            verifier = random.choice([u for u in users if u.role in [UserRole.COORDINATOR, UserRole.ADMIN]]) if r.get("verified") else None

            # Random time in last 6 hours
            hours_ago = random.uniform(0.5, 6)

            report = Report(
                id=uuid.uuid4(),
                user_id=reporter.id,
                type=r["type"],
                title=r["title"],
                description=r["desc"],
                latitude=r["lat"] + random.uniform(-0.02, 0.02),
                longitude=r["lng"] + random.uniform(-0.02, 0.02),
                severity=r.get("severity"),
                hail_size=r.get("hail_size"),
                wind_speed=r.get("wind_speed"),
                is_verified=r.get("verified", False),
                verified_by_id=verifier.id if verifier and r.get("verified") else None,
                verified_at=datetime.utcnow() - timedelta(hours=hours_ago - 0.5) if r.get("verified") else None,
                event_time=datetime.utcnow() - timedelta(hours=hours_ago + 0.25),
                created_at=datetime.utcnow() - timedelta(hours=hours_ago),
                media_urls=[],
            )
            session.add(report)
            reports_created += 1

        await session.flush()
        print(f"  Created {reports_created} weather reports")

        # Create chat channels
        print("Creating chat channels...")
        channels = [
            Channel(id=uuid.uuid4(), name="General", description="General discussion for all spotters", channel_type="regional", is_public=True),
            Channel(id=uuid.uuid4(), name="Oklahoma", description="Oklahoma spotters coordination", channel_type="regional", is_public=True),
            Channel(id=uuid.uuid4(), name="Texas", description="Texas spotters coordination", channel_type="regional", is_public=True),
            Channel(id=uuid.uuid4(), name="Kansas", description="Kansas spotters coordination", channel_type="regional", is_public=True),
            Channel(id=uuid.uuid4(), name="Coordinators", description="Coordinator-only channel", channel_type="regional", is_public=False, min_role="coordinator"),
        ]
        for ch in channels:
            session.add(ch)

        await session.flush()
        print(f"  Created {len(channels)} chat channels")

        # Create some chat messages
        print("Creating chat messages...")
        messages = [
            "Storm looking intense to the southwest!",
            "Confirmed rotation on this cell",
            "Heading north to intercept",
            "Large hail reported near my position",
            "Be careful out there everyone",
            "This storm is cycling again",
            "Wall cloud developing",
            "Great structure on this supercell",
            "Moving to better position",
            "Tornado warning just issued",
        ]

        messages_created = 0
        general_channel = channels[0]
        for i, msg_content in enumerate(messages):
            sender = random.choice(users[:8])  # Don't use admin for chat
            msg = Message(
                id=uuid.uuid4(),
                sender_id=sender.id,
                channel_id=general_channel.id,
                content=msg_content,
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
            )
            session.add(msg)
            messages_created += 1

        await session.flush()
        print(f"  Created {messages_created} chat messages")

        await session.commit()
        print("\nDemo data seeded successfully!")
        print("\nDemo accounts:")
        print("  Email: demo@openspotter.org  Password: demo123")
        print("  Email: admin@openspotter.org Password: admin123")


if __name__ == "__main__":
    asyncio.run(seed_database())
