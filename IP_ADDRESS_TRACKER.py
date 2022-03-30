## importing socket module
import socket
from requests import get
from ip2geotools.databases.noncommercial import DbIpCity
## getting the hostname by socket.gethostname() method
def geo_loc():
	hostname = socket.gethostname()## getting the IP address using socket.gethostbyname() method
	ip_address = socket.gethostbyname(hostname)
	## printing the hostname and ip_address
	print(f"Hostname: {hostname}")
	print(f"IP Address: {ip_address}")

	pub_ip = get('https://api.ipify.org').text
	print ('My public IP address is:', pub_ip)

	response = DbIpCity.get(pub_ip, api_key='free')
	re=response.region
	co = response.country
	city = response.city

	return {'country':co, 'region': re, 'city': city, 'public_ip': pub_ip, 'host': hostname}
