"""
服务器配置
"""

# 服务器配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 12345,
    "buffer_size": 8192
}

# MySQL数据库配置
DB_CONFIG = {
    "pool_name": "mypool",
    "pool_size": 5,
    "host": "localhost",
    "port": 13306,
    "user": "chatuser",
    "password": "chatpass",
    "database": "chatdb",
    "charset": "utf8mb4",
    "use_unicode": True,
    "connect_timeout": 30,       # 增加连接超时时间
    "connection_timeout": 30,    # 增加连接超时
    "pool_reset_session": True,
    "auth_plugin": "mysql_native_password",
    "use_pure": True,
    "raise_on_warnings": True,
    "autocommit": True,         # 自动提交
    "buffered": True,          # 使用缓冲游标   
    "get_warnings": True,      # 获取警告
    "unix_socket": None       # 强制使用TCP/IP连接
}
# Redis配置
REDIS_CONFIG = {
    "host": "localhost",
    "port": 16379,
    "db": 0,
    "decode_responses": True,  # 自动解码响应
    "socket_timeout": 5,      # socket超时
    "socket_connect_timeout": 5,  # 连接超时
    "retry_on_timeout": True    # 超时重试
}

# 安全配置
SECURITY_CONFIG = {
    "password_salt_size": 16,
    "token_expire_days": 7,
    "max_login_attempts": 5,
    "login_timeout_minutes": 30,
    "min_password_length": 8,
    "max_password_length": 64
}

# 消息配置
MESSAGE_CONFIG = {
    "max_length": 1000,
    "history_limit": 50,
    "rate_limit": 10,  # 每分钟最大消息数
    "flood_protection": True,
    "max_attachments": 5
}

# 频道配置
CHANNEL_CONFIG = {
    "max_channels": 10,
    "default_channel": "general",
    "system_channels": ["general", "random", "help"],
    "max_members": 1000,
    "name_max_length": 50
}

# 心跳配置
HEARTBEAT_CONFIG = {
    "interval": 10,        # 心跳包发送间隔（秒）
    "timeout": 30,        # 心跳超时时间（秒）
    "max_missed": 3       # 最大允许丢失心跳次数
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": "chat_server.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5
}

# 测试配置
TEST_CONFIG = {
    # 继承自 DB_CONFIG，但使用测试数据库
    **DB_CONFIG,
    "database": "chatdb_test",
    "pool_name": "test_pool",
    "pool_size": 3
}