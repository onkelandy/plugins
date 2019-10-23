import binascii
import hashlib
import hmac
import locale
import time
import requests

from lib.model.smartplugin import *


class Robot:
    def __init__(self, email, password):
        self.logger = logging.getLogger(__name__)
        self.__email = email
        self.__password = password
        self.__urlBeehive = "https://beehive.neatocloud.com"
        self.__urlNucleo = ""
        self.__secretKey = ""

        # Cleaning
        self.category = ''
        self.mode = ''
        self.modifier = ''
        self.navigationMode = ''
        self.spotWidth = ''
        self.spotHeight = ''

        # Meta
        self.name = ""
        self.serial = ""
        self.modelname = ""
        self.firmware = ""

        # Neato Details
        self.isCharging = None
        self.isDocked = None
        self.isScheduleEnabled = None
        self.dockHasBeenSeen = None
        self.chargePercentage = ''
        self.isCleaning = None

        self.state = ''
        self.state_action = ''

        # Neato Available Services
        self.findMe = ''
        self.generalInfo = ''
        self.houseCleaning = ''
        self.IECTest = ''
        self.logCopy = ''
        self.maps = ''
        self.preferences = ''
        self.schedule = ''
        self.softwareUpdate = ''
        self.spotCleaning = ''
        self.wifi = ''

    # Neato Available Commands
    def robot_command(self, command):
        if command == 'start':
            n = self.__cleaning_start_string()
        elif command == 'pause':
            n = '{"reqId": "77","cmd": "pauseCleaning"}'
        elif command == 'resume':
            n = '{"reqId": "77","cmd": "resumeCleaning"}'
        elif command == 'stop':
            n = '{"reqId": "77","cmd": "stopCleaning"}'
        elif command == 'findme':
            n = '{"reqId": "77","cmd": "findMe"}'
        else:
            self.logger.warning("Neato Plugin: Command unknown '{}'".format(command))
            return None
        message = self.serial.lower() + '\n' + self.__get_current_date() + '\n' + n
        h = hmac.new(self.__secretKey.encode('utf-8'), message.encode('utf8'), hashlib.sha256)
        start_cleaning_response = requests.post(
            self.__urlNucleo + "/vendors/neato/robots/" + self.serial + "/messages", data=n,
            headers={'X-Date': self.__get_current_date(), 'X-Agent': 'ios-7|iPhone 4|0.11.3-142',
                     'Date': self.__get_current_date(), 'Accept': 'application/vnd.neato.nucleo.v1',
                     'Authorization': 'NEATOAPP ' + h.hexdigest()}, )
        # todo error handling_
        # - NOT on Charge BASE
        return start_cleaning_response

    def update_robot(self):

        m = '{"reqId":"77","cmd":"getRobotState"}'
        self.__secretKey = self.__get_secret_key()
        message = self.serial.lower() + '\n' + self.__get_current_date() + '\n' + m
        h = hmac.new(self.__secretKey.encode('utf-8'), message.encode('utf8'), hashlib.sha256)
        try:
            robot_cloud_state_response = requests.post(self.__urlNucleo + "/vendors/neato/robots/" + self.serial + "/messages",
                                                    data=m, headers={'X-Date': self.__get_current_date(),
                                                                     'X-Agent': 'ios-7|iPhone 4|0.11.3-142',
                                                                     'Date': self.__get_current_date(),
                                                                     'Accept': 'application/vnd.neato.nucleo.v1',
                                                                     'Authorization': 'NEATOAPP ' + h.hexdigest()}, )
        except:
            self.logger.warning("Neato Plugin: Error during API request unknown '{}'")
            # todo error handling_

        response = robot_cloud_state_response.json()

        # Status
        self.state = str(response['state'])
        self.state_action = str(response['action'])

        # get the Details first
        self.isCharging = response['details']['isCharging']
        self.isDocked = response['details']['isDocked']
        self.isScheduleEnabled = response['details']['isScheduleEnabled']
        self.dockHasBeenSeen = response['details']['dockHasBeenSeen']
        self.chargePercentage = response['details']['charge']

        # get available services for robot second
        self.findMe = response['availableServices']['findMe']
        self.generalInfo = response['availableServices']['generalInfo']
        self.houseCleaning = response['availableServices']['houseCleaning']
        self.IECTest = response['availableServices']['IECTest']
        self.logCopy = response['availableServices']['logCopy']
        self.maps = response['availableServices']['maps']
        self.preferences = response['availableServices']['preferences']
        self.schedule = response['availableServices']['schedule']
        self.softwareUpdate = response['availableServices']['softwareUpdate']
        self.spotCleaning = response['availableServices']['spotCleaning']
        self.wifi = response['availableServices']['wifi']

        # Cleaning Config
        self.category = response['cleaning']['category']
        self.mode = response['cleaning']['mode']
        self.modifier = response['cleaning']['modifier']
        self.navigationMode = response['cleaning']['navigationMode']
        self.spotWidth = response['cleaning']['spotWidth']
        self.spotHeight = response['cleaning']['spotHeight']

        return response

    def __get_access_token(self):
        json_data = {'email': self.__email, 'password': self.__password, 'platform': 'ios',
                     'token': binascii.hexlify(os.urandom(64)).decode('utf8')}
        access_token_response = requests.post(self.__urlBeehive + "/sessions", json=json_data,
                                              headers={'Accept': 'application/vnd.neato.nucleo.v1+json'})
        access_token = access_token_response.json()['access_token']
        return access_token

    def __get_secret_key(self):
        access_token = self.__get_access_token()
        auth_data = {'Authorization': 'Token token=' + access_token}
        secret_key_response = requests.get(self.__urlBeehive + "/users/me/robots", data=auth_data,
                                           headers={'Authorization': 'Bearer ' + access_token})
        secret_key = secret_key_response.json()[0]['secret_key']
        self.serial = secret_key_response.json()[0]['serial']
        self.name = secret_key_response.json()[0]['name']
        self.__urlNucleo = secret_key_response.json()[0]['nucleo_url']
        self.modelname = secret_key_response.json()[0]['model']
        self.firmware = secret_key_response.json()[0]['firmware']
        return secret_key

    def __get_current_date(self):
        saved_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'en_US.utf8')
        except locale.Error as e:
            self.logger.error("Neato Plugin: Locale setting Error. Please install locale en_US.utf8: "+e)
            return None
        date = time.strftime('%a, %d %b %Y %H:%M:%S', time.gmtime()) + ' GMT'
        locale.setlocale(locale.LC_TIME, saved_locale)
        return date

    def __cleaning_start_string(self):
        if self.houseCleaning == 'basic-1':
            return '{"reqId": "77","cmd": "startCleaning","params": {"category": ' + str(
                self.category) + ',"mode": ' + str(self.mode) + ', "modifier": ' + str(self.modifier) + '}}'
        if self.houseCleaning == 'minimal-2':
            return '{"reqId": "77","cmd": "startCleaning","params": {"category": ' + str(
                self.category) + ',"navigationMode": ' + str(self.navigationMode) + '}}'
        if self.houseCleaning == 'minimal-3':
            return '{"reqId": "77","cmd": "startCleaning","params": {"category": ' + str(
                self.category) + ',"navigationMode": ' + str(self.navigationMode) + '}}'
        if self.houseCleaning == 'basic-3':
            return '{"reqId": "77","cmd": "startCleaning","params": {"category": ' + str(
                self.category) + ',"mode": ' + str(self.mode) + ', "navigationMode": ' + str(self.navigationMode) + '}}'
        if self.houseCleaning == 'basic-4':
            return '{"reqId": "77","cmd": "startCleaning","params": {"category": ' + str(
                self.category) + ',"mode": ' + str(self.mode) + ', "navigationMode": ' + str(self.navigationMode) + '}}'
