# -*- coding: utf-8 -*-
#**************************************************************************
#*                                                                     *
#* Copyright (c) 2019 Joel Graff <monograff76@gmail.com>               *
#*                                                                     *
#* This program is free software; you can redistribute it and/or modify*
#* it under the terms of the GNU Lesser General Public License (LGPL)  *
#* as published by the Free Software Foundation; either version 2 of   *
#* the License, or (at your option) any later version.                 *
#* for detail see the LICENCE text file.                               *
#*                                                                     *
#* This program is distributed in the hope that it will be useful,     *
#* but WITHOUT ANY WARRANTY; without even the implied warranty of      *
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
#* GNU Library General Public License for more details.                *
#*                                                                     *
#* You should have received a copy of the GNU Library General Public   *
#* License along with this program; if not, write to the Free Software *
#* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#* USA                                                                 *
#*                                                                     *
#***********************************************************************
"""
Command to draft a new alignment
"""

import os

import FreeCAD as App
import FreeCADGui as Gui

import Draft
import DraftTools
from DraftGui import translate, todo

from ..tasks.alignment.draft_alignment_task import DraftAlignmentTask

from ... import resources
from .alignment_tracker import AlignmentTracker


class DraftAlignmentCmd(DraftTools.Line):
    """
    Initiates and manages drawing activities for alignment creation
    """

    def __init__(self):
        """
        Constructor
        """

        super(DraftAlignmentCmd, self).__init__(self)
        
        self.alignment_tracker = None
        self.point = None
        self.obj = None
        self.node = None
        self.planetrack = None
        self.alignment = None
        self.temp_group = None
        self.is_activated = False

        DraftTools.Line.Activated(
            self, name=translate('Transportation', 'Alignment')
        )

    def IsActive(self):
        """
        Activation condition requires one alignment be selected
        """

        if self.is_activated:
            return False

        if not App.ActiveDocument:
            return False

        selected = Gui.Selection.getSelection()

        if not selected:
            return False

        if not selected[0].Proxy.Type == 'HorizontalAlignment':
            return False

        self.alignment = selected[0]

        return True

    def GetResources(self):
        """
        Icon resources.
        """

        icon_path = os.path.dirname(resources.__file__) \
            + '/icons/new_alignment.svg'

        return {'Pixmap'  : icon_path,
                'Accel'   : 'Ctrl+Shift+D',
                'MenuText': 'Draft Alignment',
                'ToolTip' : 'Draft a horizontal alignment',
                'CmdType' : 'ForEdit'}

    def Activated(self):
        """
        Command activation method
        """

        if self.is_activated:
            return

        self.is_activated = True

        #DraftTools.Line.Activated(
        #    self, name=translate('Transportation', 'Alignment')
        #)

        self.temp_group = \
            App.ActiveDocument.addObject('App::DocumentObjectGroup', 'Temp')

        wire = Draft.makeWire(self.alignment.Points)

        self.temp_group.addObject(wire)

        if not self.alignment_tracker:
            self.alignment_tracker = AlignmentTracker()

        self.alignment.ViewObject.LineColor = (0.5, 0.5, 0.5)
        self.alignment.ViewObject.DrawStyle = u'Dashed'

        panel = DraftAlignmentTask(self.clean_up)

        Gui.Control.showDialog(panel)
        #panel.setup()

    def select_curve_edges(self, edge_name):
        """
        Given an edge name, find the curve to which it belongs
        and the adjacent edges
        """

        curve_dict = self.alignment.Proxy.get_edges()

        for _k, _v in curve_dict.items():

            if _v.get(edge_name):

                Gui.Selection.addSelection(self.alignment, list(_v.keys()))

    def action(self, arg):
        """
        Event handling for alignment drawing
        """

        #trap the escape key to quit
        if arg['Type'] == 'SoKeyboardEvent':
            if arg['Key'] == 'ESCAPE':
                self.finish()
                return

        #trap mouse movement
        if arg['Type'] == 'SoLocation2Event':

            p = Gui.ActiveDocument.ActiveView.getCursorPos()
            point = Gui.ActiveDocument.ActiveView.getPoint(p)
            info = Gui.ActiveDocument.ActiveView.getObjectInfo(p)

            if info:
                if 'Edge' in info['Component']:
                    self.select_curve_edges(info['Component'])

        #    self.alignment_tracker.update(self.node + [self.point])

            DraftTools.redraw3DView()

            return

        #trap button clicks
        if arg['Type'] == 'SoMouseButtonEvent':

            if (arg['State'] == 'DOWN') and (arg['Button'] == 'BUTTON1'):

                if arg['Position'] == self.pos:
                    self.finish(False, cont=True)
                    return

                #first point
                if not (self.node or self.support):

                    DraftTools.getSupport(arg)

                    self.point, ctrl_point, info = \
                        DraftTools.getPoint(self, arg, noTracker=True)

                if self.point:

                    self.ui.redraw()
                    self.node.append(self.point)
                    self.draw_update(self.point)

                    if not self.isWire and len(self.node) == 2:
                        self.finish(False, cont=True)

    def undo_last(self):
        """
        Undo the last segment
        """

        if len(self.node) > 1:

            self.node.pop()
            self.alignment_tracker.update(self.node)
            self.obj.Shape = self.update_shape(self.node)
            print(translate('Transporation', 'Undo last point'))

    def draw_update(self, point):
        """
        Update the geometry as it has been defined
        """

        if len(self.node) == 1:

            self.alignment_tracker.on()

            #if self.planetrack:
            #    self.planetrack.set(self.node[0])

            #print(translate('Transportation', 'Pick next  point:\n'))

            return

        print(type(self.obj.Shape))
        #res = self.update_shape(self.node)
        print(type(res))
        #self.obj.Shape = self.update_shape(self.node)

        print(
            translate(
                'Transportation',
                'Pick next point, finish (Shift+f), or close (o):'
            ) + '\n'
        )

    def update_shape(self, points):
        """
        Generates the shape to be rendered during the creation process
        """

        #return Draft.makeWire(points).Shape

    def clean_up(self):
        """
        Callback to finish the command
        """

        print('cleanup!')
        self.finish()

        return True

    def finish(self, closed=False, cont=False):
        """
        Finish drawing the alignment object
        """

        #finalize tracking
        if self.ui:
            if hasattr(self, 'alignment_tracker'):
                self.alignment_tracker.finalize()

        #close the open dialog
        if not Draft.getParam('UiMode', 1):
            Gui.Control.closeDialog()

        #remove temporary object
        #if self.obj:
        #    old = self.obj.Name
        #    todo.delay(App.ActiveDocument.removeObject, old)

        #if self.node:
        #    if len(self.node) > 1:
        #        try:
        #            rot, sup, pts, fil = self.getStrings()
        #            Gui.addModule('Draft')
        #            self.commit(
        #                translate('Transportation', 'Create Test'),
        #                ['points = ' + pts,
        #                'fn = Draft.makeWire(points)',
        #                'Draft.autogroup(fn)'
        #                ]
        #            )

        #        except:
        #            print('Draft: error delatying commit')

        DraftTools.Creator.finish(self)

        #if self.ui:
        #    if self.ui.continueMode:
        #        self.Activated()

        if self.alignment:
            self.alignment.ViewObject.LineColor = (0.0, 0.0, 0.0)
            self.alignment.ViewObject.DrawStyle = u'Solid'

        if self.temp_group:
            if self.temp_group.OutList:
                for _geo in self.temp_group.OutList:
                    self.temp_group.removeObject(_geo)

            App.ActiveDocument.removeObject(self.temp_group.Name)

        self.is_activated = False

Gui.addCommand('DraftAlignmentCmd', DraftAlignmentCmd())
