
# 导入客户端应用
from client.chat_client import ChatClient, parse_args
from client.config import ChatConfig
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