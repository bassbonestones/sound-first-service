from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
target_metadata = Base.metadata

from .core import *
