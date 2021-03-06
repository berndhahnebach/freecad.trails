# /**********************************************************************
# *                                                                     *
# * Copyright (c) 2019 Hakan Seven <hakanseven12@gmail.com>             *
# *                                                                     *
# * This program is free software; you can redistribute it and/or modify*
# * it under the terms of the GNU Lesser General Public License (LGPL)  *
# * as published by the Free Software Foundation; either version 2 of   *
# * the License, or (at your option) any later version.                 *
# * for detail see the LICENCE text file.                               *
# *                                                                     *
# * This program is distributed in the hope that it will be useful,     *
# * but WITHOUT ANY WARRANTY; without even the implied warranty of      *
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
# * GNU Library General Public License for more details.                *
# *                                                                     *
# * You should have received a copy of the GNU Library General Public   *
# * License along with this program; if not, write to the Free Software *
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
# * USA                                                                 *
# *                                                                     *
# ***********************************************************************

'''
Create a Point Group Object from FPO.
'''

import FreeCAD, FreeCADGui
from pivy import coin
from ...design.project.support import utils
from freecad.trails import ICONPATH
import random



def create(points, name='PointGroup'):
    obj=FreeCAD.ActiveDocument.addObject("App::FeaturePython", name)
    obj.Label = name
    PointGroup(obj)
    obj.Points = points
    ViewProviderPointGroup(obj.ViewObject)


class PointGroup:
    """
    This class is about Point Group Object data features.
    """

    def __init__(self, obj):
        '''
        Set data properties.
        '''

        obj.addProperty(
            "App::PropertyVectorList",
            "Points",
            "Base",
            "List of group points").Points = ()

        obj.Proxy = self
        self.Points = None

    def onChanged(self, fp, prop):
        '''
        Do something when a data property has changed.
        '''

        return

    def execute(self, fp):
        '''
        Do something when doing a recomputation. 
        '''

        return


class ViewProviderPointGroup:
    """
    This class is about Point Group Object view features.
    """

    def __init__(self, obj):
        '''
        Set view properties.
        '''

        (r, g, b) = (random.random(),
                     random.random(),
                     random.random())

        obj.addProperty(
            "App::PropertyColor",
            "PointColor",
            "Point Style",
            "Color of the point group").PointColor = (r, g, b)

        obj.addProperty(
            "App::PropertyFloatConstraint",
            "PointSize",
            "Point Style",
            "Size of the point group").PointSize = (3.0)

        obj.Proxy = self
        obj.PointSize = (3.0, 1.0, 20.0, 1.0)

    def attach(self, obj):
        '''
        Create Object visuals in 3D view.
        '''

        # Get geo system and geo origin.
        geo_system, geo_origin = utils.get_geo(coords=obj.Object.Points[0])

        # Geo coordinates.
        self.geo_coords = coin.SoGeoCoordinate()
        self.geo_coords.geoSystem.setValues(geo_system)
        self.geo_coords.point.values = obj.Object.Points

        # Geo Seperator.
        geo_seperator = coin.SoGeoSeparator()
        geo_seperator.geoSystem.setValues(geo_system)
        geo_seperator.geoCoords.setValue(geo_origin[0], geo_origin[1], geo_origin[2])

        # Point group features.
        points = coin.SoPointSet()
        self.color_mat = coin.SoMaterial()
        self.point_normal = coin.SoNormal()
        self.point_style = coin.SoDrawStyle()
        self.point_style.style = coin.SoDrawStyle.POINTS

        # Highlight for selection.
        highlight = coin.SoType.fromName('SoFCSelection').createInstance()
        highlight.addChild(self.geo_coords)
        highlight.addChild(points)

        # Point group root.
        point_root = geo_seperator
        point_root.addChild(self.point_style)
        point_root.addChild(self.point_normal)
        point_root.addChild(self.color_mat)
        point_root.addChild(highlight)
        obj.addDisplayMode(point_root,"Point")

        # Take features from properties.
        self.onChanged(obj,"PointSize")
        self.onChanged(obj,"PointColor")

    def onChanged(self, vp, prop):
        '''
        Update Object visuals when a view property changed.
        '''

        # vp is view provider.
        if prop == "PointSize":
            size = vp.getPropertyByName("PointSize")
            self.point_style.pointSize = size

        if prop == "PointColor":
            color = vp.getPropertyByName("PointColor")
            self.color_mat.diffuseColor = (color[0],color[1],color[2])

    def updateData(self, fp, prop):
        '''
        Update Object visuals when a data property changed.
        '''

        # fp is feature python.
        if prop == "Points":
            points = fp.getPropertyByName("Points")
            self.geo_coords.point.values = points

    def getDisplayModes(self,obj):
        '''
        Return a list of display modes.
        '''

        modes=[]
        modes.append("Point")

        return modes

    def getDefaultDisplayMode(self):
        '''
        Return the name of the default display mode.
        '''

        return "Point"

    def setDisplayMode(self,mode):
        '''
        Map the display mode defined in attach with those defined in getDisplayModes.
        '''

        return mode

    def getIcon(self):
        '''
        Return object treeview icon.
        '''

        return ICONPATH + '/icons/PointGroup.svg'

    def __getstate__(self):
        '''
        When saving the document this object gets stored using Python's json module.
        '''

        return None
 
    def __setstate__(self,state):
        '''
        When restoring the serialized object from document we have the chance to set some internals here.
        '''

        return None