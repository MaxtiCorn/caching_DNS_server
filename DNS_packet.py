import struct
import json
from enum import Enum


class RecordTypes(Enum):
    A = 1
    AAAA = 28
    NS = 2


class RecordClasses(Enum):
    IN = 1


class Header:
    def __init__(self, id=0, qr=0, opcode=0, rd=0,
                 questions_count=0, ancount=0, nscount=0, arcount=0):
        self.id = id  # transaction id
        self.qr = qr  # 1-response 0-query
        self.opcode = opcode  # operation code
        self.aa = 0  # authoritative answer
        self.tc = 0  # truncation
        self.rd = rd  # recursion desired
        self.ra = 0  # recursion available
        self.z = 0  # zero
        self.rcode = 0  # response code
        self.qdcount = questions_count  # questions count
        self.ancount = ancount  # answer record count
        self.nscount = nscount  # authority record count
        self.arcount = arcount  # additional record count

    def __str__(self):
        return str(self.id) + ' ' + str(self.qr) + ' ' + str(self.opcode) + ' ' \
               + str(self.aa) + ' ' + str(self.tc) + ' ' + str(self.rd) + ' ' \
               + str(self.ra) + ' ' + str(self.z) + ' ' + str(self.rcode) + ' ' \
               + str(self.qdcount) + ' ' + str(self.ancount) + ' ' + str(self.nscount) + ' ' + str(self.arcount)

    def to_bytes(self):
        result = b''
        result += struct.pack('!H', self.id)
        result += struct.pack('!B', self.qr << 7 | self.opcode << 3 | self.aa << 2 | self.tc << 1 | self.rd)
        result += struct.pack('!B', self.ra << 7 | self.z << 3 | self.rcode)
        result += struct.pack('!HHHH', self.qdcount, self.ancount, self.nscount, self.arcount)
        return result

    def from_bytes(self, data, start_index):
        fields = struct.unpack('!HBBHHHH', data[start_index:struct.calcsize('!HBBHHHH')])
        self.id = fields[0]
        self.qr = fields[1] >> 7 & 0x1  # qr
        self.opcode = fields[1] >> 3 & 0b1111  # opcode
        self.aa = fields[1] >> 2 & 0x1  # aa
        self.tc = fields[1] >> 1 & 0x1  # tc
        self.rd = fields[1] & 0x1  # rd
        self.ra = fields[2] >> 7 & 0x1
        self.z = fields[2] >> 3 & 0x7
        self.rcode = fields[2] & 0b1111
        self.qdcount = fields[3]
        self.ancount = fields[4]
        self.nscount = fields[5]
        self.arcount = fields[6]
        return 12

    def to_dict(self):
        return {
            'id': self.id, 'qr': self.qr, 'opcode': self.opcode,
            'aa': self.aa, 'tc': self.tc, 'rd': self.rd,
            'ra': self.ra, 'z': self.z, 'rcode': self.rcode,
            'qdcount': self.qdcount, 'ancount': self.ancount,
            'nscount': self.nscount, 'arcount': self.arcount
        }

    def from_dict(self, dict):
        self.id = int(dict['id'])
        self.qr = int(dict['qr'])
        self.opcode = int(dict['opcode'])
        self.aa = int(dict['aa'])
        self.tc = int(dict['tc'])
        self.rd = int(dict['rd'])
        self.ra = int(dict['ra'])
        self.z = int(dict['z'])
        self.rcode = int(dict['rcode'])
        self.qdcount = int(dict['qdcount'])
        self.ancount = int(dict['ancount'])
        self.nscount = int(dict['nscount'])
        self.arcount = int(dict['arcount'])


def _name_to_bytes(name):
    name_parts = name.split('.')
    chars_lists = ([char for char in part] for part in name_parts)
    result = b''
    for char_gen in chars_lists:
        result += struct.pack('!B', len(char_gen))
        for char in char_gen:
            result += struct.pack('!c', char.encode('ASCII'))
    if result != b'\x00':
        result += struct.pack('!B', 0)
    return result


def _name_from_bytes(data, index=0):
    domain_name = []
    count = data[index]
    while count != 0:
        if count >= 192:
            index += 1
            hop = (count << 2 & 0b111111) + data[index]
            name, _ = _name_from_bytes(data, hop)
            domain_name.append(name)
            return '.'.join(domain_name), index + 1
        else:
            index += 1
            domain = data[index:index + count]
            decoded = domain.decode()
            domain_name.append(decoded)
            index += count
            count = data[index]
    return '.'.join(domain_name), index + 1


def _rdata_from_bytes(data, start_index, end_index, a_type):
    if a_type == RecordTypes.A.value:
        data = data[start_index:end_index]
        return '{0}.{1}.{2}.{3}'.format(data[0], data[1], data[2], data[3])
    elif a_type == RecordTypes.AAAA.value:
        data = data[start_index:end_index]
        return data
    else:
        name, _ = _name_from_bytes(data, start_index)
        return name


def _rdata_to_bytes(rdata, a_type):
    if rdata == '':
        return b''
    if a_type == RecordTypes.A.value:
        parts = rdata.split('.')
        return struct.pack('!BBBB', int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    elif a_type == RecordTypes.AAAA.value:
        try:
            return bytes(rdata)
        except:
            return rdata.replace('b', '').replace('\'', '').encode()
    else:
        return _name_to_bytes(rdata)


class Question:
    def __init__(self, qname='', qtype=RecordTypes.A, qclass=RecordClasses.IN):
        self.qname = qname  # domain name
        self.qtype = qtype.value  # type
        self.qclass = qclass.value  # class

    def __str__(self):
        return self.qname + ' ' + str(self.qtype) + ' ' + str(self.qclass)

    def to_bytes(self):
        result = b''
        result += _name_to_bytes(self.qname)
        result += struct.pack('!hh', self.qtype, self.qclass)
        return result

    def from_bytes(self, data, start_index):
        self.qname, offset = _name_from_bytes(data, start_index)
        ndt = data[offset:offset + 4]
        fields = struct.unpack('!hh', ndt)
        self.qtype = fields[0]
        self.qclass = fields[1]
        return offset + 4

    def to_dict(self):
        return {
            'qname': self.qname,
            'qtype': self.qtype,
            'qclass': self.qclass
        }

    def from_dict(self, dictionary):
        self.qname = dictionary['qname']
        self.qtype = dictionary['qtype']
        self.qclass = dictionary['qclass']

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(self, json_str):
        dictionary = json.loads(json_str)
        self.from_dict(dictionary)


class ResourceRecord:
    def __init__(self, name='', type=RecordTypes.NS, rrclass=RecordClasses.IN, ttl=100, rdlength=0, rdata=''):
        self.name = name  # domain name
        self.type = type.value  # type
        self.rr_class = rrclass.value  # class
        self.ttl = ttl  # ttl
        self.rdlength = rdlength  # rdata length
        self.rdata = rdata  # rdata

    def __str__(self):
        return self.name + '|' + str(self.type) + '|' \
               + str(self.rr_class) + '|' + str(self.ttl) + '|' \
               + str(self.rdlength) + '|' + str(self.rdata)

    def to_bytes(self):
        result = b''
        result += _name_to_bytes(self.name)
        result += struct.pack('!H', self.type)
        result += struct.pack('!H', self.rr_class)
        result += struct.pack('!I', self.ttl)
        rdata = _rdata_to_bytes(self.rdata, self.type)
        result += struct.pack('!H', len(rdata))
        result += rdata
        return result

    def from_bytes(self, data, start_index):
        self.name, offset = _name_from_bytes(data, start_index)
        l = struct.calcsize('!HHIH')
        nd = data[offset:offset + l]
        fields = struct.unpack('!HHIH', nd)
        self.type = fields[0]
        self.rr_class = fields[1]
        self.ttl = fields[2]
        self.rdlength = fields[3]
        self.rdata = _rdata_from_bytes(data, offset + l, offset + l + self.rdlength, self.type)
        return offset + l + self.rdlength

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'class': self.rr_class,
            'ttl': self.ttl,
            'rdlength': self.rdlength,
            'rdata': self.rdata
        }

    def from_dict(self, dictionary):
        self.name = dictionary['name']
        self.type = int(dictionary['type'])
        self.rr_class = int(dictionary['class'])
        self.ttl = int(dictionary['ttl'])
        self.rdlength = int(dictionary['rdlength'])
        self.rdata = dictionary['rdata']

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(self, json_str):
        dictionary = json.loads(json_str)
        self.from_dict(dictionary)


class DNSPacket:
    def __init__(self, header=Header(), questions=None,
                 answer_rrs=None, authority_rrs=None, additional_rrs=None):
        self.header = header

        self.questions = questions  # question section

        self.answer_rrs = answer_rrs  # answer resource records
        self.authority_rrs = authority_rrs  # authority resource records
        self.additional_rrs = additional_rrs  # additional resource records

    def to_bytes(self):
        result = b''
        result += self.header.to_bytes()
        for question in self.questions:
            result += question.to_bytes()
        if self.answer_rrs is not None:
            for answer in self.answer_rrs:
                result += answer.to_bytes()
        if self.authority_rrs is not None:
            for auth_rr in self.authority_rrs:
                result += auth_rr.to_bytes()
        if self.additional_rrs is not None:
            for add_rr in self.additional_rrs:
                result += add_rr.to_bytes()
        return result

    def to_dict(self):
        return {
            'header': self.header.to_dict(),
            'question': [question.to_dict() for question in self.questions],
            'answer': [answer.to_dict() for answer in self.answer_rrs if self.answer_rrs is not None],
            'authority': [answer.to_dict() for answer in self.authority_rrs if self.authority_rrs is not None],
            'additional': [answer.to_dict() for answer in self.additional_rrs if self.additional_rrs is not None]
        }

    def from_dict(self, dictionary):
        self.header = Header()
        self.header.from_dict(dictionary['header'])

        self.questions = []
        for question in dictionary['questions']:
            q = Question()
            q.from_dict(question)
            self.questions.append(q)

        self.answer_rrs = []
        for answer in dictionary['answer']:
            rr = ResourceRecord()
            rr.from_dict(answer)
            self.answer_rrs.append(rr)

        self.authority_rrs = []
        for answer in dictionary['authority']:
            rr = ResourceRecord()
            rr.from_dict(answer)
            self.authority_rrs.append(rr)

        self.additional_rrs = []
        for answer in dictionary['additional']:
            rr = ResourceRecord()
            rr.from_dict(answer)
            self.additional_rrs.append(rr)

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(self, json_str):
        dictionary = json.loads(json_str)
        self.from_dict(dictionary)


def read_packet(data):
    header = Header()
    offset = header.from_bytes(data, 0)

    def read_question(data, index):
        question = Question()
        index = question.from_bytes(data, index)
        return question, index

    questions = []
    for _ in range(header.qdcount):
        question, offset = read_question(data, offset)
        questions.append(question)

    def read_rr(data, index):
        answer_rr = ResourceRecord()
        index = answer_rr.from_bytes(data, index)
        return answer_rr, index

    answer, authority, additional = [], [], []
    for _ in range(header.ancount):
        ans, offset = read_rr(data, offset)
        answer.append(ans)
    for _ in range(header.nscount):
        auth, offset = read_rr(data, offset)
        authority.append(auth)
    for _ in range(header.arcount):
        add, offset = read_rr(data, offset)
        additional.append(add)

    dns_packet = DNSPacket(header, questions, answer, authority, additional)
    return dns_packet


def create_response(id, questions, answers):
    header = Header(id=id, qr=1,
                    questions_count=len(questions),
                    ancount=len([answer for answer in answers if answer.rdata != '']))
    response_packet = DNSPacket(header=header,
                                questions=questions,
                                answer_rrs=answers)
    return response_packet
