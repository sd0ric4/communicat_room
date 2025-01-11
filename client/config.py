import json
from dataclasses import dataclass

@dataclass
class ChatConfig:
    host: str = "127.0.0.1"
    port: int = 12345

    @classmethod
    def load_from_file(cls, filepath: str) -> "ChatConfig":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError:
            print("配置文件格式错误，使用默认配置")
            return cls()
        
    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "host": self.host,
                "port": self.port
            }, f, ensure_ascii=False, indent=2)