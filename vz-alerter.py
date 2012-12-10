#!/bin/env python3

import calendar
import datetime
import os
import pickle
import pprint
from EmailTunnel import EmailTunnel
from VerizonScraper import VerizonScraper
from SharedUsageAlerter import Warn, Alerter
from OutputFormatter import OutputFormatter

def getUserWarningTextCooperative(of, usercode, admincode=Warn.Global.Ok):
   if admincode == Warn.Global.Overage or admincode == Warn.Global.Overuse:
      return of.warningAdminTextMap[admincode]
   return of.warningUserTextMap[usercode]

def getUserWarningTextIndependent(of, usercode):
   return of.warningUserTextMap[usercode]

def showDataAlerts(d):
   resource = "data"
   coopMode = False
   of = OutputFormatter(resource)
   a = Alerter(d)
   email = EmailTunnel()
   # EOBC: End Of Billing Cycle
   print("== DATA ALERTS ==")
   globalWarning = a.getGlobalWarnText(a.accountHealth())
   print("Global status (%.1f / %.1f GB) is %s.  Estimated usage by EOBC: %.1f GB."
      % (a.globalUsed(), a.globalQuota(), globalWarning, a.globalUsagePrediction()))
   print("Message to admin: %s" % of.warningAdminTextMap[a.accountHealth()])
   email.alertAdminGlobally(resource, a.accountHealth(), globalWarning)

   for (name, usage) in d['usage'].items():
      status = a.userStatus(name)
      localquota = usage['quota'] if 'quota' in usage else "inf"
      print("%s (used %.1f / %.1f GB):" % (name, usage['used'], localquota))
      print("\tto account admin: %s.  Est. local use by EOBC: %.1f / %.1f GB."
         % (a.getLocalWarnText(status['warning-code']), status['used-eobc'], localquota))
      if 'max-daily-use-to-eobc' in status and status['max-daily-use-to-eobc'] > 0:
         print("\tto user: you can use up to %.2f GB/day until the end of the billing cycle." % status['max-daily-use-to-eobc'])
      print("\tto user (coop mode): %s" % getUserWarningTextCooperative(of, status['warning-code'], a.accountHealth()))
      print("\tto user (ind mode):  %s" % getUserWarningTextIndependent(of, status['warning-code']))
      if coopMode:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextCooperative(of, status['warning-code'], a.accountHealth()))
      else:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextIndependent(of, status['warning-code']))

def showSmsAlerts(d):
   resource = "SMS"
   coopMode = False
   of = OutputFormatter(resource)
   a = Alerter(d)
   email = EmailTunnel()
   # EOBC: End Of Billing Cycle
   print("== SMS ALERTS ==")
   globalWarning = a.getGlobalWarnText(a.accountHealth())
   print("Global status (%d / %s) is %s.  Estimated usage by EOBC: %d."
      % (a.globalUsed(), a.globalQuota() if a.globalQuota() is not None else "inf", globalWarning, a.globalUsagePrediction()))
   print("Message to admin: %s" % of.warningAdminTextMap[a.accountHealth()])
   email.alertAdminGlobally(resource, a.accountHealth(), globalWarning)

   for (name, usage) in d['usage'].items():
      status = a.userStatus(name)
      localquota = usage['quota'] if 'quota' in usage else "inf"
      print("%s (used %d / %s):" % (name, usage['used'], localquota))
      print("\tto account admin: %s.  Est. local use by EOBC: %d / %s."
         % (a.getLocalWarnText(status['warning-code']), status['used-eobc'], localquota))
      if 'max-daily-use-to-eobc' in status and status['max-daily-use-to-eobc'] > 0:
         print("\tto user: you can send up to %.1f texts/day until the end of the billing cycle." % status['max-daily-use-to-eobc'])
      print("\tto user (coop mode): %s" % getUserWarningTextCooperative(of, status['warning-code'], a.accountHealth()))
      print("\tto user (ind mode):  %s" % getUserWarningTextIndependent(of, status['warning-code']))
      if coopMode:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextCooperative(of, status['warning-code'], a.accountHealth()))
      else:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextIndependent(of, status['warning-code']))

def getAuth():
   db = {}
   with open('auth.dat', 'r') as f:
      for l in f:
         s = l.strip().split('=')
         db[s[0]] = s[1]
   return db

def KbToGb(kb):
   return kb / 1024 / 1024

def run():
   if os.access('vz.pickle', os.R_OK):
      print("Loading the pickled Verizon Wireless account info.")
      with open('vz.pickle', 'rb') as f:
         vz = pickle.load(f)
   else:
      auth = getAuth()
      print("Retrieving Verizon Wireless account info of '%s'..." % auth['username'])
      vz = VerizonScraper(auth['username'], auth['password'])
      with open('vz.pickle', 'wb') as f:
         pickle.dump(vz, f, pickle.HIGHEST_PROTOCOL)

   pp = pprint.PrettyPrinter(indent=2)
   accountInfo = vz.getAccountInfo()
   #pp.pprint(accountInfo)
   somePhone = iter(vz.getPhoneNumSet()).__next__()
   if len(accountInfo.keys()) == 0:
      sys.stderr.write("Did not find any phone numbers or any account information!\n")
      sys.exit(1)
   (_, daysInMonth) = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)

   d = {
      'billing-frac': 1 - ((accountInfo[somePhone]['sms']['billCyleEndDate'] - datetime.date.today()).days / daysInMonth),
      'usage': {}
   }

   print("You are %.0f%% of the way into the billing cycle." % (d['billing-frac']*100))
   # SMS
   d['global-quota'] = 0
   isInfinite = False
   for (phone, lineInfo) in accountInfo.items():
      d['usage'][phone] = {
         'used': lineInfo['sms']['individualUsage'],
      }
      if lineInfo['sms']['summaryAllowance'] == 'Unlimited':
         isInfinite = True
      else:
         d['usage'][phone]['quota'] = lineInfo['sms']['summaryAllowance']
         d['global-quota'] += lineInfo['sms']['summaryAllowance']
   if isInfinite: 
      d['global-quota'] = None
   showSmsAlerts(d)

   # Data
   d['global-quota'] = 0
   for (phone, lineInfo) in accountInfo.items():
      d['usage'][phone] = {
         'quota': KbToGb(lineInfo['data']['summaryAllowanceInKB']),
         'used': KbToGb(lineInfo['data']['summaryUsageInKB']),
      }
      d['global-quota'] += KbToGb(lineInfo['data']['summaryAllowanceInKB'])
   showDataAlerts(d)

run()
