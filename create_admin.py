from app.utils.core import db
from app.models.model import User, Department

from app.factory import create_app, celery_app
import json
app = create_app(config_name="PRODUCTION")
permissions = json.dumps({"hello":["123","456"]})
department = Department()
department.from_dict({"name":"管理员1","describe":"管理员1","permissions":permissions})
db.session.add(department)
db.session.commit()

department_id = Department.query.filter_by(name="管理员1").first().get("id")
user = User()
user.from_dict({"username":"admin1", "email":"admin@admin.com", "name":"admin1","password":"admin","department_id":department_id}, new_user=True)
db.session.add(user)
db.session.commit()
