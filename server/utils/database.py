import mysql.connector
import redis
from typing import Optional, Dict, List, Any
import json

from server.config import DB_CONFIG, REDIS_CONFIG

class DatabaseManager:
    def __init__(self, db_config: Dict[str, Any], redis_config: Dict[str, Any] = None):
        self.db_config = db_config
        
        # 如果传入了 Redis 配置，则初始化 Redis 连接
        if redis_config:
            self.redis_config = redis_config
        self._setup_connections()

    def _setup_connections(self):
        """初始化数据库连接池和Redis连接"""
        try:
            self.cnx_pool = mysql.connector.pooling.MySQLConnectionPool(**self.db_config)
        except mysql.connector.Error as e:
            print(f"MySQL连接错误: {e}, 配置: {self.db_config}")
            raise

        try:
            self.redis = redis.Redis(**self.redis_config)
            # 测试Redis连接
            self.redis.ping()
        except redis.ConnectionError as e:
            print(f"Redis连接错误: {e}, 配置: {self.redis_config}")
            raise

    def get_connection(self):
        """获取数据库连接"""
        return self.cnx_pool.get_connection()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询并返回结果"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作并返回影响的行数"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def cache_set(self, key: str, value: Any, expire: int = None):
        """设置缓存"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis.set(key, value, ex=expire)

    def cache_get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        value = self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode()
        return None

    def cache_delete(self, key: str):
        """删除缓存"""
        self.redis.delete(key)

    def close(self):
        """关闭所有连接"""
        self.redis.close()