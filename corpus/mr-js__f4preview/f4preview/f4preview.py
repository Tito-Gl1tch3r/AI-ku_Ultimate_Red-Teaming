import struct
from PIL import Image, ImageDraw
from datetime import datetime, timedelta
import fnmatch
import os


class BethesdaSave:
    names = ('magic', 'headerSize', 'version', 'saveNumber', 'playerName',
             'playerLevel', 'playerLocation', 'gameDate', 'playerRaceEditorId',
             'playerSex', 'playerCurExp', 'playerLvlUpExp', 'filetime',
             'shotWidth', 'shotHeight', 'screenshotData', 'formVersion',
             'programVersion', 'pluginInfoSize', 'pluginCount')
    types = ('header', 'uint32', 'uint32', 'uint32', 'wstring',
             'uint32', 'wstring', 'wstring', 'wstring',
             'uint16', 'float32', 'float32', 'filetime',
             'uint32', 'uint32', 'pixels', 'uint8',
             'wstring', 'uint32', 'uint8')
    data = None
    values = ()
    offsets = ()
    count = 0
    offset = 0


    def readDataFromFile(self, file):
        with open(file, 'rb') as f:
            self.data = f.read()
        f.close()
        return self.data


    def bethesdaByteOffset(self, addition = 0):
        if self.offset is None:
            self.offset = 0
        else:
            self.offset += addition
        return self.offset


    def bethesdaByteSize(self, type):
        return {
            'uint32': 4,
            'uint16': 2,
            'uint8': 1,
            'float32': 4,
            'wstring': int(struct.unpack(
                '<h',
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset() + 2])
            [0]),
            'filetime': 8,
            'header': 12
        }.get(type, 0)


    def bethesdaByteSymbol(self, type):
        return {
            'uint32': '<I',
            'uint16': '<h',
            'uint8': '<B',
            'float32': '<f',
            'wstring': '<' + str(struct.unpack(
                '<h',
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset() + 2])
            [0]) + 's',
            'filetime': '<8s',
            'header': '<12s'
        }.get(type, 0)


    def bethesdaByteValue(self, type):
        if (type == 'wstring'):
            result = struct.unpack(
                self.bethesdaByteSymbol(type),
                self.data[self.bethesdaByteOffset() + 2:
                self.bethesdaByteOffset(self.bethesdaByteSize(type)) + 2]
            )[0].decode()
            self.bethesdaByteOffset(2)
        elif (type == 'pixels'):
            size = self.bethesdaByteSize('uint8') * 4 * 640 * 384
            symbol = '<' + str(size) + 's'
            result = struct.unpack(
                symbol,
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset(size)]
            )[0]
        elif (type == 'header'):
            result = struct.unpack(
                self.bethesdaByteSymbol(type),
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset(self.bethesdaByteSize(type))]
            )[0].decode()
        elif (type == 'filetime'):
            result = struct.unpack(
                self.bethesdaByteSymbol(type),
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset(self.bethesdaByteSize(type))]
            )[0]
            result = (datetime(1970, 1, 1) + timedelta(microseconds=struct.unpack('<Q', result)[0] // 10 - 11644473600000000)).strftime("%d.%m.%Y %H:%M:%S")
        else:
            result = struct.unpack(
                self.bethesdaByteSymbol(type),
                self.data[self.bethesdaByteOffset() :
                self.bethesdaByteOffset(self.bethesdaByteSize(type))]
            )[0]
        return result


    def preview(self, path, file):
        print(file)
        self.data = self.readDataFromFile(os.path.join(path, file))
        self.values = ()
        self.offsets = ()
        self.count = 0
        self.offset = 0
        for type in self.types:
            self.count += 1
            self.offsets += (self.bethesdaByteOffset(0),)
            self.values += (self.bethesdaByteValue(type),)
        for i in range(self.values[self.count-1]):
            self.names += ('plugin #' + str(i+1), )
            self.types += ('wstring', )
            self.values += (self.bethesdaByteValue('wstring'),)
            self.offsets += (self.bethesdaByteOffset(0),)
            self.count += 1
            width, height = 640, 384
            img = Image.frombytes('RGBA', (width, height), self.values[15])
            draw = ImageDraw.Draw(img)
        print(''.ljust(80, '-'))
        print('self.offset'.ljust(10, ' ') + 'name'.ljust(20, ' ') + 'type'.ljust(20, ' ') +
              'value'.ljust(20, ' '))
        print(''.ljust(80, '-'))
        y = 0
        for item in list(zip(self.offsets, self.names, self.types, self.values)):
                        print(
                            (str(item[0]).zfill(8)).ljust(10, ' ') +
                            (str(item[1])).ljust(20, ' ') +
                            (str(item[2])).ljust(10, ' ') +
                            (str(item[3])[:40]).ljust(20, ' ')
                        )
                        try:
                            draw.text((0, y),str(item[1]).ljust(20, ' ') + str(item[3])[:40],(255,255,255))
                            y += 10
                        except:
                            pass
        print(''.ljust(80, '-'))
        img.convert('RGB').save(os.path.join(path, file + '.jpg'))
        print()


pattern = '*.fos'
path = os.getcwd()
for file in fnmatch.filter(os.listdir(path), pattern):
    bs = BethesdaSave()
    bs.preview(path, file)
