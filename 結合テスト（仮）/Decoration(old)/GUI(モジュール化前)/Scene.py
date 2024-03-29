# -*- coding: utf-8 -*-
import pygame
from pygame.locals import *

import codecs
import sys
import numpy as np
import cv2
import matplotlib.pyplot as plt
import datetime
import random

import IScene
import Util
import Face
import Window
import SceneEventID
import FaceDetectionDummy


# シーンクラス
# 画面内の処理を行う
# （顔の検出やスコアの計算、カメラからの映像やフレームの描画、等）
class Scene(IScene.IScene):
    # コンストラクタ
    def __init__(self, window):
        # メンバ変数の初期化 ---------------------------------------------------
        super(Scene, self).__init__(window)
        self.__sceneID = IScene.SceneID.MAIN

        self.__dirPathOfEmotionImages       = "./frame"                      # フレーム画像が存在するディレクトリのパス
        self.__pathOfemotionImageListFile   = "./frame/emotionImageList.txt" # 
        self.__pathInitSceneFile            = "./init/scene.info"
        self.__clock = pygame.time.Clock()
        self.__faces = {}
        self.__emotionNames = []                # 表情の名称を格納するリスト
        self.__emotionImages = {}               # 表情の名称に対応する画像を格納する辞書型リスト

        self.__captureImage          = None     # カメラからキャプチャーした画像
        self.__captureImageForPygame = None     # カメラからキャプチャーした画像をpygame用に変換したもの

        self.__curlikelyEmotionName  = None     # 各顔の各表情スコアから求めた尤もらしい表情
        self.__maxScore              = -1       # 各顔の各表情スコアから求めた尤もらしい表情の合計スコア

        self.__window = window                  # シーンを扱うウィンドウを取得する
        self.__isExitFlag = False               # シーン終了フラグをOFFにする
        self.__sceneEventId = SceneEventID.SceneEventID()    # シーンイベントを初期化する
        self.__initEmotionNames()               # 表情の名称を取得する
        self.__readImageFiles()                 # 表情に対応したフレームを取得する
        self.__window.setFontSize(20)           # フォントサイズを設定する


        sceneInfo = open(self.__pathInitSceneFile , "r")
        if sceneInfo == None:
            print("./init/scene.infoが見つかりませんでした")
        else:
            cameraType = int((sceneInfo.readline()).rstrip("\n"))
            # 引数： 0...内蔵カメラ　1...USB接続カメラ
            self.__cameraCapture = cv2.VideoCapture(cameraType)  
            if not self.__cameraCapture.isOpened():
                print("カメラが接続されていません・・・")
            else:
                self.__readVideoCapture()
            self.__isDrawLargeFrame = int((sceneInfo.readline()).rstrip("\n"))
            self.__isDrawFaceFrames = int((sceneInfo.readline()).rstrip("\n"))
            self.__isDrawDetectedRegions = int((sceneInfo.readline()).rstrip("\n"))
                

    # 更新処理のメインとなるメソッド
    def update(self):
        self.__eventCheck()         # シーンイベントを確認する
        self.__doEvent()            # シーンイベントを実行する
        return True

    # 描画処理のメインとなるメソッド
    def draw(self):
        self.__drawCaptureImage()       # カメラからの画像を描画する

        # 各顔を表情スコアが最大となる表情のフレームで囲うようにフレームを描画する
        if self.__isDrawFaceFrames:
            self.__drawFrameByFaces()       
        
        # 各顔の検出位置を示す矩形を表示する
        if self.__isDrawDetectedRegions:
            self.__drawDetectedRegions()

        # 画面全体を覆うフレームを描画する
        if self.__isDrawLargeFrame:
            self.__drawFrame()

        self.__window.reverseScreen()   # カメラからの映像は鏡合わせになるので左右反転させる

        #if self.__curlikelyEmotionName != None:
        #    emotionNameAndScore  = "%10s, scoree = %10s" % (self.__curlikelyEmotionName, str(self.__maxScore))
        #    self.__window.drawText(emotionNameAndScore, 100, 100)
        return True

    # シーンが終了状態かどうか取得する
    def isExit(self):
        return self.__isExitFlag


# 初期化(__init__)関連のメソッド ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # 各表情の名称を格納したリストを取得するメソッド
    # face クラスから各名称を取得する
    def __initEmotionNames(self):
        tempFace = Face.Face()
        for emotionName in tempFace.emotionScores.keys():
            self.__emotionNames.append(emotionName)



# 描画(__draw)関連のメソッド ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # 検出箇所を描画するメソッド
    def __drawDetectedRegions(self):
        for face in self.__faces:
            rect = pygame.Rect(face.x, face.y, face.width, face.width)
            rgb = (0, 255, 0)
            self.__window.drawRect(rgb, rect, 2)

    # 各顔を表情スコアが最大となる表情のフレームで囲うようにフレームを描画するメソッド
    def __drawFrameByFaces(self):
        resizedFrames = []
        for face in self.__faces:
            likelyEmotionName   = None
            maxScore            = -1
            for emotionName in face.emotionScores.keys():
                score = face.emotionScores[emotionName]
                if score > maxScore:
                    maxScore = score
                    likelyEmotionName = emotionName
            frameImage = pygame.transform.scale(
                self.__emotionImages[likelyEmotionName],
                (face.width,face.width)
            )
            self.__window.drawImg(frameImage, face.x, face.y)


    # カメラから読み込んだ画像を描画するメソッド
    def __drawCaptureImage(self):    
        if self.__captureImageForPygame != None:
            self.__window.drawImg(self.__captureImageForPygame, 0, 0)

    
    # フレームを描画するメソッド
    def __drawFrame(self):
        if self.__curlikelyEmotionName == None:
            return
        if self.__curlikelyEmotionName in self.__emotionNames:
            self.__window.drawImg(self.__emotionImages[self.__curlikelyEmotionName], 0, 0)
        else:
            print("\"Face\" クラスに存在しない表情名" + "\"" + self.__curlikelyEmotionName + "\"が尤もらしい表情として指定されました．")

    # カメラから映像１フレーム分を読み込むメソッド
    def __readVideoCapture(self):
        isSuccessed, captureImage = self.__cameraCapture.read()   
        if isSuccessed:
            self.__captureImage = captureImage                                              # まず、普通にOpenCVで使用可能な形式で読み込み、
            self.__captureImageForPygame = Util.cvtOpenCVImgToPygame(self.__captureImage)   # これをpygameで使用可能な形式へと変換する
        else:
            print("failed to read video camera image...")
            size = self.__window.getHeight(), self.__window.getWidth(), 3
            contours = np.array( [ [0,0], [0,size[1]], [size[0], size[1]], [size[0],0] ] )
            dummy = np.zeros(size, dtype=np.uint8)

    # 画像ファイルを読み込むメソッド
    def __readImageFiles(self):
        self.__readFrameImgFiles()  # フレーム画像を読み込む

    # 表情の名称とペアな画像を読み込むメソッド
    # 読み込みには "./frame/emotionsList.txt" を利用する
    def __readFrameImgFiles(self):
        emotionImageListFile = open(self.__pathOfemotionImageListFile, 'r')
        emotionImageList = []
        wndWidth = self.__window.getWidth()
        wndHeight = self.__window.getHeight()
        while True:
            line = emotionImageListFile.readline()
            if not line:
                break
            line.strip("\n")
            pair = line.split()
            if len(pair) < 2:
                continue
            #print(pair)
            self.__emotionImages[pair[0]] = pygame.image.load(self.__dirPathOfEmotionImages + "/" + pair[1])
            imgRect = self.__emotionImages[pair[0]].get_rect()
            imgWidth = imgRect.width
            imgHeight = imgRect.height
            widthRate = float(wndWidth) / float(imgWidth)
            heightRate = float(wndHeight) / float(imgHeight)
            self.__emotionImages[pair[0]] = pygame.transform.scale(
                    self.__emotionImages[pair[0]], (wndWidth, wndHeight)
            )


# 更新(__update)関連のメソッド ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # シーンの現在行うべきイベントを確認する
    def __eventCheck(self):
        self.__sceneEventId.set(SceneEventID.SceneEventID.NON)                      # イベントIDの記録を初期化
        for event in pygame.event.get():                                            # イベントを確認
            # ウィンドウの×ボタンが押された場合
            if event.type == pygame.QUIT:
                self.__sceneEventId.set(SceneEventID.SceneEventID.EXIT_SCENE)
                break
            # 何かしらキーが押された場合
            elif event.type == KEYUP:
                # [ESC]：シーンを終了状態にするフラグを立てる
                if event.key == K_ESCAPE:   
                    self.__sceneEventId.set(SceneEventID.SceneEventID.EXIT_SCENE)
                # [S]：現在画面に表示されている画像を保存するフラグを立てる
                elif event.key == K_s:      
                    self.__sceneEventId.set(SceneEventID.SceneEventID.SAVE_IMAGE)
                # [1]：画面を覆うフレームの表示/非表示を切り替えるフラグを反転させる
                elif event.key == K_1:
                    self.__isDrawLargeFrame = not self.__isDrawLargeFrame 
                # [2]：各顔を覆うフレームの表示/非表示を切り替えるフラグを反転させる
                elif event.key == K_2:
                    self.__isDrawFaceFrames = not self.__isDrawFaceFrames 
                # [3]：各顔の検出位置を示す矩形の表示/非表示を切り替えるフラグを反転させる
                elif event.key == K_3:
                    self.__isDrawDetectedRegions = not self.__isDrawDetectedRegions 
        if self.__sceneEventId.isNon():
            self.__sceneEventId.set(SceneEventID.SceneEventID.COMPUTE_SCORES)

    # 顔リストに格納された表情スコアを元に画面へ表示するフレームを選択するメソッド
    def __selectDrawFrameByFaces(self):
        # 表情スコア計算用の辞書型リストを取得する
        emotionSumScores = Face.Face().emotionScores

        # 念の為、初期化する
        for emotionName in emotionSumScores.keys():
            emotionSumScores[emotionName] = 0.0

        # カメラから画像を取得する
        self.__readVideoCapture()

        # 顔を検出する
        self.__faces = self.__detectFaces()
        
        # 各顔の表情スコアを求める
        self.__faces = self.__computeFaceScores(self.__faces)

        # スコア別に合計を求める
        for face in self.__faces:
            for emotionName in face.emotionScores.keys():
                emotionSumScores[emotionName] += face.emotionScores[emotionName]
                #print("!" + str(face.emotionScores[emotionName]) + "!")
        
        # スコアの合計が最大である表情の名称とそのスコアを取得する
        self.__maxScore = -1                # 最大スコア
        self.__curlikelyEmotionName = None  # 尤もらしい表情の名称
        for emotionName in emotionSumScores.keys():        # スコアが最大である表情の名称を検索する
            emotionScore = emotionSumScores[emotionName]   # 表情に対応するスコアを獲得する
            if emotionScore == 0:                          # 表情スコアが０の場合は対象外
                continue                                
            if emotionScore > self.__maxScore:
                self.__maxScore = emotionScore
                self.__curlikelyEmotionName = emotionName


    # 顔を検出するメソッド
    # 実装は他の人が行うので担当外
    # 仮実装として顔の検出数や位置等は乱数
    def __detectFaces(self):
        faces = FaceDetectionDummy.faceDetectionDummy(self.__captureImage)
        #for f in faces:
        #    print(">>>>>" + str(f.x) + " " + str(f.y) + " " + str(f.width) + " " + str(f.id))
        return faces

    # 検出された顔の表情スコアを求めるメソッド
    # 実装は他の人が行うので担当外
    def __computeFaceScores(self, faces):
        maxSizeFace = Face.Face()
        maxSizeFace.width = 0
        for face in faces:
            if face.width > maxSizeFace.width:
                maxSizeFace = face
        for face in faces:
            cnt = 0
            pos = int(face.width / 25) % len(self.__emotionNames)
            for emotionName in face.emotionScores.keys():
                if cnt == pos:
                    face.emotionScores[emotionName] = 1.0
                else:
                    face.emotionScores[emotionName] = 0
                cnt += 1
                #print("<" + str(face.emotionScores[emotionName]) + ">")
        return faces

    # 画面の内容を画像として保存する
    def __saveImage(self):
        filename = "./" + datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S') + ".jpg"
        print("saved : " + filename)
        self.__window.saveDisp(filename)
    
    # シーンを終了する
    def __exitScene(self):
        self.__isExitFlag = True

    # シーンイベントを実行する
    def __doEvent(self):

        if self.__sceneEventId.isComputeScores():
            self.__selectDrawFrameByFaces()

        elif self.__sceneEventId.isSaveImage():
            self.__saveImage()

        elif self.__sceneEventId.isExitScene():
            self.__exitScene()

        else:
            print("Non Event Now")
