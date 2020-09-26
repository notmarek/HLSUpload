from aiohttp import web
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
try:
    os.mkdir("./hls")
    
except FileExistsError:
    pass
try:
    os.mkdir("./source")
except FileExistsError:
    pass
engine = create_engine('sqlite:///HLS.db', echo=False)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

from app.models import File, Base
from app.routes import Routes
Base.metadata.create_all(engine)
routes = Routes(Session)
app = web.Application()
app.add_routes(routes.routes)

if __name__ == '__main__':
    web.run_app(app)