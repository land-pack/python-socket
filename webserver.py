import socket
import StringIO
import sys

class SocketServer(object):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	request_queue_size = 1
	
	def __init__(self,server_address):
		#: Create a listening socket
		listen_socket = socket.socket(self.address_family,self.socket_type)
		self.listen_socket = listen_socket
		#: Allow to resue the same address
		listen_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		#: Bind
		listen_socket.bind(server_address)
		#: Activate
		listen_socket.listen(self.request_queue_size)
		#: Get server host name and port
		host, port = self.listen_socket.getsockname()[:2]
		self.server_name = socket.getfqdn(host)
		self.server_port = port
	
	def server_forever(self):
		listen_socket = self.listen_socket
		while True:
			#: New client connection
			self.client_connection, client_address = listen_socket.accept()
			#: Handle one request and close the client connection
			#: The loop over to wait for another client connection.
			self.handle_one_request()

	def handle_one_request(self):
		pass

class WSGIServer(SocketServer):
	
	def __init__(self,server_address):
		SocketServer.__init__(self,server_address=server_address)
		self.headers_set = []
	
	def set_app(self,application):
		self.application = application
	
	#: Override the SockerServer method !
	def handle_one_request(self):
		request_data = self.client_connection.recv(1024)
		self.request_data = request_data 
		#: Print formatted request data a la 'curl -v'
		print(''.join(
			'<{line}\n'.format(line=line)
			for line in request_data.splitlines()
		))
		self.parse_request(request_data)
		#: Construct enviroment dictionary using request data
		env = self.get_environ()
		#: It's time to call our application callable and get
		#: back a result that will become HTTP response body
		result = self.application(env, self.start_response)
		#: Construct a response and send it back to the client
		self.finish_response(result)

	def parse_request(self, text):
		request_line = text.splitlines()[0]
		request_line = request_line.rstrip('\r\n')
		#: Break down the request line into components
		(	self.request_method,	#: Get
			self.path,		#: /index
			self.request_version	#: HTTP/1.1
		) = request_line.split()
	
	def get_environ(self):
		env = {}
		#: The following code snippet does not follow PEP8 conventions
		#: but it's formatted the way it if for domonstration purposes
		#: to emphasize the required variables and their values
		#:
		#: Required WSGI variables
		env['wsgi.version'] = (1,0)
		env['wsgi.url_sheme'] = 'http'
		env['wsgi.input'] = StringIO.StringIO(self.request_data)
		env['wsgi.errors'] = sys.stderr
		env['wsgi.multithread'] = False
		env['wsgi.multiprocess'] = False
		env['wsgi.run_once'] = False
		#: Required CGI variable
		env['REQUEST_METHOD'] = self.request_method	#: GET
		env['PATH_INFO'] = self.path			#: /index
		env['SERVER_NAME'] = self.server_name		#: localhost
		env['SERVER_PORT'] = str(self.server_port)	#: 7000
		return env
	
	def start_response(self, status, response_headers, exc_info=None):
		#: Add neccessary server headers
		server_headers = [
			('Date','Tue, 31 Mar 2015 12:54:48 GMT'),
			('Server','WSGIServer 0.2'),
		]
		self.headers_set = [status, response_headers + server_headers]
		#: To adhere to WSGI specification the start_response must return 
		#: a 'write' callable. We simplicity's sake we'll ignore that detail
		#: for now
		#: return self.finish_response

	def finish_response(self, result):
		try:
			status, response_headers = self.headers_set
			response = 'HTTP/1.1 {status}\r\n'.format(status=status)
			for header in response_headers:
				response += '{0}:{1}\r\n'.format(*header)
			response += '\r\n'
			for data in result:
				response += data
			#: Print formatted response data a la 'curl -v'
			print(''.join(
				'>{line}\n'.format(line=line)
				for line in response.splitlines()
			))
			self.client_connection.sendall(response)
		finally:
			self.client_connection.close()


SERVER_ADDRESS = (HOST,PORT) = '',7000

def make_server(server_address, application):
	server = WSGIServer(server_address)
	server.set_app(application)
	return server


class Laskoop(object):
	view_functions = {}
	
	def __init__(self,name,host='127.0.0.1',port=7000):
		self.name=name
		self.host = host
		self.port = port 
		self.server_address = (host,port)
		self.init_views()

	def init_views(self):
		self.view_functions['error_404'] = self.error_404 
		self.view_functions['error_501'] = self.error_501

	def error_404(self):
		return '<h1>Error 404</h1>'	
	
	def error_501(self):
		return '<h1>Error 501</h1>'

	def route(self, rule):
		def _route(function_name):
			self.view_functions[rule] = function_name
			def __route(function_arg):
				function_name(function_arg)
			return __route
		return _route	


	def run(self,debug=True):
		httpd = make_server(self.server_address,self.application)
		print('WSGIServer: Serving HTTP on port {port} ...\n'.format(port=self.port))
		httpd.server_forever()

	def wsgi(self):
		pass

	def application(self,env, start_response):
		start_response('200 OK', [('Content-Type','text/html')])
		path = env['PATH_INFO']
		view_function = self.view_functions.get(path,'no view function register!')
		if isinstance(view_function,str):
			view_function = self.view_functions['error_404']
		response = view_function()
		return [response]



app=Laskoop(__name__)

@app.route('/')
def index():
	return 'Hello,World'

@app.route('/hello')
def hello():
	return '<h1>Hello Frank</h1>'

if __name__ == '__main__':
	app.run(debug=True)
