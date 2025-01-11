from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..utils.security import SecurityManager

@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str
    salt: str
    created_at: datetime
    last_login: Optional[datetime] = None
    current_channel: str = "general"
    is_online: bool = False

    @classmethod
    def create(cls, username: str, password: str):
        """创建新用户"""
        password_hash, salt = SecurityManager.hash_password(password)
        return cls(
            id=None,
            username=username,
            password_hash=password_hash,
            salt=salt,
            created_at=datetime.now()
        )

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return SecurityManager.verify_password(password, self.password_hash, self.salt)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "current_channel": self.current_channel,
            "is_online": self.is_online
        }

class UserManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_user(self, username: str, password: str) -> Optional[User]:
        """创建用户"""
        try:
            user = User.create(username, password)
            
            # 先插入用户
            query = """
                INSERT INTO users (username, password_hash, salt, created_at)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_update(query, (
                user.username,
                user.password_hash,
                user.salt,
                user.created_at
            ))
            
            # 然后获取插入的ID
            query = "SELECT id FROM users WHERE username = %s"
            result = self.db.execute_query(query, (username,))
            
            if result:
                user.id = result[0]["id"]
                return user
            return None
            
        except Exception as e:
            print(f"创建用户错误: {str(e)}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        try:
            query = """
                SELECT id, username, password_hash, salt, created_at, last_login
                FROM users
                WHERE username = %s
            """
            result = self.db.execute_query(query, (username,))
            
            if result:
                user_data = result[0]
                return User(
                    id=user_data["id"],
                    username=user_data["username"],
                    password_hash=user_data["password_hash"],
                    salt=user_data["salt"],
                    created_at=user_data["created_at"],
                    last_login=user_data["last_login"]
                )
            return None
            
        except Exception as e:
            print(f"获取用户错误: {str(e)}")
            return None

    def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        try:
            query = """
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.db.execute_update(query, (user_id,))
        except Exception as e:
            print(f"更新登录时间错误: {str(e)}")

    def update_user_channel(self, user_id: int, channel: str):
        """更新用户当前频道"""
        try:
            query = """
                UPDATE users
                SET current_channel = %s
                WHERE id = %s
            """
            self.db.execute_update(query, (channel, user_id))
        except Exception as e:
            print(f"更新用户频道错误: {str(e)}")