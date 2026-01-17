# SQL tool - generates queries, validates them, executes safely
import sqlite3
import re
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class SQLTool:
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.schema = self._introspect_schema()
    
    def _introspect_schema(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                schema[table] = columns
            
            conn.close()
            logger.info(f"Schema introspected: {schema}")
            return schema
        except Exception as e:
            logger.error(f"Schema introspection failed: {e}")
            return {"stock_prices": ["symbol", "date", "open", "close", "volume"]}
    
    def get_schema_string(self) -> str:
        lines = []
        for table, columns in self.schema.items():
            lines.append(f"Table: {table}")
            lines.append(f"  Columns: {', '.join(columns)}")
        return "\n".join(lines)
    
    def validate_sql(self, query: str) -> Tuple[bool, Optional[str]]:
        query = query.strip()
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
            "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"
        ]
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False, f"Blocked dangerous keyword: {keyword}"
        
        if not query_upper.strip().startswith("SELECT"):
            return False, "Only SELECT queries are allowed"
        
        allowed_tables = set(self.schema.keys())
        for table in allowed_tables:
            if table.lower() in query.lower():
                break
        else:
            if any(t.lower() in query.lower() for t in ["FROM", "JOIN"]):
                return False, f"Table not in whitelist. Allowed: {list(allowed_tables)}"
        
        injection_patterns = [
            r";\s*--",  # Comment injection
            r"UNION.*SELECT",  # Union injection
            r"OR\s+1\s*=\s*1",  # Always true
        ]
        for pattern in injection_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Potential SQL injection detected"
        
        return True, None
    
    def execute_query(self, query: str, max_rows: int = 100) -> Dict:
        query = self._extract_sql_from_text(query)
        is_valid, error = self.validate_sql(query)
        if not is_valid:
            logger.warning(f"SQL validation failed: {error}")
            return {
                "success": False,
                "error": error,
                "rows": [],
                "summary": f"Query rejected: {error}"
            }
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return dict-like rows
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if len(rows) > max_rows:
                rows = rows[:max_rows]
                logger.warning(f"Query returned {len(rows)} rows, truncated to {max_rows}")
            
            result_rows = [dict(row) for row in rows]
            summary = self._generate_summary(result_rows, query)
            
            conn.close()
            
            logger.info(f"SQL query executed successfully: {len(result_rows)} rows")
            return {
                "success": True,
                "rows": result_rows,
                "row_count": len(result_rows),
                "summary": summary,
                "query": query
            }
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "summary": f"SQL error: {str(e)}"
            }
    
    def _extract_sql_from_text(self, text: str) -> str:
        text = re.sub(r"```sql\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()
        match = re.search(r"SELECT.*", text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()
        
        return text.strip()
    
    def _generate_summary(self, rows: List[Dict], query: str) -> str:
        if not rows:
            return "Query returned no results."
        
        if len(rows) == 1:
            return f"Found 1 result: {json.dumps(rows[0], default=str)}"
        
        preview = rows[:3]
        preview_str = ", ".join([json.dumps(r, default=str) for r in preview])
        if len(rows) > 3:
            return f"Found {len(rows)} results. Sample: {preview_str}..."
        return f"Found {len(rows)} results: {preview_str}"
