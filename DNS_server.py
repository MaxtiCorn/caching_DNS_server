import socket
from DNS_packet import read_packet, DNSPacket, Header, create_response, ResourceRecord
from cacher import Cache


class Server:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        cache = Cache()
        cache.load()
        self.socket.bind(('127.0.0.2', 53))
        while True:
            data, addr = self.socket.recvfrom(512)
            request = read_packet(data)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
                cache.clear()
                answers = []
                authority = []
                additional = []
                for question in request.questions:
                    cached_rr = cache.find(question.qname, question.qtype, question.qclass)
                    if cached_rr is None:
                        header = Header(questions_count=1, rd=1)
                        dns_request = DNSPacket(header, [question])
                        try:
                            server_socket.sendto(dns_request.to_bytes(), ('ns1.e1.ru', 53))
                            answer = server_socket.recvfrom(512)[0]
                            dns_answer = read_packet(answer)
                            answers.extend(dns_answer.answer_rrs)
                            authority.extend(dns_answer.authority_rrs)
                            additional.extend(dns_answer.additional_rrs)
                            for answer in answers:
                                cache.add(answer)
                            for answer in authority:
                                cache.add(answer)
                            for answer in additional:
                                cache.add(answer)
                        except:
                            pass
                    else:
                        for answer in cached_rr:
                            answers.append(answer)
                my_answer = create_response(request.header.id, request.questions, answers)
                self.socket.sendto(my_answer.to_bytes(), addr)
                cache.save()


if __name__ == '__main__':
    server = Server()
    server.start()
