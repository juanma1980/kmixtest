from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtPrintSupport import *
from PySide2.QtUiTools import *

from .Util import marginsToString, print_document_data, print_preview_data, print_printer_data, loadPixMapData, dumpPixMapData, fileToPixMap, dataPixMapToImage
from .PreviewPrinter import previewPrinter
from .Config import ARTWORK, ICONS

from copy import deepcopy

USE_FAKE_HEADER = True

# Helper class with pdf stuff related things
class helperPDF():

    header_table_cols = 3
    header_table_rows = 2

    def __init__(self, parent=None):
        self.parent = parent
        self.pageMargins = QMarginsF(10,10,10,10)
        self.orientation = QPageLayout.Orientation.Portrait
        self.layout = None
        self.printer = None
        self.resolution = QPrinter.HighResolution
        self.constPaperScreen = None
        self.document = None
        self.cursor = None
        self.styles = None
        self.widget = None
        self.printer, self.resolution, self.constPaperScreen, self.layout = self.initPrinter(printer=self.printer, resolution=self.resolution, margins=self.pageMargins, orientation=self.orientation)
        self.widget = None
        self.header_info = None
        self.preview = False
        self.last_cursor_ack = None
        self.last_page_ack = 1

    def initPrinter(self, printer=None, resolution=QPrinter.HighResolution, margins=None, orientation=None):
        
        if not resolution:
            if self.resolution:
                resolution = self.resolution
            else:
                resolution = QPrinter(QPrinter.HighResolution).resolution()
                self.resolution = resolution
        
        if isinstance(resolution,QPrinter.PrinterMode):
            default_printer = QPrinter(resolution)
            resolution = QPrinter(resolution).resolution()
        else:
            default_printer = QPrinter()
            default_printer.setResolution(resolution)
            
        if not printer:
            if self.printer:
                printer = self.printer
            else:
                self.printer = default_printer
                printer = default_printer

        if printer.resolution() != resolution:
            printer.setResolution(resolution)
        
        current_layout = self.printer.pageLayout()
        changed_layout = False
        if current_layout.units() != QPageLayout.Millimeter:
            current_layout.setUnits(QPageLayout.Millimeter)
            changed_layout = True

        if margins is not None and isinstance(margins,QMarginsF):
            qDebug("Setting margins to {}".format(marginsToString(margins)))
            current_layout.setMargins(margins)
            changed_layout = True
        else:
            self.pageMargins = current_layout.margins()
        
        if orientation is not None and isinstance(orientation, QPageLayout.Orientation):
            qDebug("Setting orientation to {}".format(orientation.name.decode()))
            current_layout.setOrientation(orientation)
            changed_layout = True

        if changed_layout:
            printer.setPageLayout(current_layout)

        PaperToScreen = int( resolution / QPrinter(QPrinter.ScreenResolution).resolution() )
        self.constPaperScreen = PaperToScreen
        qDebug("Setting constant: {}".format(int(self.constPaperScreen)))

        relTextToA4 = int(self.printer.pageSizeMM().width()/210.0)
        self.relTextToA4 = relTextToA4
        qDebug("Setting text multiplier size: {}".format(relTextToA4))

        return printer, resolution, PaperToScreen, current_layout

    def initDocument(self, printer=None, document=None):
        if not printer:
            printer = self.printer
        if not document:
            document = ExamDocument()
        if not self.document:
            self.document = document
        document.setHeadersSize(16)
        document.setPage(printer=printer)
        self.initStyles()
        return document

    def initWidget(self, parent=None, printer=None):
        
        widget = previewPrinter(parent=parent,printer=printer)
        if not self.widget:
            self.widget = widget
        widget.paintRequested.connect(self.paintRequest)
        return widget 

    def initSystem(self,printer=None):
        self.last_cursor_ack = None
        self.last_page_ack = 1
        if printer:
            self.printer = printer
        self.printer, self.resolution, self.constPaperScreen, self.layout = self.initPrinter(printer=self.printer, resolution=self.resolution, margins=self.pageMargins)
        self.document = self.initDocument(printer = self.printer)
        if not self.preview:
            self.printer.setOutputFormat(QPrinter.PdfFormat)
            self.printer.setOutputFileName('out.pdf')

    def openWidget(self):
        self.preview = True
        self.widget = self.initWidget(parent=self, printer=self.printer)
        self.widget.exec_()

    def writePDF(self):
        self.preview = False
        self.paintRequest()

    def initStyles(self, styles=None):
        
        if not styles:
            styles = {}
            self.styles = styles

        styles['line'] = QTextFrameFormat()
        styles['line'].setHeight(1*self.constPaperScreen*self.relTextToA4)
        styles['line'].setBackground(Qt.black)

        styles['pagebreak'] = QTextBlockFormat()
        styles['pagebreak'].setPageBreakPolicy(QTextFormat.PageBreak_AlwaysBefore)

        if not 'header.table' in styles:
            styles.setdefault('header.table',QTextTableFormat())
        styles['header.table'].setBorderStyle(QTextTableFormat.BorderStyle_Solid)
        styles['header.table'].setBorder(1.0)
        styles['header.table'].setBorderBrush(QBrush(Qt.black,Qt.SolidPattern))
        styles['header.table'].setMargin(0.0)
        styles['header.table'].setCellSpacing(0.0)
        styles['header.table'].setCellPadding(10 * self.constPaperScreen)
        styles['header.table'].setColumnWidthConstraints([ QTextLength(QTextLength.PercentageLength, 95/self.header_table_cols) ] * self.header_table_cols)

        if not 'title.table' in styles:
            styles.setdefault('title.table',QTextTableFormat())
        styles['title.table'].setBorderStyle(QTextTableFormat.BorderStyle_None)
        styles['title.table'].setBorder(0.0)
        # styles['title.table'].setBorderBrush(QBrush(Qt.black,Qt.SolidPattern))
        styles['title.table'].setMargin(0.0)
        styles['title.table'].setCellSpacing(0.0)
        #styles['title.table'].setCellPadding(10 * self.constPaperScreen)
        styles['title.table'].setColumnWidthConstraints([ 
            QTextLength(QTextLength.PercentageLength, 75), 
            QTextLength(QTextLength.PercentageLength, 25)
        ] )

        if not 'option.table' in styles:
            styles.setdefault('option.table',QTextTableFormat())
        styles['option.table'].setBorderStyle(QTextTableFormat.BorderStyle_Solid)
        styles['option.table'].setBorder(2.0)
        styles['option.table'].setMargin(0.0)
        styles['option.table'].setCellSpacing(10 * self.constPaperScreen)
        styles['option.table'].setBorderBrush(QBrush(Qt.black,Qt.SolidPattern))
        styles['option.table'].setColumnWidthConstraints([ 
            QTextLength(QTextLength.PercentageLength, 5), 
            QTextLength(QTextLength.PercentageLength, 20)
        ] )
        styles['centerH'] = QTextBlockFormat()
        styles['centerH'].setAlignment(Qt.AlignCenter)
        
        styles['centerV'] = QTextCharFormat()
        styles['centerV'].setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)

        styles['body'] = QTextBlockFormat()
        styles['body'].setAlignment(Qt.AlignJustify)

        styles['double'] = QTextBlockFormat()
        styles['double'].setLineHeight(200,QTextBlockFormat.ProportionalHeight)

        styles['single'] = QTextBlockFormat()
        styles['single'].setLineHeight(100,QTextBlockFormat.ProportionalHeight)
        
        qDebug("Using text multiplier size: {}".format(int(self.relTextToA4)))
        styles['defaultfont'] = QFont("Times",10 * self.constPaperScreen * self.relTextToA4)
        styles['bigfont'] = QFont("Times",30 * self.constPaperScreen * self.relTextToA4)

        styles['text'] = QTextCharFormat()
        styles['bigtext'] = QTextCharFormat()
        styles['text'].setFont(styles['defaultfont'])
        styles['bigtext'].setFont(styles['bigfont'])
        
        return styles

    def print_cursor_position_y(self,document,cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        page_h = document.pageSize().height()
        current_h = document.documentLayout().blockBoundingRect(cursor.block()).y()
        pagenumber = int(current_h/page_h)+1
        pagecount = document.pageCount()
        qDebug('Cursor at: {} page={}'.format(current_h,pagenumber,pagecount))
        return pagenumber

    @Slot(QPrinter)
    def paintRequest(self, printer=None):
        qDebug("***** Repaint Event ! *****")

        self.initSystem(printer)
        
        #print_document_data(self.document)
        #print_printer_data(self.printer)

        self.document = self.completeDocument(self.document)
        #self.document = self.makeTestDocument(self.document)
        #print_document_data(self.document)
        self.document.printExamModel(self.printer,model="A")

        #print_document_data(self.document)

    # def makeTestDocument(self,document):
    #     #Init cursor
    #     cursor = QTextCursor(document)
    #     # cursor.movePosition(QTextCursor.End)
    #     # if cursor.hasSelection():
    #     #     cursor.clearSelection()
    #     t={}
    #     for l in list('abcdefghijk'):
    #         t[l] = ''
    #         for i in range(1,20):
    #             t[l] += '{0:s}_{1:03d}_'.format(l*5,i*10)

    #     style_t = QTextCharFormat()
    #     font = QFont("Courier",10 * self.constPaperScreen * self.relTextToA4)
    #     style_t.setFont(font)
    #     style_b = QTextBlockFormat()
    #     style_f = QTextFrameFormat()

    #     cursor.insertBlock(style_b)
    #     a = cursor.block()
    #     a.setUserData(BData('a'))
    #     cursor.insertText(t.get('a'),style_t)

    #     cursor.movePosition(QTextCursor.End)
    #     cursor.insertBlock(style_b)
    #     b = cursor.block()
    #     b.setUserData(BData('b'))
    #     bpos = b.blockNumber()
    #     cursor.insertText(t.get('b'),style_t)

    #     cursor.movePosition(QTextCursor.Start)
    #     cursor.insertBlock(style_b)
    #     c = cursor.block()
    #     cursor.insertText(t.get('c'),style_t)

    #     cursor = QTextCursor(b)
    #     pos = cursor.position()
    #     cursor.insertBlock(style_b)
    #     d = cursor.block()
    #     cursor.setPosition(pos)
    #     cursor.insertText(t.get('d'),style_t)

    #     cursor = QTextCursor(b)
    #     pos2 = cursor.position()
    #     cursor.insertBlock(style_b)
    #     e = cursor.block()
    #     cursor.setPosition(pos2)
    #     cursor.insertText(t.get('e'),style_t)

    #     cursor.movePosition(QTextCursor.Start)
    #     cursor.movePosition(QTextCursor.NextBlock,QTextCursor.MoveAnchor,b.blockNumber())
    #     pos3 = cursor.position()
    #     cursor.insertBlock(style_b)
    #     f = cursor.block()
    #     cursor.setPosition(pos3)
    #     cursor.insertText(t.get('f'),style_t)

    #     cursor.movePosition(QTextCursor.Start)
    #     while cursor.block().userData() is None or cursor.block().userData().data != 'b':
    #         cursor.movePosition(QTextCursor.NextBlock,QTextCursor.MoveAnchor,1)
    #     cursor.setPosition(cursor.position()-1)
    #     cursor.insertBlock(style_b)
    #     g = cursor.block()
    #     cursor.insertText(t.get('g'),style_t)

    #     cursor.movePosition(QTextCursor.Start)
    #     tb = cursor.block()
    #     tb = tb.next().next().next()
    #     cursor = QTextCursor(tb)
    #     style_cr = QTextBlockFormat()
    #     style_cr.setPageBreakPolicy(QTextFormat.PageBreak_AlwaysBefore)
    #     cursor.insertBlock(style_cr)

    #     cursor.movePosition(QTextCursor.Start)
    #     cursor = document.find('bbb')
    #     if cursor.isNull():
    #         qDebug('null')
    #     else:
    #         cursor.movePosition(QTextCursor.StartOfBlock)
    #         cursor.insertBlock(style_cr)

    #     qDebug('Total {} blocks'.format(document.blockCount()))

    #     qDebug('{}'.format(document.toHtml()))
    #     return document


    def completeDocument(self,document):
        document = self.makeHeaderTable(document,self.styles['header.table'] )
        document = self.writeExamData(document)
        return document

    def buildFakeHeaderInfo(self):
        from random import randint
        a = randint(3,20)
        b = randint(3,20)
        header_info = { 
            'west' : {
                'type': 'image',
                'data': dumpPixMapData(fileToPixMap(ARTWORK['left'])),
                'content': QUrl(ARTWORK['left']).toString()
            },
            'north' : {
                'type': 'image',
                'data': dumpPixMapData(fileToPixMap(ARTWORK['center'])),
                'content': QUrl(ARTWORK['center']).toString()
            },
            'south' : {
                'type': 'text',
                'content': "Lorem ipsum " * a
            },
            'east' : {
                'type': 'text',
                'content': "Lorem ipsum " * b
            }
        }
        return header_info

    def setupCell(self, table, row=0, col=0, centerH=True, centerV=True):
        cell = table.cellAt(row,col)
        cursor = cell.firstCursorPosition()
        if centerH:
            cursor.setBlockFormat(self.styles['centerH'])
        if centerV:
            cell.setFormat(self.styles['centerV'])
        return cursor,cell

    def imageResized(self, name, max_image_height, max_image_width):
        image = QImage(name)
        new_image_height = image.height() * max_image_width / image.width()
        image = image.scaled(max_image_width,new_image_height,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        if image.height() > max_image_height:
            new_image_width = image.width() * max_image_height / image.height()
            image = image.scaled(new_image_width,max_image_height,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        return image

    def makeHeaderTable(self, document, style, rows = header_table_rows, cols = header_table_cols, images = ARTWORK):

        max_image_width = (document.pageSize() / cols).width()
        max_image_height = (document.pageSize() / 6).height() # no big headers!

        first_element_row = 1
        first_element_col = 0
        num_rows = 1
        num_cols = cols

        coords = { 
            'west' : { 'y':0,'x':0 },
            'north': { 'y':0,'x':1 },
            'south': { 'y':1,'x':0 },
            'east': {'y':0,'x':2 }
        }

        cursor = QTextCursor(document)
        table = cursor.insertTable(rows,cols,self.styles['header.table'])
        table.mergeCells(first_element_row,first_element_col,num_rows,num_cols)

        positions = self.header_info.keys()
        for pos in positions:
            position = self.header_info.get(pos)
            coord = coords.get(pos)
            cursor,cell = self.setupCell(table,coord['y'],coord['x'])
            typeh = position.get('type')
            if typeh == 'text':
                cursor.insertText(position.get('content'), self.styles['text'])
            elif typeh == 'image':
                cursor.insertImage(self.imageResized(dataPixMapToImage(position.get('data')),max_image_height,max_image_width))
        self.writeSeparator(document)
        return document

    def makeTitleTable(self, document, rows, cols, cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        table = cursor.insertTable(rows,cols,self.styles['title.table'])
        return table
        
    def initCursor(self,document):
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.End)
        if cursor.hasSelection():
            cursor.clearSelection()
        return cursor

    def writeSeparator(self, document, cursor=None, number=None , single=False):
        if not cursor:
            cursor = self.initCursor(document)
        if single:
            style = self.styles['single']
        else:
            style = self.styles['double']
        cursor.insertBlock(style,self.styles['text'])
        txt = ""
        if number:
            txt = '{}'.format(number)
        cursor.insertText(txt)
        return cursor

    def setExamData(self,examData):
        self.examData = deepcopy(examData)

    def writeImage(self, document, image, cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        cursor.insertImage(image)

    def debug_document_blocklayout(self,document):
        ret=[]
        blockCount = document.blockCount()
        for i in range(blockCount):
            r = document.documentLayout().blockBoundingRect(document.findBlockByNumber(i))
            ret.append('Block #{} on ({},{}) with {}x{}'.format(i,r.x(),r.y(),r.width(),r.height()))
        qDebug("\n".join(ret))
        return ret

    def writePageBreak(self, document, cursorpos=None):
        cursor = QTextCursor(document)
        if not cursorpos:
            cursor = self.initCursor(document)
            cursor.insertBlock(self.styles['pagebreak'])
        else:
            cursor.setPosition(cursorpos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.blockFormat().setPageBreakPolicy(QTextFormat.PageBreak_AlwaysBefore)
            cursor.insertBlock(self.styles['pagebreak'])
        pass
        

    def writeLine(self, document, cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        pagenum = self.print_cursor_position_y(document,cursor)

        cursor.insertFrame(self.styles['line'])
        ret = cursor.movePosition(QTextCursor.Down)
        return cursor
        
        self.debug_document_blocklayout(document)
        if pagenum != self.last_page_ack:
            qDebug('BACKTRACK')
            self.writePageBreak(document)
            #self.writePageBreak(document,self.last_cursor_ack)
            self.debug_document_blocklayout(document)

        self.last_cursor_ack = cursor
        self.last_page_ack = pagenum

    def writeExamData(self,document):
        self.pagequestion = {}
        question_num = 0
        for row in self.examData:
            question_num += 1
            title = row.get('title')
            title = title.capitalize()
            typeq = row.get('type')
            title_pic = row.get('title_pic')
            cursor = self.initCursor(document)
            cursor_ini = cursor.position()
            pagestart = self.print_cursor_position_y(document)
            if title_pic:
                table = self.makeTitleTable(document, rows=1, cols=2, cursor=cursor)
                if title:
                    cursor1,cell = self.setupCell(table,0,0,centerV=False)
                    self.writeTitle(document,title, cursor=cursor1)
                cursor2,cell = self.setupCell(table,0,1,centerV=False)
                image = dataPixMapToImage(title_pic)
                max_image_width = (document.pageSize() / 4).width()
                image = image.scaledToWidth(max_image_width,Qt.SmoothTransformation)
                self.writeImage(document, image, cursor=cursor2)
                qDebug('End question with table, (title={})'.format(title))
                self.print_cursor_position_y(document)
            else:
                if title:
                    self.writeTitle(document,title, cursor=cursor)
                    qDebug('End question (title={})'.format(title))
                    self.print_cursor_position_y(document)
            self.writeSeparator(document,single=True)
            nlines = 0
            options = None
            if typeq == 'single_question':
                nlines = row.get('empty_lines')
            else:
                options = row.get('options')
            
            if typeq == 'test_question':
                self.writeTest(document,options)
            elif typeq == 'join_activity':
                self.writeJoinActivity(document,options)

            for i in range(1,nlines+1):
                self.writeSeparator(document,number=i)
                qDebug('Space {}'.format(i))
                self.print_cursor_position_y(document)
            
            cursor_end = self.writeLine(document)
            cursor_end = cursor_end.position()
            pageend = self.print_cursor_position_y(document)
            self.pagequestion.setdefault(pagestart,[])
            self.pagequestion.setdefault(pageend,[])
            if pagestart == pageend:
                self.pagequestion[pagestart].append(question_num)
                self.last_cursor_ack = cursor_end
            else:
                if len(self.pagequestion[pagestart]) > 0:
                    self.writePageBreak(document,cursor_ini)
                else:
                    pass
            
        return document

    def writeTest(self, document, options, cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        
        rows = len(options)
        f = QTextFrameFormat()
        tabsize = 4
        f.setLeftMargin(QFontMetrics(self.styles['defaultfont']).maxWidth()*tabsize)
        cursor.insertFrame(f)
        cursor.movePosition(QTextCursor.EndOfLine)
        table = cursor.insertTable(rows,2,self.styles['option.table'])
        f = QTextFrameFormat()
        tabsize = 4
        f.setRightMargin(QFontMetrics(self.styles['defaultfont']).maxWidth()*tabsize)
        ret = cursor.movePosition(QTextCursor.NextCell)
        cursor.insertFrame(f)
        cursor.insertText("A"*100)
        i=0
        for opt in options:
            text = opt.get('text1')
            text = text.capitalize()
            pic = opt.get('pic1')

            c,cell = self.setupCell(table,i,0,centerV=False,centerH=False)
            img = QImage(ICONS['option'])
            img = img.scaledToHeight(QFontMetrics(self.styles['defaultfont']).height()*0.9,Qt.SmoothTransformation)
            c.insertImage(img)
            c,cell = self.setupCell(table,i,1,centerV=False,centerH=False)
            c.setCharFormat(self.styles['text'])
            c.insertText(text)

            i += 1
       
        return self.writeSeparator(document,single=True)

    def writeJoinActivity(self, document, options, cursor=None):
        if not cursor:
            cursor = self.initCursor(document)
        
        rows = len(options)
        f = QTextFrameFormat()
        tabsize = 4
        f.setLeftMargin(QFontMetrics(self.styles['defaultfont']).maxWidth()*tabsize)
        cursor.insertFrame(f)
        cursor.movePosition(QTextCursor.EndOfLine)
        table = cursor.insertTable(rows,5,self.styles['option.table'])
        separator = " " * 50 
        i=0
        for opt in options:
            text1 = opt.get('text1')
            text1 = text1.capitalize()
            pic1 = opt.get('pic1')
            text2 = opt.get('text1')
            text2 = text2.capitalize()
            pic2 = opt.get('pic1')

            c,cell = self.setupCell(table,i,1,centerV=False,centerH=False)
            img = QImage(ICONS['option'])
            img = img.scaledToHeight(QFontMetrics(self.styles['defaultfont']).height()*0.9,Qt.SmoothTransformation)
            c.insertImage(img)
            c,cell = self.setupCell(table,i,0,centerV=False,centerH=False)
            c.setCharFormat(self.styles['text'])
            c.insertText(text1)
            
            c,cell = self.setupCell(table,i,2,centerV=False,centerH=False)
            c.setCharFormat(self.styles['text'])
            c.insertText(separator)

            c,cell = self.setupCell(table,i,3,centerV=False,centerH=False)
            img = QImage(ICONS['option'])
            img = img.scaledToHeight(QFontMetrics(self.styles['defaultfont']).height()*0.9,Qt.SmoothTransformation)
            c.insertImage(img)
            c,cell = self.setupCell(table,i,4,centerV=False,centerH=False)
            c.setCharFormat(self.styles['text'])
            c.insertText(text2)
            i += 1

        return self.writeSeparator(document,single=True)

    def writeTitle(self,document,text, cursor=None):
        if document and text:
            if not cursor:
                cursor = self.initCursor(document)
            cursor.insertBlock(self.styles['body'],self.styles['text'])
            cursor.insertText(text)

    def validateHeader(self,header):
        fake = None
        if USE_FAKE_HEADER:
            fake = self.buildFakeHeaderInfo()

        if not header or not isinstance(header,dict):
            if fake:
                return fake
            header = {'west':{},'north':{},'east':{},'south':{}}

        ks = ['west','north','east','south']
        for k in ks:
            if k not in header.keys():
                if fake:
                    header[k] = deepcopy(fake[k])
                    continue
                header.setdefault(k,{})

            if not isinstance(header[k],dict):
                if fake:
                    header[k] = deepcopy(fake[k])
                    continue
                header[k]={}

            header[k].setdefault('type','text')
            if header[k]['type'] not in ['image','text']:
                if fake:
                    header[k] = deepcopy(fake[k])
                    continue
                header[k]['type'] = 'text'

            if header[k]['type'] == 'image':
                if not header[k].get('data'):
                    if fake:
                        header[k] = deepcopy(fake[k])
                        continue
                    header[k]['type'] = 'text'

            if header[k]['type'] == 'text':
                header[k].setdefault('content','')

        return header

    def setHeaderInfo(self,header_info):
            self.header_info = deepcopy(self.validateHeader(header_info))

# class BData(QTextBlockUserData):
#     def __init__(self,data=None):
#         super().__init__()
#         self.data = data

class ExamDocument(QTextDocument):
    def __init__(self,*args,**kwargs):
        self.headersSize = 16
        self.resolution = None
        super().__init__(*args,**kwargs)

    def setHeadersSize(self, value):
        self.headersSize = value

    def setPage(self,pageSize=None,printer=None):
        if not pageSize:
            if printer:
                self.resolution = printer.resolution()
                pageSize = printer.pageRect().size()
                if self.headersSize:
                    pageSize.setHeight(pageSize.height()-self.mmToPixels(self.headersSize))
            else:
                return
        self.setPageSize(pageSize)
    
    def mmToPixels(self, mm, printer=None):
        # 1 pixel per inch (ppi) = 0.03937 pixel per mm (dpi)
        # 1 pixel per mm (dpi)   = 25.4 pixel per inch (ppi)
        # 1 inch = 25.4 mm
        res = None
        if not printer:
            if self.resolution:
                res = self.resolution
        else:
            res = printer.resolution()
        if res:
            return mm * 0.039370147 * res
        return None

    def printPageWithHeaders(self,index,painter,document,body,printer,header="HEADER",footer="FOOTER"):

        fontHeaders = QFont('courier',16,QFont.Black)

        printer_height = printer.height()
        paper_height = body.height()

        offset_document = (index-1) * paper_height

        free_space = printer_height - paper_height
        header_height = free_space / 2
        footer_height = free_space / 2

        # header rect
        # Coordinates into one page
        headerPageRect = QRectF(0,0, printer.width(), header_height)
        # text rect
        # Coordinates into one page
        # textPageRect = QRectF(0, header_height, printer.width(), body.height())
        # view rect
        # Coordinates into full document
        viewRect = QRectF(QPointF(0,offset_document), body.size())
        # footer rect
        # Coordinates into one page
        footerPageRect = QRectF(0,printer_height-footer_height, printer.width(), header_height)

        offset_line = self.mmToPixels(2)

        pen = painter.pen()
        pen.setColor(Qt.black)

        painter.save()        
        painter.setRenderHint(QPainter.TextAntialiasing,True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing,False)

        offset_header = 0

        if header:
            painter.setPen(pen)
            painter.setFont(fontHeaders)
            painter.drawText(headerPageRect,Qt.AlignRight, header)
            pen.setWidth(5)
            painter.setPen(pen)
            painter.drawLine(0,header_height-offset_line,printer.width(),header_height-offset_line)
            offset_header = header_height
        
        offset_header = - offset_document + offset_header
        painter.translate(0, offset_header)
        
        layout = document.documentLayout()
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.clip = viewRect
        ctx.palette.setColor(QPalette.Text,Qt.black)
        layout.draw(painter,ctx)
        painter.restore()
        
        if footer:
            painter.save()
            painter.setRenderHint(QPainter.TextAntialiasing,True)
            painter.setRenderHint(QPainter.HighQualityAntialiasing,False)
            pen = painter.pen()
            pen.setWidth(5)
            pen.setColor(Qt.black)
            painter.setPen(pen)
            painter.drawLine(0,paper_height+header_height-offset_line,printer.width(),paper_height+header_height-offset_line)
            painter.setFont(fontHeaders)
            painter.drawText(footerPageRect,Qt.AlignRight, footer)
            painter.restore()

    def printExamModel(self,printer,model=""):
        p = QPainter(printer)       
        self.setPage(printer=printer)
        body = QRectF(QPointF(0,0),self.pageSize())
        for i in range(self.pageCount()):
            if i != 0:
                printer.newPage()
            self.printPageWithHeaders(i+1,p,self,body,printer,header=model,footer=str(i+1))

# class MyPrinter(QPrinter):
#     def __init__(self,*args,**kwargs):
#         super().__init__(*args,**kwargs)
#     def paintRequested(self,*args,**kwargs):
#         super().__init__(*args,**kwargs)