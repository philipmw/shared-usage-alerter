#!/bin/env python3

import unittest
from SharedUsageAlerter import Warn, Alerter, Error as SuaError

"""This is a unit-testing module for SharedUsageAlerter.  If you ever tweak
SharedUsageAlerter, be sure to rerun this."""

class TestSequenceFunctions(unittest.TestCase):
   def test_init_01(self):
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
      a = Alerter(d)
      self.assertEqual(d['billing-frac'], a.billingFraction())
      self.assertEqual(d['usage'], a.usage())
      self.assertEqual(d['global-quota'], a.globalQuota())
      self.assertEqual(sum(u['used'] for u in d['usage'].values()), a.globalUsed())

   def test_init_02(self):
      d = {
         'billing-frac': 0.8, # Four-fifths into the billing cycle.
         'global-quota': 1,   # GB
         'usage': {
            'Philip the Model Citizen': {
               'quota': 2,   # GB
               'used': 1,    # GB
            },
         },
      }
      with self.assertRaises(SuaError):
         a = Alerter(d)

   def test_init_nousers(self):
      d = {
         'billing-frac': 0.5,
         'global-quota': 1,
         'usage': {
         },
      }
      a = Alerter(d)
      self.assertEqual(d['usage'], a.usage())
      self.assertEqual(d['global-quota'], a.globalQuota())
      self.assertEqual(0, a.globalUsed())

   # On the first day, Yuri the Streamer uses 50% of his quota.  That's ok.
   def test_yuri_01(self):
      d = {
         'billing-frac': 1.0/30,
         'global-quota': 6,   # GB
         'usage': {
            'Yuri the Streamer': {
               'quota': 1,   # GB
               'used': 0.5,  # GB
            },
         },
      }
      a = Alerter(d)
      self.assertEqual(a.accountHealth(), Warn.Global.Ok)
      self.assertEqual(a.userStatus('Yuri the Streamer')['warning-code'], Warn.Local.Ok)

   # A user is underusing his quota, but it's not time yet to notify him.
   def test_john_01(self):
      d = {
         'billing-frac': 0.2, # One-fifth into the billing cycle.
         'global-quota': 6,   # GB
         'usage': {
            'John the Hermit': {
               'quota': 2,   # GB
               'used': 0.1,  # GB
            },
         },
      }
      a = Alerter(d)
      self.assertEqual(a.userStatus('John the Hermit')['warning-code'], Warn.Local.Ok)

   # John gets closer to the end of the billing cycle.
   # In response to the email, John's the usage spikes.
   def test_john_02(self):
      d = {
         'billing-frac': 0.8, # Four-fifths into the billing cycle.
         'global-quota': 6,   # GB
         'usage': {
            'John the Hermit': {
               'quota': 2,   # GB
               'used': 0.1,  # GB
            },
         },
      }
      a = Alerter(d)
      self.assertEqual(a.accountHealth(), Warn.Global.Underuse)
      self.assertEqual(a.userStatus('John the Hermit')['warning-code'], Warn.Local.Underuse)

   # John is doing fine, but someone else uses too much data!  That's ok,
   # don't alarm the user.
   def test_john_03(self):
      d = {
         'billing-frac': 0.8, # Four-fifths into the billing cycle.
         'global-quota': 6,   # GB
         'usage': {
            'John the Hermit': {
               'quota': 2,   # GB
               'used': 0.1,  # GB
            },
            'David the Downloader': {
               'quota': 4,   # GB
               'used': 7.1,  # GB
            },
         },
      }
      a = Alerter(d)
      self.assertEqual(a.accountHealth(), Warn.Global.Overage)
      self.assertEqual(a.userStatus('John the Hermit')['warning-code'], Warn.Local.Underuse)

   # In the last few days of the billing cycle, John heeds the emails and uses
   # much more data.
   def test_john_04(self):
      d = {
         'billing-frac': 0.85,
         'global-quota': 6,   # GB
         'usage': {
            'John the Hermit': {
               'quota': 2,   # GB
               'used': 1.9,  # GB
            },
         },
      }
      a = Alerter(d)
      self.assertEqual(a.accountHealth(), Warn.Global.Underuse)
      self.assertEqual(a.userStatus('John the Hermit')['warning-code'], Warn.Local.Overuse)

unittest.main()
