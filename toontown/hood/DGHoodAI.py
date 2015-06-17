from toontown.classicchars import DistributedDaisyAI
from toontown.hood import HoodAI
from toontown.safezone import ButterflyGlobals
from toontown.safezone import DistributedButterflyAI
from toontown.safezone import DistributedDGFlowerAI
from toontown.safezone import DistributedTrolleyAI
from toontown.toonbase import ToontownGlobals
from toontown.ai import DistributedGreenToonEffectMgrAI


class DGHoodAI(HoodAI.HoodAI):
    def __init__(self, air):
        HoodAI.HoodAI.__init__(self, air,
                               ToontownGlobals.DaisyGardens,
                               ToontownGlobals.DaisyGardens)

        self.trolley = None
        self.flower = None
        self.classicChar = None
        self.butterflies = []

        self.startup()

    def startup(self):
        HoodAI.HoodAI.startup(self)

        if simbase.config.GetBool('want-minigames', True):
            self.createTrolley()
        self.createFlower()
        if simbase.config.GetBool('want-classic-chars', True):
            if simbase.config.GetBool('want-daisy', True):
                self.createClassicChar()
        if simbase.config.GetBool('want-butterflies', True):
            self.createButterflies()

        if simbase.air.holidayManager.isHolidayRunning(ToontownGlobals.IDES_OF_MARCH):
            self.startupGreenToonManager()

    def shutdown(self):
        HoodAI.HoodAI.shutdown(self)

        ButterflyGlobals.clearIndexes(self.zoneId)

    def createTrolley(self):
        self.trolley = DistributedTrolleyAI.DistributedTrolleyAI(self.air)
        self.trolley.generateWithRequired(self.zoneId)
        self.trolley.start()

    def createFlower(self):
        self.flower = DistributedDGFlowerAI.DistributedDGFlowerAI(self.air)
        self.flower.generateWithRequired(self.zoneId)
        self.flower.start()

    def createClassicChar(self):
        self.classicChar = DistributedDaisyAI.DistributedDaisyAI(self.air)
        self.classicChar.generateWithRequired(self.zoneId)
        self.classicChar.start()

    def createButterflies(self):
        playground = ButterflyGlobals.DG
        for area in xrange(ButterflyGlobals.NUM_BUTTERFLY_AREAS[playground]):
            for b in xrange(ButterflyGlobals.NUM_BUTTERFLIES[playground]):
                butterfly = DistributedButterflyAI.DistributedButterflyAI(self.air)
                butterfly.setArea(playground, area)
                butterfly.setState(0, 0, 0, 1, 1)
                butterfly.generateWithRequired(self.zoneId)
                self.butterflies.append(butterfly)

    def startupGreenToonManager(self):
        if hasattr(self, 'GreenToonEffectManager'):
            return
        self.GreenToonEffectManager = DistributedGreenToonEffectMgrAI.DistributedGreenToonEffectMgrAI(self.air)
        self.GreenToonEffectManager.generateWithRequired(5819)

    def stopGreenToonManager(self):
        if hasattr(self, 'GreenToonEffectManager'):
            self.GreenToonEffectManager.requestDelete()
