import socket
import json
import threading
import time
from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button
from textual.containers import Container

class ChatClient(App):
    CSS_PATH = "chat.css"

    def __init__(self, username, server_host='localhost', server_port=12345):
        super().__init__()
        self.server_address = (server_host, server_port)
        self.username = username
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.sendto(json.dumps({"command": "join", "username": self.username}).encode('utf-8'), self.server_address)
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Chat Messages", id="chat_area"),
            Container(
                Input(placeholder="Type a message...", id="input_box"),
                Input(placeholder="Recipient (leave empty for broadcast)", id="recipient_box"),
                Button("Send", id="send_button"),
                id="input_container"
            ),
            Button("History", id="history_button"),
        )

    async def on_mount(self) -> None:
        self.message_box = self.query_one("#chat_area")
        self.input_box = self.query_one("#input_box")
        self.recipient_box = self.query_one("#recipient_box")
        
        # Start message receiving thread
        receiver_thread = threading.Thread(target=self.receive_messages)
        receiver_thread.daemon = True
        receiver_thread.start()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_button":
            self.send_message()
        elif event.button.id == "history_button":
            self.request_history()

    def send_message(self) -> None:
        msg_text = self.input_box.value
        recipient = self.recipient_box.value
        if msg_text:
            message = {"command": "message", "username": self.username, "message": msg_text}
            if recipient:
                message["recipient"] = recipient
            self.socket.sendto(json.dumps(message).encode('utf-8'), self.server_address)
            self.input_box.value = ""
            self.recipient_box.value = ""

    def request_history(self) -> None:
        message = {"command": "history", "username": self.username}
        self.socket.sendto(json.dumps(message).encode('utf-8'), self.server_address)

    def receive_messages(self):
        received_timestamps = set()
        while True:
            data, _ = self.socket.recvfrom(1024)
            msg = data.decode('utf-8')
            if msg.startswith("[History]"):
                history = json.loads(msg[9:])
                for item in history:
                    if item['timestamp'] not in received_timestamps:
                        received_timestamps.add(item['timestamp'])
                        self.message_box.update(self.message_box.renderable + f"\n{item['username']}: {item['message']}")
            else:
                self.message_box.update(self.message_box.renderable + "\n" + msg)

    def send_heartbeat(self):
        while True:
            heartbeat_message = {"command": "heartbeat", "username": self.username}
            self.socket.sendto(json.dumps(heartbeat_message).encode('utf-8'), self.server_address)
            time.sleep(10)  # 每10秒发送一次心跳包

if __name__ == "__main__":
    username = input("Enter your username: ")
    app = ChatClient(username)
    app.run()