import binascii
import requests
import struct

class Helper():
    @staticmethod
    def downloader(source, dest):
        req = requests.get(source, stream=True, timeout=10)

        if req.status_code == 200:
            with open(dest, 'wb') as fil:
                for chunk in req.iter_content(1024):
                    fil.write(chunk)
        else:
            raise Exception('File not found')


    @staticmethod
    def pronto2lirc(pronto):
        codes = [int(binascii.hexlify(pronto[i:i+2]), 16) for i in range(0, len(pronto), 2)]

        if codes[0]:
            raise ValueError('Pronto code should start with 0000')
        if len(codes) != 4 + 2 * (codes[2] + codes[3]):
            raise ValueError('Number of pulse widths does not match the preamble')

        frequency = 1 / (codes[1] * 0.241246)
        return [int(round(code / frequency)) for code in codes[4:]]

    @staticmethod
    def lirc2broadlink(pulses):
        array = bytearray()

        for pulse in pulses:
            pulse = int(pulse * 269 / 8192)

            if pulse < 256:
                array += bytearray(struct.pack('>B', pulse))
            else:
                array += bytearray([0x00])
                array += bytearray(struct.pack('>H', pulse))

        packet = bytearray([0x26, 0x00])
        packet += bytearray(struct.pack('<H', len(array)))
        packet += array
        packet += bytearray([0x0d, 0x05])

        # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
        remainder = (len(packet) + 4) % 16
        if remainder:
            packet += bytearray(16 - remainder)

        return packet
