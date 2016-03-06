import pygame
import os
import socket
import json
import requests
import requests.exceptions
import logging
from time import sleep
import subprocess

_max_retries = 5
_req_timeout = 5 

def run_cmd(cmd):
   p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
   output = p.communicate()[0]
   return output

	# NOTE: this method will retry according to self._max_retries, so failure will take a little while
	# On start (first req), we may want the failure sooner, but this is a daemon, so we aren't worried about it	
def _getJsonWithRetry(url,token):
	"""Private method to wrap getting json data with retries. Only gets single page, nothing fancy. See getJson
	:param url: url to get
	:return: json data returned from server
	"""
	retry_count = 0
	req = None
	headers = {'Content-type': 'application/json'}
	
	while retry_count < _max_retries:
		try:
			#val = 'Token ' + self._token
			haders = {'Authorization': 'Token ' + token} 
			req = requests.get(url, timeout=_req_timeout, headers=headers)
			if req.status_code == requests.codes.ok:
				break
			logging.warning('Failed to get %s, status %d, retry %d' % (url, req.status_code, retry_count))
		except requests.exceptions.RequestException as e:
			logging.warning('Failed to get request for %s, RequestException: %s' % (url, e))
			pass        # Just pass it, we will include it as a retry ahead
		finally:
			retry_count += 1

			if retry_count >= _max_retries:
				logging.error("Exceeded max connection retries for %s" % url)
				if req is not None:
					logging.error("Request failure reason: %s" % req.reason)
					raise ConnectionError(req.reason)
				else:
					logging.error("No request, no reason!")
					raise ConnectionError
	return req.json()

        
def main(): 
	os.environ["SDL_FBDEV"] = "/dev/fb1"
	os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
	os.environ["SDL_MOUSEDRV"] = "TSLIB"	
	logging.warning('RPI_UI')
	
	cmd = "ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1"
	
	#Colours
	WHITE = (255,255,255)
	BLACK = (0,0,0)	
	WIDTH = 480
	XCENTER = WIDTH / 2
	HEIGHT = 320
	BIGFONTSIZE = 40
	SMALLFONTSIZE = 30
	LINESPACE = ((HEIGHT / SMALLFONTSIZE)) + 7
	COL1 = SMALLFONTSIZE
	COL2 = XCENTER + SMALLFONTSIZE
	pygame.init()
	pygame.mouse.set_visible(False)
	 
	lcd = pygame.display.set_mode((WIDTH, HEIGHT),pygame.NOFRAME | pygame.FULLSCREEN )
	lcd.fill((161,212,83))
	pygame.display.update()
	f = open(os.path.join('/home/pi/', 'server_ip.txt'), 'r')
	server_ip = f.readline();
	logging.warning('IP %s',server_ip)
	f.close()
	base_url = "http://" + server_ip.strip() + "/"
	_post_datapoint_url = base_url + 'dataPoint/'        
	
	# Authorization
	data = { 'username':'plantos', 'password':'plantos' }
	data_string = json.dumps(data)
	headers = {'Content-type': 'application/json'}
	req = requests.post(base_url+"auth/login/", params={"many": True}, data=data_string, headers=headers)
	if req.status_code != 200:
		logging.warning('Failed to post %s: Code %d', data_string, req.status_code) 
	else:
		logging.warning('Key Aquired')
	token = req.json()['key']

	# Get Urls       
	_urls_dictby_name = _getJsonWithRetry(base_url,token)
	_cache_dictby_url = {}
	_thread_list = []

	font_big = pygame.font.Font(None, BIGFONTSIZE)
	font_small = pygame.font.Font(None, SMALLFONTSIZE)

	while True:
		
		row = 4;
		sensor_list = ["Window","11","CO2","8","Hum","7","Air Temp","6","Light Int","3","PAR","2","Water Temp","5","EC","4","Ph","1"]
			
		#title
		text_surface = font_big.render("OpenAg Food Computer", True, BLACK)
		rect = text_surface.get_rect(center=(XCENTER,LINESPACE*1))
		lcd.blit(text_surface, rect)

		#ip address
		ipaddr = run_cmd(cmd)
		totalip = "IP: " + ipaddr.decode("utf-8")
		text_surface = font_small.render(totalip, True, BLACK)
		rect = text_surface.get_rect(center=(XCENTER,LINESPACE*row))
		lcd.blit(text_surface, rect)
		row += 1
		
		#run through the list of sensors
		for x in range(0, 9):
			_dict = _getJsonWithRetry(base_url+"/sensingPoint/"+ sensor_list.pop()+"/value/",token)
			temp = sensor_list.pop() + ": " + str(_dict['value'])
			text_surface = font_small.render(temp, True, BLACK)
			rect = text_surface.get_rect(center=(XCENTER,LINESPACE*row))
			lcd.blit(text_surface, rect)
			row += 1

		pygame.display.update()
	
		sleep(30.0)
		lcd.fill((161,212,83))

if __name__ == '__main__': main()
