import hashlib
import secrets
import re
from typing import Tuple, Optional

class SecurityManager:
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        对密码进行加盐哈希
        返回: (哈希后的密码, 盐值)
        """
        if not salt:
            salt = secrets.token_hex(16)
        
        salted = password + salt
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        return hashed, salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """验证密码是否正确"""
        new_hash, _ = SecurityManager.hash_password(password, salt)
        return new_hash == hashed

    @staticmethod
    def validate_username(username: str) -> bool:
        """
        验证用户名是否合法
        规则：
        - 长度在3-20之间
        - 只允许字母、数字、下划线
        - 不能以数字开头
        """
        if not (3 <= len(username) <= 20):
            return False
        
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        验证密码强度
        规则：
        - 长度至少8位
        - 必须包含数字和字母
        - 不能包含特殊字符
        """
        if len(password) < 8:
            return False
        
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        is_alnum = password.isalnum()
        
        return has_letter and has_digit and is_alnum

    @staticmethod
    def sanitize_input(text: str) -> str:
        """清理用户输入，防止XSS"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 转义特殊字符
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

    @staticmethod
    def generate_token() -> str:
        """生成安全的随机令牌"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def rate_limit_key(username: str, action: str) -> str:
        """生成速率限制的键名"""
        return f"rate_limit:{action}:{username}"