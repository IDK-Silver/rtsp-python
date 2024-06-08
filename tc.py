# -*- coding: utf-8 -*-

import socket

# 设置IP和端口
SERVER_HOST = "114.35.234.248"
SERVER_PORT = 5006

# 这是文件读写缓存区
BUFFER_SIZE = 4096

# 创建UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    text = input("输入：")
    # 发送数据到服务器
    s.sendto(text.encode(), (SERVER_HOST, SERVER_PORT))

    # 接收服务器响应
    response, server_address = s.recvfrom(BUFFER_SIZE)
    print("服务器响应：", response.decode())

    if text.lower() == "del":
        break

s.close()
