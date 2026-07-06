from app.db.auth_models import User
print('remark column:', 'remark' in [c.name for c in User.__table__.columns])
print('columns:', [c.name for c in User.__table__.columns])
