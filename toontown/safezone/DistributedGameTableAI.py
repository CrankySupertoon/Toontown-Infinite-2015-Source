from direct.distributed.DistributedNodeAI import DistributedNodeAI

from direct.distributed.ClockDelta import *

from toontown.safezone import DistributedChineseCheckersAI

from toontown.safezone import DistributedCheckersAI
from toontown.safezone import DistributedFindFourAI


class DistributedGameTableAI(DistributedNodeAI):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedGameTableAI')

    def __init__(self, air, zone, name, x, y, z, h, p, r):
        DistributedNodeAI.__init__(self, air)
        self.posHpr = (x, y, z, h, p, r)
        self.name = name
        self.zoneId = zone
        self.air = air
        self.seats = [None, None, None, None, None, None]
        self.playersSitting = 0
        self.playerIdList = []
        self.checkersZoneId = None
        self.observers = []
        self.allowPickers = []
        self.hasPicked = False
        self.game = None
        self.gameDoId = None
        self.isAccepting = True

    def setPosHpr(self, x, y, z, h, p, r):
        self.posHpr = (x, y, z, h, p, r)

    def getPosHpr(self):
        return self.posHpr

    def announceGenerate(self):
        pass

    def start(self):
        self.handleGameOver()

    def delete(self):
        DistributedNodeAI.delete(self)
        self.game = None
        self.gameDoId = None

    def setGameDoId(self, doId):
        self.gameDoId = doId
        self.game = self.air.doId2do.get(doId)

    def requestTableState(self):
        avId = self.air.getAvatarIdFromSender()
        self.getTableState()

    def getTableState(self):
        tableStateList = []
        for x in self.seats:
            if x == None:
                tableStateList.append(0)
                continue
            tableStateList.append(x)

        if self.game and self.game.fsm.getCurrentState().getName() == 'playing':
            self.sendUpdate('setTableState', [tableStateList, 1])
        else:
            self.sendUpdate('setTableState', [tableStateList, 0])

    def sendIsPlaying(self):
        if self.game.fsm.getCurrentState().getName() == 'playing':
            self.sendUpdate('setIsPlaying', [1])
        else:
            self.sendUpdate('setIsPlaying', [0])

    def announceWinner(self, gameName, avId):
        self.sendUpdate('announceWinner', [gameName, avId])
        self.gameDoId = None
        self.game = None

    def requestJoin(self, si):
        avId = self.air.getAvatarIdFromSender()
        if self.findAvatar(avId) != None:
            self.notify.warning('Ignoring multiple requests from %s to board.' % avId)
            return None

        av = self.air.doId2do.get(avId)
        if av:
            if av.hp > 0 and self.isAccepting and self.seats[si] == None:
                self.notify.debug('accepting boarder %d' % avId)
                self.acceptBoarder(avId, si)
            else:
                self.notify.debug('rejecting boarder %d' % avId)
                self.sendUpdateToAvatarId(avId, 'rejectJoin', [])
        else:
            self.notify.warning('avid: %s does not exist, but tried to board a picnicTable' % avId)

    def acceptBoarder(self, avId, seatIndex):
        self.notify.debug('acceptBoarder %d' % avId)
        if self.findAvatar(avId) != None:
            return None

        isEmpty = False
        if self.findAvailableSeat() != -1:
            isEmpty = True

        if isEmpty == True or self.hasPicked == False:
            self.sendUpdateToAvatarId(avId, 'allowPick', [])
            self.allowPickers.append(avId)

        if self.hasPicked == True:
            self.sendUpdateToAvatarId(avId, 'setZone', [self.game.zoneId])

        self.seats[seatIndex] = avId
        self.acceptOnce(self.air.getAvatarExitEvent(avId), self._DistributedGameTableAI__handleUnexpectedExit,
                        extraArgs=[avId])
        self.timeOfBoarding = globalClock.getRealTime()
        if self.game:
            self.game.informGameOfPlayer()

        self.sendUpdate('fillSlot', [avId, seatIndex,
                                     globalClockDelta.localToNetworkTime(self.timeOfBoarding), self.doId])
        self.getTableState()

    def requestPickedGame(self, gameNum):
        avId = self.air.getAvatarIdFromSender()
        if self.hasPicked == False and avId in self.allowPickers:
            numPickers = len(self.allowPickers)
            self.allowPickers = []
            self.pickGame(gameNum)
            if self.game:
                self.hasPicked = True
                for x in xrange(numPickers):
                    self.game.informGameOfPlayer()

    def pickGame(self, gameNum):
        if self.game:
            return

        activePlayers = self.countFullSeats()

        if gameNum == 1:
            if simbase.config.GetBool('want-chinese', 1):
                self.game = DistributedChineseCheckersAI.DistributedChineseCheckersAI(self.air, self.doId, 'chinese',
                                                                                      self.posHpr[0], self.posHpr[1],
                                                                                      self.posHpr[2] + 2.8300000000000001,
                                                                                      self.posHpr[3], self.posHpr[4],
                                                                                      self.posHpr[5])
                self.sendUpdate('setZone', [self.game.zoneId])

        elif gameNum == 2:
            if activePlayers <= 2:
                if simbase.config.GetBool('want-checkers', 1):
                    self.game = DistributedCheckersAI.DistributedCheckersAI(self.air, self.doId, 'checkers',
                                                                            self.posHpr[0], self.posHpr[1],
                                                                            self.posHpr[2] + 2.8300000000000001,
                                                                            self.posHpr[3], self.posHpr[4],
                                                                            self.posHpr[5])
                    self.sendUpdate('setZone', [self.game.zoneId])

        elif activePlayers <= 2:
            if simbase.config.GetBool('want-findfour', 1):
                self.game = DistributedFindFourAI.DistributedFindFourAI(self.air, self.doId, 'findFour', 
                                                                        self.posHpr[0], self.posHpr[1],
                                                                        self.posHpr[2] + 2.8300000000000001,
                                                                        self.posHpr[3], self.posHpr[4], 
                                                                        self.posHpr[5])
                self.sendUpdate('setZone', [self.game.zoneId])

    def requestZone(self):
        if not self.game:
            return

        avId = self.air.getAvatarIdFromSender()
        self.sendUpdateToAvatarId(avId, 'setZone', [self.game.zoneId])

    def requestGameZone(self):
        if self.hasPicked == True:
            avId = self.air.getAvatarIdFromSender()
            if self.game:
                self.game.playersObserving.append(avId)

            self.observers.append(avId)
            self.acceptOnce(self.air.getAvatarExitEvent(avId), self.handleObserverExit, extraArgs=[
                avId])
            if self.game:
                if self.game.fsm.getCurrentState().getName() == 'playing':
                    self.sendUpdateToAvatarId(avId, 'setGameZone', [self.checkersZoneId, 1])
                else:
                    self.sendUpdateToAvatarId(avId, 'setGameZone', [self.checkersZoneId, 0])

    def leaveObserve(self):
        avId = self.air.getAvatarIdFromSender()
        if self.game:
            if avId in self.game.playersObserving:
                self.game.playersObserving.remove(avId)

    def handleObserverExit(self, avId):
        if self.game and avId in self.game.playersObserving:
            if self.game:
                self.game.playersObserving.remove(avId)
                self.ignore(self.air.getAvatarExitEvent(avId))

    def requestExit(self):
        self.notify.debug('requestExit')
        avId = self.air.getAvatarIdFromSender()
        av = self.air.doId2do.get(avId)
        if av:
            if self.countFullSeats() > 0:
                self.acceptExiter(avId)
            else:
                self.notify.debug('Player tried to exit after AI already kicked everyone out')
        else:
            self.notify.warning('avId: %s does not exist, but tried to exit picnicTable' % avId)

    def acceptExiter(self, avId):
        seatIndex = self.findAvatar(avId)
        if seatIndex == None:
            if avId in self.observers:
                self.sendUpdateToAvatarId(avId, 'emptySlot', [
                    avId,
                    255,
                    globalClockDelta.getRealNetworkTime()])

        else:
            self.seats[seatIndex] = None
            self.ignore(self.air.getAvatarExitEvent(avId))
            self.sendUpdate('emptySlot', [
                avId,
                seatIndex,
                globalClockDelta.getRealNetworkTime()])
            self.getTableState()
            numActive = self.countFullSeats()

            if self.game:
                self.game.informGameOfPlayerLeave()
                self.game.handlePlayerExit(avId)

            if numActive == 0:
                self.isAccepting = True
                if self.game:
                    self.game.handleEmptyGame()
                    self.game.requestDelete()
                    self.game = None
                    self.hasPicked = False

    def _DistributedGameTableAI__handleUnexpectedExit(self, avId):
        self.notify.warning('Avatar: ' + str(avId) + ' has exited unexpectedly')
        seatIndex = self.findAvatar(avId)
        if seatIndex == None:
            pass

        self.seats[seatIndex] = None
        self.ignore(self.air.getAvatarExitEvent(avId))
        if self.game:
            self.game.informGameOfPlayerLeave()
            self.game.handlePlayerExit(avId)
            self.hasPicked = False

        self.getTableState()
        numActive = self.countFullSeats()

        if numActive == 0 and self.game:
            simbase.air.deallocateZone(self.game.zoneId)
            self.game.requestDelete()
            self.game = None
            self.gameDoId = None
            self.hasPicked = False

    def informGameOfPlayerExit(self, avId):
        self.game.handlePlayerExit(avId)

    def handleGameOver(self):
        for toon in self.observers:
            self.acceptExiter(toon)
            self.observers.remove(toon)

        if self.game:
            self.game.playersObserving = []

        for toon in self.seats:
            if toon != None:
                self.acceptExiter(toon)
                continue

        self.game = None
        self.gameDoId = None
        self.hasPicked = False

    def findAvatar(self, avId):
        for si in xrange(len(self.seats)):
            if self.seats[si] == avId:
                return si
                
        return -1
         
    def countFullSeats(self):
        toonCount = 0
        for toon in self.seats:
            if toon != None:
                toonCount += 1
                
        return toonCount

    def findAvailableSeat(self):
        for si in xrange(len(self.seats)):
            if self.seats[si] == None:
                return si
                
        return -1

    def setCheckersZoneId(self, zoneId):
        self.checkersZoneId = zoneId

    def setTableIndex(self, index):
        self._tableIndex = index

    def getTableIndex(self):
        return self._tableIndex
