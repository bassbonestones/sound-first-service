from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.capability_schema import Capability, MaterialTeachesCapability, UserCapability
from app.models.core import Material

engine = create_engine('sqlite:///sound_first.db')
Session = sessionmaker(bind=engine)
db = Session()

# Find pitch_direction_awareness capability
cap = db.query(Capability).filter(Capability.name.like('%pitch_direction%')).first()
if cap:
    print(f'Capability: {cap.name} (id={cap.id})')
    
    # Check user 1's status for this cap
    uc = db.query(UserCapability).filter_by(user_id=1, capability_id=cap.id).first()
    if uc:
        print(f'User 1 has this cap: mastered_at={uc.mastered_at}, is_active={uc.is_active}')
    else:
        print('User 1 does NOT have this capability')
    
    # Find materials that teach this capability
    teaches = db.query(MaterialTeachesCapability).filter_by(capability_id=cap.id).all()
    print(f'\nMaterials teaching this capability: {len(teaches)}')
    for t in teaches[:5]:
        mat = db.query(Material).filter_by(id=t.material_id).first()
        if mat:
            print(f'  - {mat.title} (id={mat.id})')
else:
    print('Capability not found')
