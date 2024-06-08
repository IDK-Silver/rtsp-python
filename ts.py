# -*- coding: utf-8 -*-
'''
服务端接收用户请求
'''
import socket
import time

# 设置服务器的IP和端口
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5006

# 这是文件读写缓存区
BUFFER_SIZE = 4096

# 创建UDP Server
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((SERVER_HOST, SERVER_PORT))

while True:
    # 接收客户端信息
    received, address = s.recvfrom(BUFFER_SIZE)
    inio = received.decode("utf-8")
    print("接收客户端的消息：", inio)
    localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    #
    # with open("text.txt", "a+") as fp:
    #     fp.write(inio + "      " + localtime + "\n")

    # 发送OK回复到客户端
    s.sendto("OK".encode(), address)

    if inio.lower() == "del":
        break

s.close()
