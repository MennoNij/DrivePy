import os

class DataCollector(object):
    def __init__(self, name, filename, fields):
        self.name = name
        self.filename = filename
        self.fields = fields
        self.numFields = len(fields)
        self.entries = []
        self.delimiter = '\t'
        self.fp = open(self.filename,'w')
        self.writeRow(self.fields)
        self.fp.close()
        self.fp = 0

    def addData(self, data, flush):
    
        if len(data) % 2 > 0:
            print 'Collector['+self.name+']: not all data pairs are complete'
        else:
            entry = ['?'] * self.numFields

            for i in xrange(0, len(data), 2):
                idx = -1
                if data[i] in self.fields:
                    idx = self.fields.index(data[i])

                if idx >= 0:
                    entry[idx] = data[i+1]

            self.entries.append(entry)

            if flush:
                self.writeOut()

    def writeOut(self):
        if len(self.entries) > 0:
            for l in self.entries:
                self.writeRow(l)

            self.entries = []

    def writeRow(self, row):
        out = str(row[0])
        for i in range(1, len(row)):
            out += self.delimiter + str(row[i])
        out += '\n'
        self.fp.write(out)

    def open(self):
        self.fp = open(self.filename,'a')

    def close(self):
        if self.fp != 0:
            self.fp.close()
