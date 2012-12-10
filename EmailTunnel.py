from SharedUsageAlerter import Warn

"""EmailTunnel is a module for sending email notifications to users who cause
a usage alert.  Its main purpose is to eliminate duplicate notifications.  The
software is designed to run periodically (daily), and we don't want to spam the
user or the account administrator with the same notification every time.
Instead we prefer to generate an email only when something changes.  That's what
this module does."""
class EmailTunnel:
   def __init__(self):
      self.useralerts = {}
      self.aaau = {} # admin alerts about user
      self.adminalert = None
      pass

   def alertUser(self, line, resource, wCode, wText):
      if line not in self.useralerts:
         self.useralerts[line] = {}
      if resource in self.useralerts[line]:
         if self.useralerts[line][resource] == wCode:
            pass  # This warning has already been issued
         elif wCode == Warn.Local.Ok:
            # Warning is cleared.
            del self.useralerts[line][resource]
         else:
            # Issue the warning.
            print("EMAIL: Warning to %s about %s: %s" % (line, resource, wText))
      else:
         if wCode != Warn.Local.Ok:
            # Issue the warning and store it.
            self.useralerts[line][resource] = wCode
            print("EMAIL: Warning to %s about %s: %s" % (line, resource, wText))

   def alertAdminAboutUser(self, line, resource, wCode, wText):
      if line not in self.aaau:
         self.aaau[line] = {}
      if resource in self.aaau[line]:
         if self.aaau[line] == wCode:
            pass  # This warning has already been issued
         elif wCode == Warn.Local.Ok:
            # Warning is cleared.
            del self.aaau[line][resource]
         else:
            # Issue the warning.
            print("EMAIL: Warning to admin about %s (%s): %s" % (line, resource, wText))
      else:
         if wCode != Warn.Local.Ok:
            # Issue the warning and store it.
            self.aaau[line][resource] = wCode
            print("EMAIL: Warning to admin about %s (%s): %s" % (line, resource, wText))

   def alertAdminGlobally(self, resource, wCode, wText):
      if wCode == None:
         self.adminalert = wCode
      elif wCode == Warn.Global.Ok:
         self.adminalert = None
      elif wCode != self.adminalert:
         # Issue the warning.
         print("EMAIL: Global %s warning to admin: %s" % (resource, wText))
 
