import argparse
import socket
import json
import threading
import sys
import time
from .config import ChatConfig
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Label, ListView, ListItem
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.validation import Length

class NetworkManager:
    def __init__(self, host='127.0.0.1', port=12345):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.5)  # 设置超时
        self.server_address = (host, port)
        self.username = None
        self.current_channel = "general"
        self.channels = []
        self.heartbeat_thread = None
        self.running = False

    def authenticate(self, username, password):
        message = json.dumps({
            "command": "auth",
            "username": username, 
            "password": password
        }).encode()
        
        self.socket.sendto(message, self.server_address)
        try:
            # 第一个响应：频道列表或失败
            data, _ = self.socket.recvfrom(4096)
            response = json.loads(data.decode())
            
            # 如果是频道列表，说明认证成功
            if response.get("type") == "channel_list":
                self.channels = response.get("channels", [])
                
                # 接收历史消息
                data, _ = self.socket.recvfrom(4096)
                history = json.loads(data.decode())
                
                return {
                    "status": True,
                    "channels": self.channels,
                    "history": history.get("messages", [])
                }
            
            # 如果不是频道列表，可能是认证失败
            return {"status": False}
        
        except Exception as e:
            print(f"认证错误: {e}")
            return {"status": False}
    def register(self, username, password):
        message = json.dumps({
            "command": "register",
            "username": username, 
            "password": password
        }).encode()
        
        self.socket.sendto(message, self.server_address)
        data, _ = self.socket.recvfrom(4096)
        return data.decode() == "REGISTER_SUCCESS"

    def send_message(self, content, recipient=None):
        message = {
            "command": "message",
            "username": self.username,
            "content": content,
            "channel": self.current_channel
        }
        if recipient:
            message["recipient"] = recipient
        
        encoded_message = json.dumps(message).encode()
        self.socket.sendto(encoded_message, self.server_address)

    def join_channel(self, channel_name):
        message = {
            "command": "join_channel",
            "username": self.username,
            "channel": channel_name
        }
        encoded_message = json.dumps(message).encode()
        self.socket.sendto(encoded_message, self.server_address)
        self.current_channel = channel_name

    def start_heartbeat(self):
        def heartbeat_loop():
            while self.running:
                try:
                    heartbeat = {
                        "command": "heartbeat",
                        "username": self.username
                    }
                    self.socket.sendto(json.dumps(heartbeat).encode(), self.server_address)
                    time.sleep(30)  # 每30秒发送一次心跳
                except Exception as e:
                    print(f"心跳错误: {e}")
                    break

        self.running = True
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

class AuthScreen(Screen):
    def __init__(self, network_manager):
        super().__init__()
        self.network_manager = network_manager
        self.is_login_mode = True

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="login-container"):
            yield Label("聊天室", classes="title")
            yield Label(id="mode_label")
            
            yield Input(
                placeholder="用户名", 
                id="username_input",
                validators=[Length(minimum=3, maximum=20)]
            )
            yield Input(
                placeholder="密码", 
                password=True, 
                id="password_input",
                validators=[Length(minimum=6)]
            )
            
            yield Label(id="error_label", classes="error")
            
            with Horizontal(classes="button-container"):
                yield Button("登录", id="auth_button", variant="primary")
                yield Button("切换到注册", id="switch_mode_button", variant="default")

        yield Footer()

    def on_mount(self):
        self.update_mode()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "auth_button":
            self.attempt_auth()
        elif event.button.id == "switch_mode_button":
            self.toggle_mode()

    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode
        self.update_mode()

    def update_mode(self):
        mode_label = self.query_one("#mode_label", Label)
        auth_button = self.query_one("#auth_button", Button)
        switch_mode_button = self.query_one("#switch_mode_button", Button)
        error_label = self.query_one("#error_label", Label)

        if self.is_login_mode:
            mode_label.update("登录")
            auth_button.label = "登录"
            switch_mode_button.label = "切换到注册"
        else:
            mode_label.update("注册")
            auth_button.label = "注册"
            switch_mode_button.label = "切换到登录"
        
        # 清空错误信息
        error_label.update("")

    def attempt_auth(self):
        username = self.query_one("#username_input", Input).value
        password = self.query_one("#password_input", Input).value
        error_label = self.query_one("#error_label", Label)

        try:
            if self.is_login_mode:
                # 登录
                result = self.network_manager.authenticate(username, password)
                if result.get("status"):
                    self.network_manager.username = username
                    self.network_manager.start_heartbeat()
                    self.app.push_screen(ChatScreen(
                        self.network_manager, 
                        result.get("channels", []),
                        result.get("history", [])
                    ))
                else:
                    error_label.update("登录失败，请检查用户名和密码")
            else:
                # 注册
                if self.network_manager.register(username, password):
                    error_label.update("注册成功，请登录")
                    self.is_login_mode = True
                    self.update_mode()
                else:
                    error_label.update("注册失败，用户名可能已存在")
        except Exception as e:
            error_label.update(f"发生错误：{str(e)}")

class ChatScreen(Screen):
    
    def __init__(self, network_manager, channels, history):
        super().__init__()
        self.network_manager = network_manager
        self.channels = channels
        self.history = history
        self.received_messages = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="chat-container"):
            with Horizontal():
                # 频道列表
                with Vertical(classes="channel-list"):
                    yield Label("频道列表", classes="section-title")
                    yield ListView(id="channel_list")

                # 消息区域
                with Vertical(classes="message-area"):
                    yield Static(id="message_list")
                    with Horizontal(classes="input-area"):  # 添加类名
                        yield Input(
                            placeholder="输入消息...", 
                            id="message_input",
                            classes="message-input"  # 添加类名
                        )
                        yield Input(
                            placeholder="私聊对象(可选)", 
                            id="recipient_input",
                            classes="recipient-input"  # 添加类名
                        )

        yield Footer()
    def on_mount(self):
        # 填充频道列表
        channel_list = self.query_one("#channel_list", ListView)
        for channel in self.channels:
            channel_list.append(ListItem(Label(channel['name'])))
        
        # 显示历史消息
        self.update_message_list(self.history)

        # 启动消息接收线程
        self.message_thread = threading.Thread(
            target=self.receive_messages, 
            daemon=True
        )
        self.message_thread.start()

    def on_list_view_selected(self, message: ListView.Selected):
        # 切换频道
        selected_channel = message.item.query_one(Label).renderable
        self.network_manager.join_channel(selected_channel)

    def on_input_submitted(self, message: Input.Submitted):
        if message.input.id == "message_input":
            content = message.input.value
            recipient = self.query_one("#recipient_input", Input).value or None
            self.network_manager.send_message(content, recipient)
            message.input.value = ""  # 清空输入框

    def update_message_list(self, messages):
        message_list = self.query_one("#message_list", Static)
        # 格式化消息并显示,增加私聊标注
        formatted_messages = "\n".join([
            f"[私聊] {msg.get('sender', 'Unknown')}: {msg.get('content', '')}" 
            if msg.get('is_private') 
            else f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        message_list.update(formatted_messages)

    def receive_messages(self):
        while True:
            try:
                data, _ = self.network_manager.socket.recvfrom(4096)
                message = json.loads(data.decode())
                
                # 处理不同类型的消息
                if message.get("type") == "message":
                    self.received_messages.append(message)
                    self.update_message_list(self.received_messages)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收消息错误: {e}")
                break
def parse_args():
    parser = argparse.ArgumentParser(description="聊天室客户端")
    parser.add_argument("--host", help="服务器地址")
    parser.add_argument("--port", type=int, help="服务器端口")
    parser.add_argument("--config", help="配置文件路径", default="chat_config.json")
    return parser.parse_args()

class ChatClient(App):
    CSS = """
    .input-area {
        width: 100%;
        height: auto;
        padding: 1;
    }

    .message-input {
        width: 70%;
        margin-right: 1;
    }

    .recipient-input {
        width: 30%;
    }
    """
    def __init__(self, config: ChatConfig):
        super().__init__()
        self.network_manager = NetworkManager(host=config.host, port=config.port)

    def on_mount(self):
        self.push_screen(AuthScreen(self.network_manager))

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置文件
    config = ChatConfig.load_from_file(args.config)
    
    # 命令行参数覆盖配置文件
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    
    # 保存当前配置
    config.save_to_file(args.config)
    
    # 启动应用
    app = ChatClient(config)
    app.run()

if __name__ == "__main__":
    main()