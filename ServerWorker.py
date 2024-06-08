from random import randint
import threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    SPEEDUP = 'SPEEDUP'

    INIT = 0
    READY = 1
    PLAYING = 2
    PLAYING2 = 3
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    def __init__(self, client_info):
        self.clientInfo = client_info
        # Create a new socket for RTP/UDP
        self.clientInfo['rtpSocket'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    def run(self):
        threading.Thread(target=self.recv_rtsp_request).start()

    def recv_rtsp_request(self):
        """Receive RTSP request from the client."""
        conn_socket = self.clientInfo['rtspSocket'][0]
        while True:
            data = conn_socket.recv(2048)
            if data:
                print("Data received:\n" + data.decode("utf-8"))
                self.process_rtsp_request(data.decode("utf-8"))

    def process_rtsp_request(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        request_type = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if request_type == self.SETUP:
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.reply_rtsp(self.FILE_NOT_FOUND_404, seq[1])

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)

                # Send RTSP reply
                self.reply_rtsp(self.OK_200, seq[1])

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = request[2].split(' ')[3]
                # print(self.clientInfo['rtpPort'])


        # Process PLAY request
        elif request_type == self.PLAY:
            if self.state == self.READY or self.state == self.PLAYING2:
                print("processing PLAY\n")
                self.state = self.PLAYING

                self.reply_rtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.send_rtp)
                self.clientInfo['worker'].start()

        # Process PAUSE request
        elif request_type == self.PAUSE:
            if self.state == self.PLAYING or self.state == self.PLAYING2:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.reply_rtsp(self.OK_200, seq[1])


        # Process TEARDOWN request
        elif request_type == self.TEARDOWN:
            print("processing TEARDOWN\n")

            self.clientInfo['event'].set()

            self.reply_rtsp(self.OK_200, seq[1])

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()

        # Process SPEEDUP request
        elif request_type == self.SPEEDUP:
            if self.state == self.PLAYING:
                print("processing SPEEDUP\n")
                self.state = self.PLAYING2
                # Create a new socket for RTP/UDP
                # self.clientInfo['rtpSocket'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.reply_rtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.send_rtp_fast)  ##
                self.clientInfo['worker'].start()

    def send_rtp(self):
        """Send RTP packets over UDP."""
        while True:
            print('send rtp')
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    client_ip = self.clientInfo['rtspSocket'][1][0]
                    client_rtp_port = self.clientInfo['rtpPort']

                    address = (
                        client_ip,
                        int(client_rtp_port)
                    )
                    print('rtp target', address)
                    # print(address, port)
                    self.clientInfo['rtpSocket'].sendto(self.make_rtp_packet(data, frameNumber), address)
                except:
                    print("Connection Error")

    def send_rtp_fast(self):

        while True:
            self.clientInfo['event'].wait(0.25)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.make_rtp_packet(data, frameNumber), (address, port))
                except:
                    print("Connection Error")
                #print('-'*60)
                #traceback.print_exc(file=sys.stdout)

    def make_rtp_packet(self, payload, frame_num):

        # RTP-packet size the video data
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seq_num = frame_num
        ssrc = 0

        rtp_packet = RtpPacket()

        rtp_packet.encode(version, padding, extension, cc, seq_num, marker, pt, ssrc, payload)

        return rtp_packet.getPacket()

    def reply_rtsp(self, code, seq):
        print('start reply rtsp', code, seq)
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            #print("200 OK")
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
            conn_socket = self.clientInfo['rtspSocket'][0]
            print('replay content ', reply.encode())
            conn_socket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
