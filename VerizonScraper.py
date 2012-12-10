#!/bin/env python3

import datetime
import http.client
import re
import urllib.request
import xml.etree.ElementTree as ET

# Thanks, http://stackoverflow.com/questions/603856/how-do-you-get-default-headers-in-a-urllib2-request
class PrintedHTTPConnection(http.client.HTTPConnection):
	def send(self, s):
		print("PrintedHTTPConnection: %s" % s)
		http.client.HTTPConnection.send(self, s)

class PrintedHTTPSConnection(http.client.HTTPSConnection):
	def send(self, s):
		print("PrintedHTTPSConnection: %s" % s)
		http.client.HTTPSConnection.send(self, s)

class PrintedHTTPHandler(urllib.request.HTTPHandler):
	def http_open(self, req):
		return self.do_open(PrintedHTTPConnection, req)

class PrintedHTTPSHandler(urllib.request.HTTPSHandler):
	def https_open(self, req):
		return self.do_open(PrintedHTTPSConnection, req)

"""VerizonScraper is a module that retrieves account information from Verizon's
web interface.  Verizon does not provide a convenient API for retrieving usage
info, so this tool simulates a user going through the browser.

To use this module, you need your My Verizon credentials.  Once the object
exists, you can call getPhoneNumSet() and getAccountInfo()."""
class VerizonScraper:
   def __init__(self, username, password):
      self._initUrllib()
      self._getInitialCj()
      self.phoneNumSet = self._doLogin(username, password)

      self.accountInfo = {}
      for phoneNum in self.phoneNumSet:
         lineInfo = {'data': None, 'sms': None}
         lineInfo['data'] = self._getDataOverview(phoneNum)
         lineInfo['sms'] = self._getSmsOverview(phoneNum)
         self.accountInfo[phoneNum] = lineInfo

   """This returns the set of phone numbers associated with the account.  The
   phone numbers are formatted as strings of pure digits."""
   def getPhoneNumSet(self):
      return self.phoneNumSet

   """This returns per-line usage info.  It's formed like this:
   ['phonenum': {
      'sms': {
         usage data provided by Verizon and partially fixed-up
      },
      'data': {
         usage data provided by Verizon and partially fixed-up
      },
    ...more phone numbers...
   ]"""
   def getAccountInfo(self):
      return self.accountInfo

   def _initUrllib(self):
      cj = urllib.request.HTTPCookieProcessor()
      #opener = urllib.request.build_opener(cj, PrintedHTTPHandler(), PrintedHTTPSHandler())
      opener = urllib.request.build_opener(cj)
      opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0) Gecko/20121026 Firefox/16.0')]
      urllib.request.install_opener(opener)

   def _getInitialCj(self):
      r = urllib.request.urlopen('http://www.verizonwireless.com/b2c/index.html')

   # The login function's responsibility is to log in to Verizon Wireless and
   # retrieve phone numbers associated with this account.
   def _doLogin(self, usernm, passwd):
      logindata = urllib.parse.urlencode({
         'realm': 'vzw',
         'goto': '',
         'gx_charset': 'UTF-8',
         'rememberUserNameCheckBoxExists': 'Y',
         'login_select': '1',
         'IDToken1': usernm,
         'IDToken2': passwd,
         'rememberUserName': 'Y',
         'signIntoMyVerizonButton': '',
      }).encode('utf-8')
      req = urllib.request.Request('https://login.verizonwireless.com:443/amserver/UI/Login', logindata)
      req.add_header('Referer', 'https://login.vzw.com/cdsso/public/controller?action=logout')
      r = urllib.request.urlopen(req)

      # The layout of the webpage is a bit different depending on whether there's
      # just one line or multiple lines associated with the account.  Fortunately
      # we can always search through the webpage both ways end end up with the
      # correct result.
      phoneNumRegex = re.compile('^	SELECTED_MTN :\'(\d{10})\',')
      multiPhoneRegex = re.compile('^    <option value="(\d{3}-\d{3}-\d{4})">')
      phoneNums = []
      #f = open('verizon-login.html', 'w')
      phoneNum = None
      for line in self._decodeToUtf8(r):
         #f.write(line)
         moSingle = phoneNumRegex.match(line)
         moMulti = multiPhoneRegex.match(line)
         if moSingle:
            num = moSingle.group(1)
            phoneNums.append(num)
         if moMulti:
            num = moMulti.group(1).replace('-', '')
            phoneNums.append(num)
      #f.close()
      #for c in cj.cookiejar:
      #	if c.name == 'JSESSIONID':	
      #		sid = c.value
      #		print("Session ID: %s" % c.value)

      #print("Login response HEADERS:")
      #print(r.info())
      return set(phoneNums)

   def _decodeToUtf8(self, lines):
      for l in lines:
         yield l.decode('utf-8')

   def _getSmsOverview(self, phoneNum):
      reqData = urllib.parse.urlencode({
         'activeMtn': phoneNum,
      }).encode('utf-8')
      req = urllib.request.Request('https://nbillpay.verizonwireless.com/vzw/secure/overview/OverviewMessaging.action', reqData)
      req.add_header('Referer', 'https://nbillpay.verizonwireless.com/vzw/secure/router.action')
      r = urllib.request.urlopen(req)
      xmlstring = ''.join(self._decodeToUtf8(r.readlines()))
      root = ET.fromstring(xmlstring)
      dataDict = {}
      for child in root:
         (k, v) = self._fixupSmsEntry(child.tag, child.text)
         dataDict[k] = v
      return dataDict

   def _getDataOverview(self, phoneNum):
      reqData = urllib.parse.urlencode({
         'activeMtn': phoneNum,
         'connectHotspotCall': 'false',
      }).encode('utf-8')
      req = urllib.request.Request('https://nbillpay.verizonwireless.com/vzw/secure/overview/OverviewData.action', reqData)
      req.add_header('Referer', 'https://nbillpay.verizonwireless.com/vzw/secure/router.action')
      r = urllib.request.urlopen(req)
      xmlstring = ''.join(self._decodeToUtf8(r.readlines()))
      root = ET.fromstring(xmlstring)
      dataDict = {}
      for child in root:
         (k, v) = self._fixupDataEntry(child.tag, child.text)
         dataDict[k] = v
      return dataDict

   def _fixupSmsEntry(self, k, v):
      # integers
      if k == 'summaryAllowance':
         if v != 'Unlimited':
            v = int(self._fixupPrettyFloatStr(v))  # convert to float first because some logical integers end with ".0".
      else:
         return self._fixupGenericEntry(k, v)
      return (k, v)

   def _fixupDataEntry(self, k, v):
      return self._fixupGenericEntry(k, v)

   def _fixupGenericEntry(self, k, v):
      if k == 'billCyleEndDate': # lol, Cyle. I spent 10 mins figuring out why this field isn't getting fixed up.
         v = datetime.datetime.strptime(v, "%m/%d/%y").date()
      # floats
      elif k == 'summaryAllowanceInKB' or k == 'summaryUsageInKB':
         v = self._fixupPrettyFloatStr(v)
      # integers
      elif k == 'summaryUsage' or k == 'individualUsage':
         v = int(self._fixupPrettyFloatStr(v))  # convert to float first because some logical integers end with ".0".
      return (k, v)

   def _fixupPrettyFloatStr(self, n):
      return float(n.replace(',', ''))

