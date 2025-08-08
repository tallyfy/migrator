"""
Database Migrator for Pipefy Tables
Migrates Pipefy database tables to external PostgreSQL/MySQL
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration of Pipefy tables to external database"""
    
    def __init__(self, database_url: str):
        """
        Initialize database migrator
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.metadata = MetaData()
        
        # Parse database type
        parsed = urlparse(database_url)
        self.db_type = parsed.scheme.split('+')[0]  # Handle postgresql+psycopg2
        
        logger.info(f"Database migrator initialized with {self.db_type}")
        
        # Statistics
        self.stats = {
            'tables_created': 0,
            'records_inserted': 0,
            'errors': 0
        }
    
    def create_table_from_pipefy(self, pipefy_table: Dict[str, Any]) -> str:
        """
        Create database table from Pipefy table schema
        
        Args:
            pipefy_table: Pipefy table definition
            
        Returns:
            Created table name
        """
        try:
            # Generate table name
            table_name = self._sanitize_table_name(pipefy_table.get('name', 'unnamed_table'))
            
            logger.info(f"Creating table: {table_name}")
            
            # Build columns from Pipefy fields
            columns = [
                Column('id', String(50), primary_key=True),
                Column('pipefy_id', String(50), unique=True, nullable=False),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
                Column('created_by', String(100)),
                Column('updated_by', String(100))
            ]
            
            # Add columns for each Pipefy field
            for field in pipefy_table.get('fields', []):
                column = self._create_column_from_field(field)
                if column is not None:
                    columns.append(column)
            
            # Create table
            table = Table(table_name, self.metadata, *columns)
            
            # Drop if exists and recreate
            table.drop(self.engine, checkfirst=True)
            table.create(self.engine)
            
            self.stats['tables_created'] += 1
            
            logger.info(f"Table created successfully: {table_name}")
            
            # Create indexes
            self._create_indexes(table_name, pipefy_table)
            
            # Store table metadata
            self._store_table_metadata(table_name, pipefy_table)
            
            return table_name
            
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            self.stats['errors'] += 1
            raise
    
    def _create_column_from_field(self, field: Dict[str, Any]) -> Optional[Column]:
        """
        Create SQLAlchemy column from Pipefy field
        
        Args:
            field: Pipefy field definition
            
        Returns:
            SQLAlchemy Column or None
        """
        field_id = field.get('id')
        field_label = self._sanitize_column_name(field.get('label', f'field_{field_id}'))
        field_type = field.get('type')
        required = field.get('required', False)
        
        # Map Pipefy field types to SQL types
        type_mapping = {
            'text': String(255),
            'textarea': Text,
            "text": Float,
            'currency': Float,
            'percentage': Float,
            'date': DateTime,
            'datetime': DateTime,
            'due_date': DateTime,
            "text": String(255),
            "text": String(50),
            'select': String(255),
            "radio": String(255),
            "multiselect": Boolean,
            'multiselect': Text,  # JSON array
            'attachment': Text,  # JSON array
            'assignee_select': String(255),
            'label_select': String(255),
            'connector': Text,  # JSON
            'statement': Text,
            'time': String(20),
            'cpf': String(20),
            'cnpj': String(20),
            'formula': Text,
            'dynamic_content': Text
        }
        
        sql_type = type_mapping.get(field_type, Text)
        
        # Handle array types
        if field_type in ['multiselect', 'attachment', 'connector']:
            # Store as JSON
            sql_type = Text
        
        return Column(
            field_label,
            sql_type,
            nullable=not required,
            comment=f"Pipefy field: {field.get('label')} (type: {field_type})"
        )
    
    def insert_record(self, table_name: str, record: Dict[str, Any]):
        """
        Insert Pipefy record into database table
        
        Args:
            table_name: Target table name
            record: Pipefy record data
        """
        try:
            # Transform record data
            transformed_record = self._transform_record(record)
            
            # Add metadata
            transformed_record['pipefy_id'] = record.get('id')
            transformed_record['created_at'] = record.get('created_at', datetime.utcnow())
            transformed_record['updated_at'] = record.get('updated_at', datetime.utcnow())
            transformed_record['created_by'] = record.get('created_by', {}).get("text")
            transformed_record['updated_by'] = record.get('updated_by', {}).get("text")
            
            # Insert into database
            with self.engine.connect() as conn:
                table = Table(table_name, self.metadata, autoload_with=self.engine)
                conn.execute(table.insert().values(**transformed_record))
                conn.commit()
            
            self.stats['records_inserted'] += 1
            
        except Exception as e:
            logger.error(f"Failed to insert record: {e}")
            self.stats['errors'] += 1
            raise
    
    def _transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Pipefy record for database insertion
        
        Args:
            record: Pipefy record
            
        Returns:
            Transformed record
        """
        transformed = {
            'id': record.get('id')
        }
        
        # Process field values
        for field_value in record.get('record_fields', []):
            field = field_value.get('field', {})
            field_label = self._sanitize_column_name(field.get('label', ''))
            value = field_value.get('value')
            array_value = field_value.get('array_value')
            
            if array_value:
                # Store arrays as JSON
                transformed[field_label] = json.dumps(array_value)
            elif value is not None:
                # Handle different value types
                if field.get('type') == "multiselect":
                    transformed[field_label] = value == 'true' or value is True
                elif field.get('type') in ['date', 'datetime', 'due_date']:
                    try:
                        transformed[field_label] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        transformed[field_label] = value
                else:
                    transformed[field_label] = value
        
        return transformed
    
    def create_api_wrapper(self, port: int = 8000) -> str:
        """
        Create FastAPI wrapper for database access
        
        Args:
            port: API port
            
        Returns:
            API endpoint URL
        """
        # Generate API wrapper code
        api_code = self._generate_api_wrapper_code()
        
        # Save to file_upload
        api_file = 'database_api.py'
        with open(api_file, 'w') as f:
            f.write(api_code)
        
        logger.info(f"API wrapper created: {api_file}")
        
        return f"http://localhost:{port}"
    
    def _generate_api_wrapper_code(self) -> str:
        """Generate FastAPI wrapper code for database access"""
        return '''"""
Auto-generated API wrapper for Pipefy database tables
"""

from fastapi import FastAPI, HTTPException, Query
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
import databases
import sqlalchemy
from pydantic import BaseModel

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create database connection
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Initialize FastAPI
app = FastAPI(title="Pipefy Tables API", version="1.0.0")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/")
async def root():
    return {"message": "Pipefy Tables API", "status": "running"}

@app.get("/tables")
async def list_tables():
    """List all available tables"""
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    result = await database.fetch_all(query)
    return {"tables": [row["table_name"] for row in result]}

@app.get("/tables/{table_name}")
async def get_table_schema(table_name: str):
    """Get table schema"""
    query = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = :table_name
    """
    result = await database.fetch_all(query, values={"table_name": table_name})
    return {"table": table_name, "columns": result}

@app.get("/tables/{table_name}/records")
async def get_records(
    table_name: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get records from table"""
    query = f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"
    result = await database.fetch_all(query, values={"limit": limit, "offset": offset})
    return {"table": table_name, "records": result}

@app.get("/tables/{table_name}/records/{record_id}")
async def get_record(table_name: str, record_id: str):
    """Get single record"""
    query = f"SELECT * FROM {table_name} WHERE id = :id OR pipefy_id = :id"
    result = await database.fetch_one(query, values={"id": record_id})
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"table": table_name, "record": result}

@app.post("/tables/{table_name}/records")
async def create_record(table_name: str, record: Dict[str, Any]):
    """Create new record"""
    columns = ", ".join(record.keys())
    values = ", ".join([f":{k}" for k in record.keys()])
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING *"
    result = await database.fetch_one(query, values=record)
    return {"table": table_name, "record": result}

@app.put("/tables/{table_name}/records/{record_id}")
async def update_record(table_name: str, record_id: str, record: Dict[str, Any]):
    """Update record"""
    set_clause = ", ".join([f"{k} = :{k}" for k in record.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE id = :id OR pipefy_id = :id RETURNING *"
    record["id"] = record_id
    result = await database.fetch_one(query, values=record)
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"table": table_name, "record": result}

@app.delete("/tables/{table_name}/records/{record_id}")
async def delete_record(table_name: str, record_id: str):
    """Delete record"""
    query = f"DELETE FROM {table_name} WHERE id = :id OR pipefy_id = :id RETURNING id"
    result = await database.fetch_one(query, values={"id": record_id})
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"message": "Record deleted", "id": result["id"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    def _sanitize_table_name(self, name: str) -> str:
        """Sanitize table name for database"""
        # Convert to lowercase and replace spaces/special chars
        sanitized = name.lower()
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'table_' + sanitized
        
        # Limit length
        return sanitized[:63]  # PostgreSQL limit
    
    def _sanitize_column_name(self, name: str) -> str:
        """Sanitize column name for database"""
        # Convert to lowercase and replace spaces/special chars
        sanitized = name.lower()
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'col_' + sanitized
        
        # Limit length
        return sanitized[:63]  # PostgreSQL limit
    
    def _create_indexes(self, table_name: str, pipefy_table: Dict[str, Any]):
        """Create database indexes for performance"""
        try:
            with self.engine.connect() as conn:
                # Index on pipefy_id
                conn.execute(f"CREATE INDEX idx_{table_name}_pipefy_id ON {table_name}(pipefy_id)")
                
                # Index on timestamps
                conn.execute(f"CREATE INDEX idx_{table_name}_created_at ON {table_name}(created_at)")
                conn.execute(f"CREATE INDEX idx_{table_name}_updated_at ON {table_name}(updated_at)")
                
                # Index on unique fields
                for field in pipefy_table.get('fields', []):
                    if field.get('unique'):
                        col_name = self._sanitize_column_name(field.get('label'))
                        conn.execute(f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name}({col_name})")
                
                conn.commit()
                
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    def _store_table_metadata(self, table_name: str, pipefy_table: Dict[str, Any]):
        """Store Pipefy table metadata for reference"""
        try:
            # Create metadata table if not exists
            metadata_table = Table(
                '_pipefy_metadata',
                self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('table_name', String(100), unique=True),
                Column('pipefy_id', String(50)),
                Column('pipefy_name', String(255)),
                Column('pipefy_description', Text),
                Column('field_mappings', Text),  # JSON
                Column('created_at', DateTime, default=datetime.utcnow)
            )
            
            metadata_table.create(self.engine, checkfirst=True)
            
            # Store metadata
            field_mappings = {
                field.get('id'): {
                    'label': field.get('label'),
                    'type': field.get('type'),
                    'column': self._sanitize_column_name(field.get('label'))
                }
                for field in pipefy_table.get('fields', [])
            }
            
            with self.engine.connect() as conn:
                conn.execute(
                    metadata_table.insert().values(
                        table_name=table_name,
                        pipefy_id=pipefy_table.get('id'),
                        pipefy_name=pipefy_table.get('name'),
                        pipefy_description=pipefy_table.get('description'),
                        field_mappings=json.dumps(field_mappings)
                    )
                )
                conn.commit()
                
        except Exception as e:
            logger.warning(f"Failed to store table metadata: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get migration statistics"""
        return self.stats