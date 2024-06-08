from tkinter import *
import tkinter.messagebox as tkMessageBox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

import miniupnpc

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    PLAYING2 = 3#
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    SPEEDUP = 4  #new
    #	REPLAY = 5

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.rtp_socket = None
        self.rtspSocket = None
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0




    # def setup_port_forwarding(self, protocol, external_port, internal_port):
    #     upnp = miniupnpc.UPnP()
    #     upnp.discoverdelay = 200  # 延迟200ms进行设备发现
    #     upnp.discover()  # 发现 UPnP 设备
    #     upnp.selectigd()  # 选择 IGD (Internet Gateway Device)
    #
    #     internal_client = upnp.lanaddr  # 内部客户端的 IP 地址
    #
    #     # 添加端口映射
    #     try:
    #         upnp.addportmapping(external_port, protocol, internal_client, internal_port, 'UPnP Test', '')
    #         print(f"Port {external_port} forwarded to {internal_client}:{internal_port} ({protocol})")
    #     except Exception as e:
    #         print(f"Failed to add port mapping: {e}")

    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create SPEEDUP button new
        self.speedup = Button(self.master, width=20, padx=3, pady=3)
        self.speedup["text"] = "Speedup"
        self.speedup["command"] = self.speedUP
        self.speedup.grid(row=1, column=4, padx=2, pady=2)
        #REPLAY
        #		self.restart = Button(self.master, width=20, padx=3, pady=3)
        #		self.restart["text"] = "Replay"
        #		self.restart["command"] = self.replayMovie
        #		self.restart.grid(row=1, column=5, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.connectToServer()
            print(self.rtspSocket.getsockname())
            extern_port = self.rtspSocket.getsockname()[1]
            # self.setup_port_forwarding('TCP', extern_port, extern_port)
            self.sendRtspRequest(self.SETUP)



    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy() # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING or self.state == self.PLAYING2:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY or self.state == self.PLAYING2:
            print('start new thread to listen rtp')
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)
    #New
    def speedUP(self):
        """Play button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.SPEEDUP)
    #	def replayMovie(self):
    #		"""Play button handler."""
    #		if self.state == self.PLAYING or self.state == self.PLAYING2 or self.state == self.READY:
    #			self.sendRtspRequest(self.REPLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        print('success start listen rtp ')
        while True:
            try:
                data, address = self.rtp_socket.recvfrom(8192)
                if data is not None:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    print("Current Seq Num: " + str(currFrameNbr))

                    print(rtpPacket.getPayload())

                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                print('error recv rtp')
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtp_socket.shutdown(socket.SHUT_RDWR)
                    self.rtp_socket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image = photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtspSocket.settimeout(None)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""

        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = 1
            # Write the RTSP request to be sent.
            request = "SETUP " + str(self.fileName) + "\n " + str(self.rtspSeq) + " \n RTSP/1.0 RTP/UDP " + str(self.rtpPort) + ' '
            self.rtspSocket.send(request.encode())
            threading.Thread(target=self.recvRtspReply).start()


        # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PLAY " + str(self.fileName)+ "\n " + str(self.rtspSeq)
            self.rtspSocket.send(request.encode("utf-8"))
            print ('-'*60 + "\nPLAY request sent to Server...\n" + '-'*60)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PLAY
        # Pause request
        elif requestCode == self.PAUSE and (self.state == self.PLAYING or self.state == self.PLAYING2):
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PAUSE " + str(self.fileName) + "\n " + str(self.rtspSeq)
            self.rtspSocket.send(request.encode("utf-8"))
            print ('-'*60 + "\nPAUSE request sent to Server...\n" + '-'*60)
            # Keep track of the sent request.
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PAUSE
        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "TEARDOWN " + str(self.fileName) + "\n " + str(self.rtspSeq)
            self.rtspSocket.send(request.encode("utf-8"))
            print ('-'*60 + "\nTEARDOWN request sent to Server...\n" + '-'*60)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.TEARDOWN
        #new
        elif requestCode == self.SPEEDUP and self.state == self.PLAYING:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "SPEEDUP " + str(self.fileName)+ "\n " + str(self.rtspSeq)
            self.rtspSocket.send(request.encode("utf-8"))
            print ('-'*60 + "\nSPEEDUP request sent to Server...\n" + '-'*60)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.SPEEDUP
        #		elif requestCode == self.REPLAY and (self.state == self.PLAYING or self.state == self.PLAYING2 or self.state == self.READY):
        # Update RTSP sequence number.
        # ...
        #			self.rtspSeq = self.rtspSeq + 1
        # Write the RTSP request to be sent.
        # request = ...
        #			request = "REPLAY " + str(self.fileName)+ "\n " + str(self.rtspSeq)
        #			self.rtspSocket.send(request.encode("utf-8"))
        #			print ('-'*60 + "\nREPLAY request sent to Server...\n" + '-'*60)
        # Keep track of the sent request.
        # self.requestSent = ...
        #			self.requestSent = self.REPLAY
        else:
            return

        # Send the RTSP request using rtspSocket.
        # ...
        self.rtspSocket.send(request.encode())

        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            self.rtspSocket.settimeout(None)
            reply = self.rtspSocket.recv(4096)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):

        print('parse rtsp reply')
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:

                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        # self.state = ...
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        # self.state = ...
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        # self.state = ...
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1
                    elif self.requestSent == self.SPEEDUP:
                        # self.state = ...
                        self.state = self.PLAYING2
                    elif self.requestSent == self.REPLAY:
                        # self.state = ...
                        self.state = self.PLAYING

    def openRtpPort(self):
        print('binding RTP port')
        # self.setup_port_forwarding('UDP', self.rtpPort, self.rtpPort)
        # Create a new datagram socket to receive RTP packets from the server
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # ...
        # self.rtp_socket.settimeout(None)
        try:

            # binding localhost because udp is rev from server
            # the server need to send packet to client (localhost)
            self.rtp_socket.bind(('', self.rtpPort))
        except:
            tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            self.playMovie()
