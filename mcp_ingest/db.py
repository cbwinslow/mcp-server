#!/usr/bin/env python3
"""
MCP Database Layer
Provides database operations for MCP server components
"""

import os
import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPDatabase:
    """Database layer for MCP server operations"""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent
            db_path = project_root / "mcp_database.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Repositories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    description TEXT,
                    language TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    crawled_at TEXT,
                    extracted_at TEXT,
                    embedded_at TEXT,
                    metadata TEXT  -- JSON field for additional data
                )
            ''')

            # Crawler jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawler_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'pending',
                    target TEXT,
                    config TEXT,  -- JSON config
                    started_at TEXT,
                    completed_at TEXT,
                    repositories_found INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')

            # Embeddings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER,
                    content_type TEXT,
                    content_path TEXT,
                    embedding_vector TEXT,  -- JSON array of floats
                    model_name TEXT,
                    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories (id)
                )
            ''')

            # System status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_status (
                    component TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'unknown',
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    details TEXT  -- JSON details
                )
            ''')

            # Insert default status records
            components = ['crawler', 'extractor', 'embeddings', 'database']
            for component in components:
                cursor.execute('''
                    INSERT OR IGNORE INTO system_status (component, status, details)
                    VALUES (?, 'idle', '{}')
                ''', (component,))

            conn.commit()
            logger.info("Database initialized successfully")

    def add_repository(self, repo_data: Dict[str, Any]) -> int:
        """
        Add a repository to the database

        Args:
            repo_data: Repository information

        Returns:
            Repository ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Prepare data
            metadata = repo_data.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)

            cursor.execute('''
                INSERT INTO repositories
                (name, owner, url, description, language, stars, forks,
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                repo_data.get('name'),
                repo_data.get('owner'),
                repo_data.get('url'),
                repo_data.get('description'),
                repo_data.get('language'),
                repo_data.get('stars', 0),
                repo_data.get('forks', 0),
                repo_data.get('created_at'),
                repo_data.get('updated_at'),
                metadata
            ))

            repo_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added repository: {repo_data.get('name')} (ID: {repo_id})")
            return repo_id

    def get_repositories(self, filters: Dict[str, Any] = None,
                        limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get repositories from database

        Args:
            filters: Query filters
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            List of repositories
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM repositories WHERE 1=1"
            params = []

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if key in ['name', 'owner', 'language', 'processed']:
                        query += f" AND {key} = ?"
                        params.append(value)
                    elif key == 'min_stars':
                        query += " AND stars >= ?"
                        params.append(value)
                    elif key == 'max_stars':
                        query += " AND stars <= ?"
                        params.append(value)

            query += " ORDER BY added_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                repo = dict(row)
                # Parse metadata JSON
                if repo.get('metadata'):
                    try:
                        repo['metadata'] = json.loads(repo['metadata'])
                    except:
                        repo['metadata'] = {}
                results.append(repo)

            return results

    def update_repository_status(self, repo_id: int, status_field: str,
                               status_value: Any) -> bool:
        """
        Update repository processing status

        Args:
            repo_id: Repository ID
            status_field: Status field to update (processed, crawled_at, etc.)
            status_value: New value

        Returns:
            Success status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Convert datetime objects to ISO strings
            if isinstance(status_value, datetime):
                status_value = status_value.isoformat()

            cursor.execute(f'''
                UPDATE repositories
                SET {status_field} = ?
                WHERE id = ?
            ''', (status_value, repo_id))

            success = cursor.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"Updated repository {repo_id} {status_field}: {status_value}")

            return success

    def add_crawler_job(self, job_id: str, target: str,
                       config: Dict[str, Any]) -> int:
        """
        Add a crawler job to the database

        Args:
            job_id: Unique job identifier
            target: Crawl target
            config: Job configuration

        Returns:
            Job ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO crawler_jobs
                (job_id, target, config, started_at)
                VALUES (?, ?, ?, ?)
            ''', (
                job_id,
                target,
                json.dumps(config),
                datetime.now().isoformat()
            ))

            job_db_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added crawler job: {job_id}")
            return job_db_id

    def update_crawler_job(self, job_id: str, status: str,
                          repositories_found: int = None,
                          error_message: str = None) -> bool:
        """
        Update crawler job status

        Args:
            job_id: Job identifier
            status: New status
            repositories_found: Number of repositories found
            error_message: Error message if failed

        Returns:
            Success status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            update_fields = ["status = ?"]
            params = [status]

            if repositories_found is not None:
                update_fields.append("repositories_found = ?")
                params.append(repositories_found)

            if error_message:
                update_fields.append("error_message = ?")
                params.append(error_message)

            if status in ['completed', 'failed']:
                update_fields.append("completed_at = ?")
                params.append(datetime.now().isoformat())

            query = f'''
                UPDATE crawler_jobs
                SET {', '.join(update_fields)}
                WHERE job_id = ?
            '''
            params.append(job_id)

            cursor.execute(query, params)
            success = cursor.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"Updated crawler job {job_id}: {status}")

            return success

    def add_embedding(self, repository_id: int, content_type: str,
                     content_path: str, embedding_vector: List[float],
                     model_name: str) -> int:
        """
        Add an embedding to the database

        Args:
            repository_id: Repository ID
            content_type: Type of content
            content_path: Path to content
            embedding_vector: Embedding vector
            model_name: Model used for generation

        Returns:
            Embedding ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO embeddings
                (repository_id, content_type, content_path, embedding_vector, model_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                repository_id,
                content_type,
                content_path,
                json.dumps(embedding_vector),
                model_name
            ))

            embedding_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added embedding for repo {repository_id}: {content_path}")
            return embedding_id

    def update_system_status(self, component: str, status: str,
                           details: Dict[str, Any] = None) -> bool:
        """
        Update system component status

        Args:
            component: Component name
            status: Status value
            details: Additional details

        Returns:
            Success status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            details_json = json.dumps(details) if details else '{}'

            cursor.execute('''
                UPDATE system_status
                SET status = ?, last_updated = ?, details = ?
                WHERE component = ?
            ''', (status, datetime.now().isoformat(), details_json, component))

            success = cursor.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"Updated {component} status: {status}")

            return success

    def get_system_status(self, component: str = None) -> Dict[str, Any]:
        """
        Get system component status

        Args:
            component: Specific component or None for all

        Returns:
            Status information
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if component:
                cursor.execute('SELECT * FROM system_status WHERE component = ?', (component,))
                row = cursor.fetchone()
                if row:
                    status = dict(row)
                    status['details'] = json.loads(status.get('details', '{}'))
                    return status
                return {}
            else:
                cursor.execute('SELECT * FROM system_status')
                rows = cursor.fetchall()
                status_dict = {}
                for row in rows:
                    status = dict(row)
                    status['details'] = json.loads(status.get('details', '{}'))
                    status_dict[status['component']] = status
                return status_dict

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Database statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Repository stats
            cursor.execute('SELECT COUNT(*) as total_repos FROM repositories')
            total_repos = cursor.fetchone()['total_repos']

            cursor.execute('SELECT COUNT(*) as processed_repos FROM repositories WHERE processed = 1')
            processed_repos = cursor.fetchone()['processed_repos']

            # Embedding stats
            cursor.execute('SELECT COUNT(*) as total_embeddings FROM embeddings')
            total_embeddings = cursor.fetchone()['total_embeddings']

            # Crawler job stats
            cursor.execute('SELECT COUNT(*) as total_jobs FROM crawler_jobs')
            total_jobs = cursor.fetchone()['total_jobs']

            cursor.execute('SELECT COUNT(*) as completed_jobs FROM crawler_jobs WHERE status = "completed"')
            completed_jobs = cursor.fetchone()['completed_jobs']

            return {
                "repositories": {
                    "total": total_repos,
                    "processed": processed_repos,
                    "unprocessed": total_repos - processed_repos
                },
                "embeddings": {
                    "total": total_embeddings
                },
                "crawler_jobs": {
                    "total": total_jobs,
                    "completed": completed_jobs,
                    "pending": total_jobs - completed_jobs
                }
            }

# Global database instance
_db_instance = None

def get_database() -> MCPDatabase:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = MCPDatabase()
    return _db_instance

if __name__ == "__main__":
    # Test database functionality
    db = get_database()

    # Add a test repository
    test_repo = {
        "name": "test-repo",
        "owner": "testuser",
        "url": "https://github.com/testuser/test-repo",
        "description": "A test repository",
        "language": "Python",
        "stars": 42,
        "metadata": {"test": True}
    }

    repo_id = db.add_repository(test_repo)
    print(f"Added repository with ID: {repo_id}")

    # Get repositories
    repos = db.get_repositories(limit=10)
    print(f"Found {len(repos)} repositories")

    # Get stats
    stats = db.get_stats()
    print(f"Database stats: {stats}")
