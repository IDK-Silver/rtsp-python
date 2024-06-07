# -*- coding: utf-8 -*-
'''
服务端接收用户请求
'''
import  socket
import time
# import tqdm
# import os
#服务端读写
#设置服务器的IP和端口
SERVER_HOST="0.0.0.0"
SERVER_PORT=5004

#这是文件读写缓存区
BUFFER_SIZE=4096
SEPARATOR="<SEPARATOR>"

#创建Server
s=socket.socket()
s.bind((SERVER_HOST,SERVER_PORT))
#设置链接的监听数
s.listen(5)

#循环检测 接收客户端链接  调用 accept()时，Socket会进入“waiting”状态。客户请求连接时，方法建立连接并返回服务器。
# accept()返回一个含有两个元素的元组(conn, addr)。第一个元素conn是新的Socket对象，
# 服务器必须通过它与客户通信；第二个元素addr是客户的IP地址及端口。

client_socket,address=s.accept()
# print("客户端接收信息和地址",client_socket,address)

while True:
    #接收客户端信息
    received=client_socket.recv(BUFFER_SIZE)
    inio=received.decode("utf-8")
    print("接收客户端的消息：",inio)
    localtime =time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open("text.txt", "a+") as fp:
        fp.write(inio+"      "+localtime+"\n")
    if inio == "del" or inio == "DEL":
        break
    # else:
    #
    # else:
    #     text=input("客服1号：")
    #     client_socket.send(text.encode())
s.close()