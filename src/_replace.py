'''
Created on Mar 21, 2015

@author: qurban.ali
'''
import pymel.core as pc
import maya.cmds as cmds
import qutil
import os.path as osp
import re
import uiContainer
from PyQt4.QtGui import QMessageBox
import msgBox
import qtify_maya_window as qtfy
import subprocess
import fillinout

logFile = osp.join(osp.dirname(osp.expanduser('~')), 'replaceRef.txt')
texturesFile = osp.join(osp.dirname(osp.expanduser('~')), 'textures.txt')

if not osp.exists(logFile):
    with open(logFile, 'w'):
        pass
if not osp.exists(texturesFile):
    with open(texturesFile, 'w'):
        pass

def createLog(details, fh):
    fh.write('Source File: '+cmds.file(q=True, location=True)+'\r\n'*3)
    fh.write(details)
    fh.write('\r\n'+'-'*100)
    fh.write('\r\n'*4)

def getRefs():
    refs = pc.ls(type='reference')
    fileRefs = []
    for ref in refs:
        if ref.referenceFile():
            fileRefs.append(pc.FileReference(ref))
    return fileRefs

def setResolution():
    node = pc.ls('defaultResolution')[0]
    node.width.set(1920)
    node.height.set(1080)
    pc.setAttr("defaultResolution.deviceAspectRatio", 1.777)
    pc.mel.redshiftUpdateResolution()

def fixAOVPrefixes(*args):
    
    prefixString='<Camera>\Nano_Screen\<RenderLayer>_<AOV>\<RenderLayer>_<AOV>_'
    pc.setAttr("redshiftOptions.imageFilePrefix", prefixString, type="string")
    for node in pc.ls(type='RedshiftAOV'):
        name = node.name().split('|')[-1].split(':')[-1]
        if name.startswith('rsAov_'):
            name = name[6:]
        if pc.attributeQuery('name', n=node, exists=True):
            node.attr('name').set(name)
        ps = re.compile('<AOV>', re.I).sub(name, prefixString)
        node.filePrefix.set(ps)
        node.redId.set(500)
        
def setRenderableCamera(camera):
    for cam in pc.ls(cameras=True):
        if cam.renderable.get():
            cam.renderable.set(False)
    camera.renderable.set(True)
    
def showLog():
    with open(logFile, 'r') as f:
        if f.read():
            btn = msgBox.showMessage(qtfy.getMayaWindow(), title='Replace Ref',
                                     msg='Errors occurred while replacing the reference\n'+
                                     'Log: '+logFile,
                                     ques='Do you want to view the log file now?',
                                     icon=QMessageBox.Information,
                                     btns=QMessageBox.Yes|QMessageBox.No)
            if btn == QMessageBox.Yes:
                subprocess.call('explorer %s'%logFile.replace('/', '\\'), shell=True)

def replace(**kwargs):
    if pc.mel.currentRenderer().lower() != 'redshift':
        pc.warning('Set the current renderer to Redshift')
        return
    nanoFile = r"P:\external\Al_Mansour_Season_02\assets\character\main\nano\nano_regular\sources\maya\Nano_Rig_Shaded_v03.mb"
    if not osp.exists(nanoFile):
        pc.warning(nanoFile +' :Does not exist')
        return
    filePath = kwargs.get('csvfile')
    if not filePath:
        pc.warning('CSV file not specified')
        return
    data = qutil.getCSVFileData(filePath)
    with open(logFile, 'w') as fh:
        with open(texturesFile, 'w') as tfh:
            for row in data:
                try:
                    path = row[0]
                    camera = row[1]
                    savePath = 'D:/shot_test'#= row[2]
                    name = row[3]
                    texture = row[4]
                except IndexError:
                    continue
                nanoRef = []
                otherRefs = []
                if osp.exists(path):
                    if osp.normcase(osp.normpath(path)) != osp.normcase(osp.normpath(cmds.file(q=True, location=True))):
                        cmds.file(path, o=True, f=True, prompt=False)
                        for ref in getRefs():
                            if not 'nano_regular_rig' in ref.path:
                                otherRefs.append(ref)
                            else:
                                nanoRef.append(ref)
                        if len(nanoRef) != 1:
                            createLog('More than one references exist for nano', fh)
                            continue
                        nanoRef = nanoRef[0]
                        nanoRef.replaceWith(nanoFile)
                        for oRef in otherRefs:
                            try:
                                oRef.remove()
                            except Exception as ex:
                                createLog(str(ex), fh)
                        pc.mel.redshiftCreateAov("Puzzle Matte")
                        fixAOVPrefixes()
                        setResolution()
                    try:
                        setRenderableCamera(pc.PyNode(camera))
                    except Exception as ex:
                        createLog(str(ex), fh)
                    pc.setAttr("defaultRenderGlobals.animation", 1)
                    pc.select(camera)
                    try:
                        start, end = fillinout.fill()
                        pc.setAttr("defaultRenderGlobals.extensionPadding", len(str(int(max([start, end])))))
                    except:
                        createLog('Could not find keyframes on camera: '+camera)
                    pc.select(cl=True)
                    fileType = cmds.file(q=True, type=True)[0]
                    ext = '.ma' if fileType == 'mayaAscii' else '.mb'
                    cmds.file(rename=savePath.replace('\\', '/')+'/'+name+ext)
                    cmds.file(s=True, f=True, type=fileType)
                    try:
                        node = pc.ls('*:nano_expressions_file')[0]
                    except IndexError:
                        createLog('Could not find texture file named as: nano_expressions_file')
                        continue
                    node.ftn.set(texture)
                    tfh.write(texture)
                    tfh.write('\r\n')
                else:
                    createLog('File does not exist:\r\n'+ path)
    cmds.file(new=True, f=True)
    showLog()
    btn = msgBox.showMessage(qtfy.getMayaWindow(), title='Replace Ref',
                             msg='Textures file: '+texturesFile,
                             icon=QMessageBox.Information,
                             btns=QMessageBox.Yes|QMessageBox.No)
    if btn == QMessageBox.Yes:
        subprocess.call('explorer %s'%texturesFile.replace('/', '\\'), shell=True)