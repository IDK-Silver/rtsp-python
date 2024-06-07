import sys, socket

from ServerWorker import ServerWorker


class Server:

    def main(self):
        server_port: int = 0

        try:
            server_port = int(sys.argv[1])
        except:
            print("[Usage: Server.py Server_port]\n")

        rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        rtsp_socket.bind((ip_address, server_port))
        rtsp_socket.listen(5)

        # Receive client info (address,port) through RTSP/TCP session
        while True:
            client_info = {}

            # socket.accept will return (client_socket, client_address)
            client_info['rtspSocket'] = rtsp_socket.accept()
            # client_info['rtspSocket'][0].settimeout(None)
            ServerWorker(client_info).run()


if __name__ == "__main__":
    (Server()).main()
