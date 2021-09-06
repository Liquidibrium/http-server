from datetime import datetime
import magic
import mimetypes
import os
import data
from hashlib import sha256
# encoding problem
class HTTPRequestHandler():
    def __init__(self, client_socket, address):
        self.client_socket = client_socket
        self.client_address = address
        self.timeout = 5  # time to wait for client request
        self.client_socket.settimeout(self.timeout)
        self.keep_conn = True

    def get_content_type(self, path_to_file):
        if self.headers_dict['user-agent'].find('python') != -1:
            mime = magic.Magic(mime=True)
            return mime.from_file(path_to_file)  # for tests
        else:
            content_type, _ = mimetypes.guess_type(path_to_file)
            return content_type  # for browser

    # if no index file found in directory then list it as html
    def ls_dir(self):
        ls = os.listdir(self.full_path)
        html = f"""\
        <html>
        <head>
            <meta http-equiv='Content-Type' content=text/html; charset=UTF-8>
            <title>list dir:{self.path} </title>
        </head>
        <body>
            <ul>
        """.encode()
        for file in ls:
            file_path = os.path.join(self.path, file)
            html += f'<li> <a href={file_path.replace(" ","%20")}>{file_path}</a></li>'.encode(
            )
        html += '</ul>\n</body>\n</html>\n\r\n\r\n'.encode()
        self.content_type = 'text/html'
        self.content_length = len(html)
        return html

    # hash content file for Etag Header
    def etag_hash(self):
        etag = sha256()
        etag.update(self.content)
        self.etag = etag.digest()
        if 'if-none-match' in self.headers_dict:
            old_hash = self.headers_dict['if-none-match']
            if old_hash == self.etag:
                return False
        return True

    def parse_range(self):
        range = self.headers_dict['range']  # get range in bytes
        if len(range) == 0:
            return False

        start_range, end_range = range.split('bytes=')[1].split('-')
        if len(start_range) == 0:
            start_range = 0

        if len(end_range) == 0:
            end_range = self.content_length - 1

        try:
            start_range = int(start_range)
            end_range = int(end_range)
        except:
            return False

        if start_range >= end_range:
            return False
        end_range = min(end_range, self.content_length - 1)
        self.add_header(
            'Content-Range', f'bytes {start_range}-{end_range}/{self.content_length}')
        self.content_length = end_range - start_range + 1
        self.content = self.content[start_range:end_range+1]
        return True

    def parse_path(self):
        if os.path.exists(self.full_path):
            #  cheking for dir
            if os.path.isdir(self.full_path):
                self.content = self.ls_dir()
            else:
                self.content_type = self.get_content_type(self.full_path)
                with open(self.full_path, 'rb') as file:
                    self.content = file.read()
                    file_stats = os.fstat(file.fileno())
                    self.content_length = file_stats[6]
            if not self.etag_hash():
                self.send_error(data.NOT_MODIFIED) # actually this is not error 
                return False
            if 'range' in self.headers_dict:
                if not self.parse_range():
                    self.send_error(data.REQUESTED_RANGE_NOT_SATISFIABLE)
                    return False
                self.status_line(data.PARTIAL_CONTENT)
                return True            
            self.status_line(data.OK)
            return True
        else:
            self.send_error(data.NOT_FOUND)
            return False

    def status_line(self, status):
        self.code = status[0]
        self.response_headers.insert(
            0, f'{data.DEFAULT_HTTP_VERSION} {self.code} {status[1]}\r\n'.encode())

    def add_header(self, key, value):
        self.response_headers.append(f'{key}: {value}\r\n'.encode())

    def end_header(self):
        self.response_headers.append("\r\n".encode())

    def build_HEAD(self):
        self.add_header("server", f'{self.vhost}:{self.port}')
        self.add_header("date", datetime.utcnow().strftime(
            '%a, %d %b %Y %H:%M:%S GMT'))
        self.add_header('etag', self.etag)
        self.add_header('content-length', self.content_length)
        self.add_header('content-type', f'{self.content_type}')
        self.add_header(
            'connection', 'keep-alive' if self.keep_conn else 'close')
        self.add_header('keep-alive', f'timeout={self.timeout}')  # max=1024
        self.add_header('ACCEPT-RANGES', 'bytes')
        self.end_header()

    def build_GET(self):
        self.response_headers.append(self.content)

    def actually_send_response(self):
        msg_to_send = b"".join(self.response_headers)
        self.write_log()
        self.client_socket.sendall(msg_to_send)
        if not self.keep_conn:
            self.client_socket.close()
        return self.keep_conn

    # handle client requests
    # send proper response from server to client
    def send_http_response(self):
        self.build_HEAD()
        if self.method == 'GET':
            self.build_GET()
        elif self.method != 'HEAD':
            self.send_error(data.METHOD_NOT_ALLOWED)
            return False
        self.log_file = self.vhost
        return self.actually_send_response()

    def write_log(self):
        log_str = datetime.now().strftime(
            f"[%a %b %d %H:%M:%S %Y] {self.client_address[0]} {self.vhost} {self.path} {self.code} {self.content_length} {self.headers_dict['user-agent']}\r\n")
        with open(f'{data.LOG_PATH}/{self.log_file}.log', 'a') as log:
            log.write(log_str)

    def send_error(self, status, additional_text=None):
        self.code = status[0]
        self.keep_conn = False
        self.log_file = 'error'
        self.status_line(status)
        self.add_header('connection', 'close')
        self.add_header("date", datetime.utcnow().strftime(
            '%a, %d %b %Y %H:%M:%S GMT'))
        error_text = b''
        self.content_length = 0
        if additional_text != None:
            error_text = additional_text.encode()
            self.content_length = len(error_text)
            self.add_header('content-length', self.content_length)
            self.add_header('content-type', 'text/html')
        self.end_header()
        self.response_headers.append(error_text)
        self.actually_send_response()

    def parse_headers(self, headers):
        list = []
        for header in headers:
            if len(header) == 0:
                break
            list.append(header.lower().split(': '))
        headers_dict = {}
        headers_dict.update(list)
        self.headers_dict = headers_dict

    def get_host_info(self):
        host = self.headers_dict['host'].split(':')
        if len(host) < 2:
            self.vhost = host[0]
            return False
        self.vhost = host[0]
        self.port = host[1]
        if self.vhost in data.servers_dict.keys():
            # check if port is same
            if self.port == str(data.servers_dict[self.vhost]['port']):
                self.full_path = data.servers_dict[self.vhost]['documentroot'] + self.path
                return True
        return False

    # parse client's http message
    def parse_message(self, msg):
        request_line, *headers = msg.split('\r\n')
        request_line_parts = request_line.split()
        if len(request_line_parts) == 0:
            self.send_error(data.BAD_REQUEST)
            return False
        if len(request_line_parts) >= 3:
            version = request_line_parts[2]
            if version.startswith('HTTP/'):
                version_number_strs = version.split('HTTP/', 1)[1].split('.')
                if len(version_number_strs) == 2:
                    version_number = int(
                        version_number_strs[0]) + int(version_number_strs[1])/10
                    if(version_number == 1.1 or version_number == 2.0):
                        self.keep_conn = True  # keep conn true for v1.1 or 2.0
                else:
                    self.send_error(data.BAD_REQUEST)
                    return False
            else:
                self.send_error(data.BAD_REQUEST)
                return False  # no header defined
            self.method, self.path = request_line_parts[0:2]
            self.path = self.path.replace('%20', ' ')
            self.parse_headers(headers)
            if 'connection' in self.headers_dict:
                conn = self.headers_dict['connection']
                if conn == 'close':
                    self.keep_conn = False
                elif conn == 'keep-alive' and version_number >= 1.1:
                    self.keep_conn = True

            if not self.get_host_info():
                self.send_error(
                    data.NOT_FOUND, additional_text='REQUESTED DOMAIN NOT FOUND')
                return False
            return self.parse_path()
        else:
            self.send_error(data.BAD_REQUEST)
            return False

    #  handles clients response
    #  parses message and sends approproate response
    def handle(self, message):
        mkdir(data.LOG_PATH)
        self.response_headers = []
        if self.parse_message(message):
            return self.send_http_response()
        return False


def mkdir(dir_name):
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
