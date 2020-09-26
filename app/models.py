from sqlalchemy import Column, Integer, String
from app import engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class File(Base):
    __tablename__ = 'File'
    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    file_id = Column(String)
    file_key = Column(String)
    
    def __repr__(self):
        return f"<File {self.file_id}:{self.file_name}>"
