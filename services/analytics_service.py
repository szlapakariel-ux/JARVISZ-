from sqlalchemy import select, func, desc
from database.db import async_session
from database.models import CheckIn, KPIEvent
from datetime import datetime, timedelta

class AnalyticsService:
    @staticmethod
    async def get_kpis(user_id: int):
        async with async_session() as session:
            # 1. ADHERENCE (Last 30 days)
            # Count distinct days with checkins / 30
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            result = await session.execute(
                select(func.count(func.distinct(func.date(CheckIn.timestamp))))
                .where(CheckIn.user_id == user_id)
                .where(CheckIn.timestamp >= thirty_days_ago)
            )
            days_with_checkin = result.scalar() or 0
            adherence_pct = int((days_with_checkin / 30) * 100)
            
            # 2. STREAK
            # Harder in SQL, let's do python logic on last 30 checkins dates
            result = await session.execute(
                select(func.date(CheckIn.timestamp))
                .where(CheckIn.user_id == user_id)
                .order_by(desc(CheckIn.timestamp))
                .limit(60) # Fetch enough history
            )
            dates = sorted(list(set([r[0] for r in result.all()])), reverse=True)
            
            streak = 0
            if dates:
                # Check if today or yesterday is present
                today_str = datetime.utcnow().strftime("%Y-%m-%d")
                yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Start counting from today or yesterday
                latest = str(dates[0])
                if latest == today_str or latest == yesterday_str:
                    streak = 1
                    current = datetime.strptime(latest, "%Y-%m-%d")
                    for i in range(1, len(dates)):
                        prev = datetime.strptime(str(dates[i]), "%Y-%m-%d")
                        if (current - prev).days == 1:
                            streak += 1
                            current = prev
                        else:
                            break
            
            # 3. BLOCK RATE
            # Count 'frustration' events vs total interactions (approx by checkins + events?)
            # Or simplified: Total Frustration Events in last 30 days.
            result = await session.execute(
                select(func.count(KPIEvent.id))
                .where(KPIEvent.user_id == user_id)
                .where(KPIEvent.event_type == 'frustration')
                .where(KPIEvent.timestamp >= thirty_days_ago)
            )
            blocking_events = result.scalar() or 0
            
            return {
                "adherence": adherence_pct,
                "streak": streak,
                "blocks": blocking_events
            }
