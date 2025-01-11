from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from ..utils.security import SecurityManager

@dataclass
class Message:
    id: Optional[int]
    channel_id: int
    sender_id: int
    content: str
    created_at: datetime
    is_private: bool = False
    recipient_id: Optional[int] = None

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "sender_id": self.sender_id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "is_private": self.is_private,
            "recipient_id": self.recipient_id
        }

class MessageManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_message(self, message: Message) -> Optional[Message]:
        """创建新消息"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 清理消息内容
                cleaned_content = SecurityManager.sanitize_input(message.content)
                
                # 插入消息
                query = """
                    INSERT INTO messages 
                    (channel_id, sender_id, content, is_private, recipient_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(query, (
                    message.channel_id,
                    message.sender_id,
                    cleaned_content,
                    message.is_private,
                    message.recipient_id,
                    message.created_at
                ))
                
                # 获取插入的消息ID
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                result = cursor.fetchone()
                
                # 提交事务
                conn.commit()
                
                if result and result['id']:
                    message.id = result['id']
                    return message
                        
                return None
                
        except Exception as e:
            print(f"创建消息错误: {str(e)}")
            # 记录更详细的错误信息
            import traceback
            traceback.print_exc()
            return None
        
    def get_channel_messages(self, channel_id: int, limit: int = 50) -> List[Message]:
        """获取频道消息"""
        try:
            query = """
                SELECT m.*, u.username as sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.channel_id = %s AND m.is_private = FALSE
                ORDER BY m.created_at DESC
                LIMIT %s
            """
            results = self.db.execute_query(query, (channel_id, limit))
            
            return [Message(
                id=row["id"],
                channel_id=row["channel_id"],
                sender_id=row["sender_id"],
                content=row["content"],
                created_at=row["created_at"],
                is_private=row["is_private"],
                recipient_id=row["recipient_id"]
            ) for row in results]
        except Exception as e:
            print(f"获取频道消息错误: {str(e)}")
            return []

    def get_private_messages(self, user1_id: int, user2_id: int, limit: int = 50) -> List[Message]:
        """获取私聊消息"""
        try:
            # 确保使用事务保持一致性
            with self.db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                query = """
                    SELECT m.*, u.username as sender_name
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.is_private = TRUE
                    AND (
                        (m.sender_id = %s AND m.recipient_id = %s)
                        OR (m.sender_id = %s AND m.recipient_id = %s)
                    )
                    ORDER BY m.created_at DESC
                    LIMIT %s
                """
                
                cursor.execute(query, (user1_id, user2_id, user2_id, user1_id, limit))
                results = cursor.fetchall()
                
                return [Message(
                    id=row["id"],
                    channel_id=row["channel_id"],
                    sender_id=row["sender_id"],
                    content=row["content"],
                    created_at=row["created_at"],
                    is_private=True,
                    recipient_id=row["recipient_id"]
                ) for row in results]
                
        except Exception as e:
            print(f"获取私聊消息错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def delete_message(self, message_id: int, user_id: int) -> bool:
        """删除消息（仅消息发送者可以删除）"""
        try:
            query = """
                DELETE FROM messages
                WHERE id = %s AND sender_id = %s
            """
            result = self.db.execute_update(query, (message_id, user_id))
            return result > 0
        except Exception as e:
            print(f"删除消息错误: {str(e)}")
            return False