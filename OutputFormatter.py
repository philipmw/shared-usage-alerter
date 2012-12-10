from SharedUsageAlerter import Warn

class OutputFormatter:
   def __init__(self, resource):
      self.resourceForms = {
         'voice'  : {
                      'infinitive': 'to call',
                      'gerund': 'calling',
                    },
         'SMS'    : {
                      'infinitive': 'to text',
                      'gerund': 'texting',
                    },
         'data'   : {
                      'infinitive': 'to use data',
                      'gerund': 'using data',
                    },
      }

      self.warningAdminTextMap = {
         Warn.Global.Overage  : "An account overage for %s has occurred!" % resource,
         Warn.Global.Overuse  : "An account overage for %s is predicted.  Be careful." % resource,
         Warn.Global.Underuse : "An underuse for %s is predicted.  Rock on." % resource,
         Warn.Global.Ok       : "All is ok for %s." % resource,
      }

      self.warningUserTextMap = {
         Warn.Local.Overage      : "Please stop %s; you're over your %s quota!" % (self.resourceForms[resource]['gerund'], resource),
         Warn.Local.Overuse      : "If you keep %s at your rate, you may exceed the quota." % (self.resourceForms[resource]['gerund']),
         Warn.Local.Underuse     : "You're way under your %s quota. Feel free %s more.  Use it or lose it." % (resource, self.resourceForms[resource]['infinitive']),
         Warn.Local.Ok           : "All is ok.",
      }
