from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from ..config import CHANNEL_CONFIG

@dataclass
class Channel:
    id: Optional[int]
    name: str
    description: str
    created_at: datetime
    is_private: bool = False
    owner_id: Optional[int] = None

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "is_private": self.is_private,
            "owner_id": self.owner_id
        }

class ChannelManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_channel(self, channel: Channel) -> Optional[Channel]:
        """创建新频道"""
        try:
            # 检查频道数量限制
            if channel.name not in CHANNEL_CONFIG["system_channels"]:
                count = self.get_channel_count()
                if count >= CHANNEL_CONFIG["max_channels"]:
                    raise Exception("已达到最大频道数量限制")

            # 先插入频道
            query = """
                INSERT INTO channels (name, description, is_private, owner_id, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute_update(query, (
                channel.name,
                channel.description,
                channel.is_private,
                channel.owner_id,
                channel.created_at
            ))
            
            # 然后获取插入的ID
            query = "SELECT id FROM channels WHERE name = %s"
            result = self.db.execute_query(query, (channel.name,))
            
            if result:
                channel.id = result[0]["id"]
                return channel
            return None
            
        except Exception as e:
            print(f"创建频道错误: {str(e)}")
            return None

    def get_channel_by_name(self, name: str) -> Optional[Channel]:
        """通过名称获取频道"""
        try:
            query = """
                SELECT *
                FROM channels
                WHERE name = %s
            """
            result = self.db.execute_query(query, (name,))
            
            if result:
                channel_data = result[0]
                return Channel(
                    id=channel_data["id"],
                    name=channel_data["name"],
                    description=channel_data["description"],
                    created_at=channel_data["created_at"],
                    is_private=channel_data["is_private"],
                    owner_id=channel_data["owner_id"]
                )
            return None
        except Exception as e:
            print(f"获取频道错误: {str(e)}")
            return None

    def get_public_channels(self) -> List[Channel]:
        """获取所有公开频道"""
        try:
            query = """
                SELECT *
                FROM channels
                WHERE is_private = FALSE
                ORDER BY created_at DESC
            """
            results = self.db.execute_query(query)
            
            return [Channel(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_at=row["created_at"],
                is_private=False,
                owner_id=row["owner_id"]
            ) for row in results]
        except Exception as e:
            print(f"获取公开频道错误: {str(e)}")
            return []

    def get_channel_count(self) -> int:
        """获取频道总数"""
        query = "SELECT COUNT(*) as count FROM channels"
        result = self.db.execute_query(query)
        return result[0]["count"]

    def delete_channel(self, channel_id: int, user_id: int) -> bool:
        """删除频道（仅频道所有者可以删除）"""
        try:
            # 系统频道不能删除
            channel = self.get_channel_by_id(channel_id)
            if channel and channel.name in CHANNEL_CONFIG["system_channels"]:
                return False

            query = """
                DELETE FROM channels
                WHERE id = %s AND owner_id = %s
            """
            result = self.db.execute_update(query, (channel_id, user_id))
            return result > 0
        except Exception as e:
            print(f"删除频道错误: {str(e)}")
            return False

    def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """通过ID获取频道"""
        try:
            query = """
                SELECT *
                FROM channels
                WHERE id = %s
            """
            result = self.db.execute_query(query, (channel_id,))
            
            if result:
                channel_data = result[0]
                return Channel(
                    id=channel_data["id"],
                    name=channel_data["name"],
                    description=channel_data["description"],
                    created_at=channel_data["created_at"],
                    is_private=channel_data["is_private"],
                    owner_id=channel_data["owner_id"]
                )
            return None
        except Exception as e:
            print(f"获取频道错误: {str(e)}")
            return None