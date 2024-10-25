import socket
import threading
from typing import Set, Tuple
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# 定义服务器地址和端口
SERVER_ADDRESS: Tuple[str, int] = ("localhost", 12345)

# 存储已连接的客户端
clients: Set[Tuple[str, int]] = set()

# UDP 套接字
udp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind(SERVER_ADDRESS)


def handle_client() -> None:
    """处理客户端消息的函数"""
    while True:
        message, client_address = udp_socket.recvfrom(1024)
        if client_address not in clients:
            clients.add(client_address)
        broadcast(message, client_address)


def broadcast(message: bytes, sender_address: Tuple[str, int]) -> None:
    """广播消息给所有连接的客户端"""
    for client in clients:
        if client != sender_address:
            udp_socket.sendto(message, client)


@app.on_event("startup")
def startup_event() -> None:
    """在应用启动时启动UDP处理线程"""
    threading.Thread(target=handle_client, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
async def read_root() -> str:
    """简单的HTML界面"""
    return """
    <html>
        <head>
            <title>UDP Chat Room</title>
        </head>
        <body>
            <h1>Welcome to the UDP Chat Room!</h1>
            <form action="/send" method="post">
                <input type="text" name="message" placeholder="Enter your message" required>
                <input type="text" name="address" placeholder="Enter recipient address (e.g., localhost:12345)" required>
                <button type="submit">Send</button>
            </form>
        </body>
    </html>
    """


@app.post("/send")
async def send_message(message: str, address: str) -> dict:
    """发送消息到指定地址"""
    try:
        host, port = address.split(":")
        udp_socket.sendto(message.encode("utf-8"), (host, int(port)))
        return {"status": "Message sent"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)