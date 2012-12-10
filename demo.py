#!/bin/env python3

from EmailTunnel import EmailTunnel
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
      email.alertAdminAboutUser(name, resource, status['warning-code'], a.getLocalWarnText(status['warning-code']))
      if coopMode:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextCooperative(of, status['warning-code'], a.accountHealth()))
      else:
         email.alertUser(name, resource, status['warning-code'], getUserWarningTextIndependent(of, status['warning-code']))

def scenario1():
   d = {
      'billing-frac': 0.2, # One-fifth into the billing cycle.
      'global-quota': 6,   # GB
      'usage': {
         'Philip the Model Citizen': {
            'quota': 2,   # GB
            'used': 1,    # GB
         },
         'John the Hermit': {
            'quota': 2,   # GB
            'used': 0.1,  # GB
         },
         'Yuri the Streamer': {
            'quota': 1,   # GB
            'used': 1.2,  # GB
         },
         'David the Downloader': {
            'quota': 1,   # GB
            'used': 1.1,  # GB
         },
      },
   }

   print("== Scenario 1 ==")
   showDataAlerts(d)

def scenario2():
   d = {
      'billing-frac': 0.8, # Four-fifths into the billing cycle.
      'global-quota': 6,   # GB
      'usage': {
         'Philip the Model Citizen': {
            'quota': 2,   # GB
            'used': 1,    # GB
         },
         'John the Hermit': {
            'quota': 2,   # GB
            'used': 0.1,  # GB
         },
         'Yuri the Streamer': {
            'quota': 1,   # GB
            'used': 1.2,  # GB
         },
         'David the Downloader': {
            'quota': 1,   # GB
            'used': 1.1,  # GB
         },
      },
   }

   print("== Scenario 2 ==")
   showDataAlerts(d)

scenario1()
print("\nTime flows... we're approaching the end of the billing cycle, but data usage doesn't change.\n")
scenario2()
