# -*- coding: utf-8 -*-

class SceneID:
    NONE    = 0
    MAIN    = 1

class IScene(object):
    def __init__(self, window):
        self.__window = window
        self.__sceneID = SceneID.NONE
    
    def draw(self):
        return False
    
    def update(self):
        return False

    def isExit(self):
        return True

    def isRunning(self):
        return not self.isExit()

    def getNextSceneID(self):
        #return SceneID.NONE
        return SceneID.NONE

class NoneScene(IScene):
    def __init__(self, window):
        super(NoneScene, self).__init__(window)



