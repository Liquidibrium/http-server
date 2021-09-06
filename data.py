import json

DEFAULT_ERROR_CONTENT_TYPE = "text/html;charset=utf-8"
LOG_PATH = "logs"
ENCODING = 'utf-8'
PARALELL_CONN = 1024
CLIENT_MAX_MESSAGE_SIZE = 2048
DEFAULT_HTTP_VERSION = 'HTTP/1.1'

# status codes
# (value, phrase, description)
# ________________________________
OK = (200, 'OK')
PARTIAL_CONTENT = (206, 'Partial Content')
NOT_MODIFIED = (304, 'Not Modified')
BAD_REQUEST = (400,"Bad Request")
NOT_FOUND = (404, 'Not Found')
METHOD_NOT_ALLOWED = (405,'Method Not Allowed')
REQUESTED_RANGE_NOT_SATISFIABLE = (416, 'Requested Range Not Satisfiable')

# read config.json file
def get_config():
    with open("config.json") as file:
        return json.load(file)


servers_dict = {}
# return dict with ip and its unique ports  {ip : {port}} 
def get_unique_addresses():
    config_dict = get_config()
    unique_ip_port_servers = {}
    for server in config_dict['server']:
        servers_dict[server['vhost']] = server
        if server['ip'] in unique_ip_port_servers.keys():
            unique_ip_port_servers[server['ip']].add(server['port'])
        else:
            unique_ip_port_servers[server['ip']] = {server['port']}
    return unique_ip_port_servers
