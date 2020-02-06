from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtPrintSupport import *
from PySide2.QtUiTools import *

from .Config import ICONS

class QPushButtonTest(QPushButton):
    icon_size = 32
    def __init__(self,*args,**kwargs):
        parent = kwargs.get('parent')
        if not parent:
            for i in args:
                if isinstance(i,QWidget):
                    parent = i
        if not parent:
            raise ValueError()
        self._parent = parent
        self.controller = parent.optionController
        
        self.okbwicon = QIcon(ICONS['okbw'])
        self.okicon = QIcon(ICONS['ok'])
        
        # buttons = self.controller.buttons()
        # if buttons:
        #     icon = self.okbwicon
        # else:
        #     icon = self.okicon

        icon = self.okbwicon

        if kwargs.get('icon'):
            kwargs['icon'] = icon
        
        for i in range(len(args)):
            found = False
            if isinstance(args[i],QIcon):
                args[i] = icon
                found = True
        if not found:
            largs = list(args)
            largs.insert(0,icon)
            args = tuple(largs)
        
        super().__init__(*args,**kwargs)

        self.setIconSize(QSize(self.icon_size,self.icon_size))
        self.setCheckable(True)
        self.toggled.connect(self.changeIcon)
        self.state = self.isChecked()
        self.myStyle()
        self.controller.addButton(self)

    def myStyle(self):
        stylesheet = 'background-color: transparent; border: 0px;'
        self.setStyleSheet(stylesheet)
        self.setIconSize(QSize(self.icon_size,self.icon_size))

    @Slot(bool)
    def changeIcon(self,checked):
        if self.state != checked:
            self.state = checked
            if checked == True:
                icon = self.okicon
            else:
                icon = self.okbwicon
            self.setIcon(icon)
            self.myStyle()
            
    # def event(self,event):
    #     if event.type() == QEvent.Type.MouseButtonRelease:
    #         qDebug("Event in QPushButtonTest {}".format(event.type()))
    #     return super().event(event)
