"""Persistent, user-scoped operational history. Never stores credentials or images."""
from datetime import datetime, timezone
from fastapi import APIRouter,Depends,Query
from sqlalchemy import Column,Integer,String,JSON,select,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base,get_db
from app.api.deps import get_current_user_id

class ActivityEvent(Base):
    __tablename__='hidro_activity_events'
    id=Column(Integer,primary_key=True)
    owner_id=Column(Integer,nullable=False,index=True)
    timestamp=Column(String(40),nullable=False)
    action=Column(String(50),nullable=False)
    detail=Column(JSON,nullable=False)

def record_event(db,uid,action,**detail):
    db.add(ActivityEvent(owner_id=uid,timestamp=datetime.now(timezone.utc).isoformat(),action=action,detail=detail))

router=APIRouter(prefix='/activity',tags=['Historial de operaciones'])
@router.get('')
async def history(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),db:AsyncSession=Depends(get_db),uid:int=Depends(get_current_user_id)):
    query=select(ActivityEvent).where(ActivityEvent.owner_id==uid)
    total=(await db.execute(select(func.count(ActivityEvent.id)).where(ActivityEvent.owner_id==uid))).scalar() or 0
    rows=(await db.execute(query.order_by(ActivityEvent.id.desc()).offset(offset).limit(limit))).scalars().all()
    return {'total':total,'items':[{'id':r.id,'timestamp':r.timestamp,'action':r.action,'detail':r.detail} for r in rows]}
