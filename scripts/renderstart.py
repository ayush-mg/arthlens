import os
import sys
import subprocess
import sqlalchemy as sa
import uvicorn
os.environ["PYTHONPATH"]="/app:/app/backend"
sys.path.insert(0,"/app")
sys.path.insert(0,"/app/backend")
dburl=os.environ["DATABASE_URL"]
engine=sa.create_engine(dburl)
with engine.begin() as conn:
conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
engine.dispose()
subprocess.run([sys.executable,"-B","-m","alembic","-c","backend/alembic.ini","upgrade","head"],check=True)
subprocess.run([sys.executable,"-B","scripts/bootstrap_admin.py"],check=True)
subprocess.run([sys.executable,"-B","scripts/seed_demo_accounts.py"],check=True)
portval=int(os.environ.get("PORT","10000"))
uvicorn.run("backend.arthlens.api.app:create_app",factory=True,host="0.0.0.0",port=portval)
