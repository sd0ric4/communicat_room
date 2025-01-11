from server.chat_server import ChatServer

if __name__ == "__main__":
    try:
        server = ChatServer()
        server.run()
    except Exception as e:
        print(f"服务器启动错误: {str(e)}")