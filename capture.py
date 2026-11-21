"""Linux AF_PACKET and macOS native BPF capture backends."""
import errno
import fcntl
import os
import select
import socket
import struct
import sys
import time


class LinuxCapture:
    name = 'Linux Raw Socket · AF_PACKET / SOCK_RAW'

    def __init__(self, interface):
        self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        try:
            self.socket.bind((interface, 0))
            self.socket.settimeout(0.3)
        except Exception:
            self.socket.close()
            raise
        self.linktype = 1

    def read(self):
        try:
            frame, address = self.socket.recvfrom(262144)
        except socket.timeout:
            return []
        direction = '송신' if address[2] == 4 else '수신'
        return [(time.time(), frame, direction)]

    def close(self):
        self.socket.close()


class MacCapture:
    name = 'macOS 네이티브 BPF · /dev/bpf'

    @staticmethod
    def ioctl_code(operation, number, size):
        return operation | (size << 16) | (ord('B') << 8) | number

    def __init__(self, interface):
        self.fd = None
        denied = False
        for number in range(256):
            try:
                self.fd = os.open('/dev/bpf{}'.format(number), os.O_RDONLY | os.O_NONBLOCK)
                break
            except OSError as exc:
                denied = denied or exc.errno in (errno.EACCES, errno.EPERM)
                if exc.errno not in (errno.EBUSY, errno.EACCES, errno.EPERM, errno.ENOENT):
                    raise
        if self.fd is None:
            if denied:
                raise PermissionError('BPF 장치 접근 권한이 필요합니다. 안내서를 확인하세요.')
            raise OSError('사용할 수 있는 BPF 장치가 없습니다.')
        try:
            # Darwin ifreq is 32 bytes. BPF timestamps use timeval32 on LP64.
            fcntl.ioctl(self.fd, self.ioctl_code(0x80000000,108,32), struct.pack('32s', interface.encode()))
            fcntl.ioctl(self.fd, self.ioctl_code(0x80000000,112,4), struct.pack('I',1))
            fcntl.ioctl(self.fd, self.ioctl_code(0x80000000,119,4), struct.pack('I',1))
            self.buffer_size = self.get_uint(102)
            self.linktype = self.get_uint(106)
            if self.linktype not in (0, 1, 12, 101, 108):
                raise ValueError('이 인터페이스의 링크 유형은 지원하지 않습니다. lo0 또는 en0를 선택하세요.')
        except Exception:
            self.close()
            raise

    def get_uint(self, number):
        value = fcntl.ioctl(self.fd, self.ioctl_code(0x40000000,number,4), bytes(4))
        return struct.unpack('I',value)[0]

    def read(self):
        if not select.select([self.fd], [], [], 0.3)[0]:
            return []
        try:
            block = os.read(self.fd, self.buffer_size)
        except BlockingIOError:
            return []
        offset, packets = 0, []
        while offset + 18 <= len(block):
            sec, usec, caplen, wirelen, hdrlen = struct.unpack_from('=IIIIH', block, offset)
            end = offset + hdrlen + caplen
            if hdrlen < 18 or end > len(block):
                raise ValueError('잘못된 BPF 레코드')
            packets.append((sec + usec / 1e6, block[offset + hdrlen:end], '미확인'))
            offset += (hdrlen + caplen + 3) & ~3
        return packets

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def open_capture(interface):
    if interface not in [name for _, name in socket.if_nameindex()]:
        raise ValueError('존재하지 않는 네트워크 인터페이스')
    if sys.platform.startswith('linux'):
        return LinuxCapture(interface)
    if sys.platform == 'darwin':
        return MacCapture(interface)
    raise RuntimeError('지원하는 운영체제는 Linux와 macOS입니다.')


def interface_ip(interface):
    if sys.platform == 'darwin':
        # SIOCGIFADDR, Darwin struct ifreq. IPv4 address is at offset 20.
        request = 0xC0206921
    else:
        request = 0x8915
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            data = fcntl.ioctl(sock.fileno(), request, struct.pack('256s', interface.encode()[:15]))
            return socket.inet_ntoa(data[20:24])
        except OSError:
            return None
