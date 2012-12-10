#!/bin/env python3

"""SharedUsageAlerter is a module for detecting overuse and underuse of a shared
resource like a family plan with a cell phone company.  The shared resource
may be voice minutes, texts, data, and anything else that has a cap.

The intended workflow is to retrieve per-user and global usage records from the
cell phone company (such as screen-scraping their web site), then to send these
values into the Alerter class.  Alerter will issue warnings which you can then
forward to the user and/or the account administrator.

Modes of operation:
* cooperative: Users will be alerted if another user may cause the account to
               exceed quota.  This is intended for families that don't have
               per-user quotas.
* independent: Users will be alerted only about their own usage.  This is
               intended for accounts shared by relative strangers.  Each
               individual should have a per-user quota specified.

Scenarios detected:
* A user's rate of consumption may exceed account quota by end of billing cycle.
* A user's rate of consumption may exceed that user's individual quota as set
  by the account administrator.
* A user's rate of consumption is estimated to be significantly lower than the
  user's monthly quota.
* A user has gone over his per-user quota.
* An account as a whole has gone over the global quota.

Setup steps per resource (voice minutes, texts, data):
1) Get per-user and global usage records in the form of:
   - global quota: how much the whole family has to share.
   - global used: how much the whole family has used.
   For each user on the shared account:
   - local quota: how much the individual is allowed to use.
   - local used: how much the individual has used.
2) Instantiate Alerter with the usage records.
3) Call accessors to retrieve applicable warnings and other info.  Refer to the
   alerter.py sample program.
4) Forward the warning to the user by email or some other way.
5) Schedule the whole thing to run automatically as often as you please.

The meat of this module is in the functions _getMaxAllowablePctUsedOfMonthlyQuota
and _getMinPctUsedConsideredUnderuse.  They determine the upper and lower bounds
of acceptable (non-warnable) usage.  I determined both of them by plotting on
paper the path of acceptable usage.  Tweak it as needed.  Before tweaking it, I
recommend reading through the scenarios in test-sua.py and adjusting it to suit
your needs.  That'll ensure that your tweaks in this module work as you intend.
"""

class Error(BaseException):
   pass

class Warn:
   # Warnings must all have unique IDs, even across categories.  This is to
   # allow someone to have just one dictionary from warning-code to text.

   class Global:
      """Warnings applicable to the global resource (account cap)."""
      Ok = 0
      Overage = 1
      Overuse = 2
      Underuse = 3

      @staticmethod
      def name(code):
         if code == Warn.Global.Ok:
            return "Ok"
         elif code == Warn.Global.Overage:
            return "Overage"
         elif code == Warn.Global.Overuse:
            return "Overuse"
         elif code == Warn.Global.Underuse:
            return "Underuse"
         else:
            raise Error

   class Local:
      """Warnings applicable to the local resource (individual's cap)."""
      Ok = 10
      # The individual has incurred an overage either on his personal quota (if
      # exists) or on the account as a whole.  Note that the mere fact of the
      # account having incurred an overage is not sufficient to trigger this;
      # we trigger it only if *this* user is responsible for it.  If you want
      # to ask this user to reduce his usage to accommodate someone else, use
      # Global.Overage.
      Overage = 11
      # The individual may exceed his personal quota (if available) or the
      # account quota if this usage pattern keeps up.
      Overuse = 12
      # The individual has an individual quota and is significantly underusing
      # it.  This alert will never trigger if there's no individual quota.
      Underuse = 13

      @staticmethod
      def name(code):
         if code == Warn.Local.Ok:
            return "Ok"
         elif code == Warn.Local.Overage:
            return "Overage"
         elif code == Warn.Local.Overuse:
            return "Overuse"
         elif code == Warn.Local.Underuse:
            return "Underuse"
         else:
            raise Error

class Alerter:
   """This is the primary class of SharedUsageAlerter.  It takes the usage
   information, calculates various interesting things about it, and determines
   any applicable warning."""

   # The Alerter expects its input as a single dictionary formed like this:
   # {
   #   'billing-frac': number,
   #   'global-quota': number or None,
   #   'usage': {
   #              user-name: {
   #                           'quota': number or None,
   #                           'used': number,
   #                         },
   #              ...
   #            }
   # }
   # In the above:
   # * billing-frac is a number ranged [0, 1) indicating the fraction of the
   #   billing cycle that has completed.  The first day of the cycle is 0.
   # * "user-name" is a string that uniquely identifies every user.
   #   I have the user's first name in mind.
   def __init__(self, d):
      self.bf = float(d['billing-frac'])
      self.gq = d['global-quota'] if 'global-quota' in d else None
      self.u = d['usage']
      # Derived
      self.gu = sum(u['used'] for u in self.u.values())

      # If there's at least one individual quota, then verify that the sum of
      # all available individual quotas doesn't exceed the account quota.
      doCheck = True
      indivSum = 0
      for u in self.u.values():
         if 'quota' not in u:
            doCheck = False
            break
         else:
            indivSum += u['quota']
      if doCheck and indivSum > self.gq:
         raise Error("Individual quotas are larger than the nominal account quota")

   # ACCESSORS

   def billingFraction(self):
      """Returns a number ranged [0, 1)."""
      return self.bf

   def usage(self):
      """Returns the original 'usage' element."""
      return self.u

   def globalQuota(self):
      """Returns a number or None."""
      return self.gq

   def globalUsed(self):
      """Returns a number."""
      return self.gu

   def globalUsagePrediction(self):
      return self._eobcUsagePrediction(self.gu)

   # WARNINGS
   def userStatus(self, name):
      def getWarningForOneUser(lq, lu):
         if lq is None:
            # Only the global quota matters.
            if self.gq is None:
               return Warn.Local.Ok
            if lu > self.gq:
               return Warn.Local.Overage
            localUsagePctOfQuota = lu / self.gq
            if localUsagePctOfQuota > self._getMaxAllowablePctUsedOfMonthlyQuota():
               return Warn.Local.Overuse
            # In cooperative mode, we should not alert anyone of underuse.
            # This is because it's possible for everyone to be under global
            # quota yet cause an account overage.
         else:
            # This user has his own quota.
            if lu > lq:
               return Warn.Local.Overage

            if lu == 0 and lq == 0:
               return Warn.Local.Ok

            localUsagePctOfQuota = lu / lq
            if localUsagePctOfQuota > self._getMaxAllowablePctUsedOfMonthlyQuota():
               return Warn.Local.Overuse
            # Underuse alerts will be sent only once the billing cycle is ending.
            if self.bf > 0.7:
               if localUsagePctOfQuota < self._getMinPctUsedConsideredUnderuse():
                  return Warn.Local.Underuse
         return Warn.Local.Ok
      status = {}
      userdata = self.u[name]
      status['used-eobc'] = self._eobcUsagePrediction(userdata['used'])
      status['warning-code'] = getWarningForOneUser(userdata['quota'] if 'quota' in userdata else None, userdata['used'])
      if 'quota' in userdata:
         status['max-daily-use-to-eobc'] = (userdata['quota'] - userdata['used']) / (31*(1 - self.bf))
      return status

   def accountHealth(self):
      """Return a usage warning for the overall account.  The warning is a
      value of Warn.Global enum."""
      if self.gq is None:
         return Warn.Global.Ok

      if self.gu > self.gq:
         return Warn.Global.Overage

      globalUsagePctOfQuota = self.gu / self.gq
      if globalUsagePctOfQuota > self._getMaxAllowablePctUsedOfMonthlyQuota():
         return Warn.Global.Overuse
      # Underuse alerts will be sent only once the billing cycle is ending.
      if self.bf > 0.7:
         if globalUsagePctOfQuota < self._getMinPctUsedConsideredUnderuse():
            return Warn.Global.Underuse
      return Warn.Global.Ok

   @staticmethod
   def getLocalWarnText(code):
      return Warn.Local.name(code)

   @staticmethod
   def getGlobalWarnText(code):
      return Warn.Global.name(code)

   # HELPERS
   def _eobcUsagePrediction(self, usednow):
      return usednow / self.bf

   # An Overuse alert will be issued if the current percent used of the monthly
   # quota is above the percentage returned by this function.
   def _getMaxAllowablePctUsedOfMonthlyQuota(self):
      return self.bf/2 + 0.5

   # An Underuse alert will be issued if the current percent used of the monthly
   # quota is below the percentage returned by this function.  This function can
   # be used only if the user is not already in Overuse mode.
   def _getMinPctUsedConsideredUnderuse(self):
      startFrac = 0.7
      if self.bf < startFrac:
         return 1 # should never trigger
      else:
         def pctChg(x, y):
            return (x-y)/y
         # Range between [50%, 70%].
         return pctChg(1, self.bf) * 0.2 + 0.5

