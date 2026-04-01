from encore.runtime import Service
from encore.runtime.sqldb import SQLDatabase

# Declare the Encore service
service = Service("summarizer")

# Declare the PostgreSQL database.
# Encore provisions and manages it automatically.
db = SQLDatabase("summarizer", migrations="../migrations")
