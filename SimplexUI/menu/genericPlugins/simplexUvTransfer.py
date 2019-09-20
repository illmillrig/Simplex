# Copyright 2016, Blur Studio
#
# This file is part of Simplex.
#
# Simplex is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Simplex is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Simplex.  If not, see <http://www.gnu.org/licenses/>.

from alembic.Abc import OArchive, IArchive
from alembic.AbcGeom import IXform
from ...commands.uvTransfer import getVertCorrelation, applyTransfer
from ...commands.alembicCommon import getSampleArray, getMesh, buildAbc
from ...commands.mesh import Mesh
from ... import OGAWA

try:
	import numpy as np
except ImportError:
	np = None

def _loadJSString(srcSmpxPath):
	''' Get the json string out of a .smpx file '''
	iarch = IArchive(str(srcSmpxPath))
	top = iarch.getTop()
	par = top.children[0]
	parName = par.getName()
	par = IXform(top, parName)

	systemSchema = par.getSchema()
	props = systemSchema.getUserProperties()
	prop = props.getProperty("simplex")
	jsString = prop.getValue()
	return jsString, parName

def simplexUvTransfer(srcSmpxPath, tarPath, outPath, srcUvPath=None, tol=0.0001, pBar=None):
	""" Transfer a simplex system onto a mesh through UV space

	Parameters
	----------
	srcSmpxPath : str
		The path to the source .smpx file
	tarPath : str
		The path to the mesh to recieve the blendshapes
	outPath : str
		The .smpx path that will be written
	srcUvPath : str
		If the .smpx file doesn't have UV's, then the UV's
		from this mesh wil be used. Defaults to None
	tol : float
		The tolerance for checking if a UV is outside of a poly
	pBar : QProgressDialog
		Optional progress bar

	"""
	if np is None:
		raise RuntimeError("UV Transfer requires Numpy. It is currently unavailable")

	if pBar is not None:
		pBar.setLabelText("Loading Source Mesh")
		from Qt.QtWidgets import QApplication
		QApplication.processEvents()

	srcUvPath = srcUvPath or srcSmpxPath
	if srcUvPath.endswith('.abc') or srcUvPath.endswith('.smpx'):
		src = Mesh.loadAbc(srcUvPath, ensureWinding=False)
	elif srcUvPath.endswith('.obj'):
		src = Mesh.loadObj(srcUvPath, ensureWinding=False)
	srcVerts = getSampleArray(getMesh(srcSmpxPath))

	if pBar is not None:
		pBar.setLabelText("Loading Target Mesh")
		from Qt.QtWidgets import QApplication
		QApplication.processEvents()
	if tarPath.endswith('.abc'):
		tar = Mesh.loadAbc(tarPath, ensureWinding=False)
	elif tarPath.endswith('.obj'):
		tar = Mesh.loadObj(tarPath, ensureWinding=False)

	srcFaces = src.faceVertArray
	srcUvFaces = src.uvFaceMap['default']
	srcUvs = np.array(src.uvMap['default'])

	tarFaces = tar.faceVertArray
	tarUvFaces = tar.uvFaceMap['default']
	tarUvs = np.array(tar.uvMap['default'])
	oldTarVerts = np.array(tar.vertArray)

	corr = getVertCorrelation(srcUvFaces, srcUvs, tarFaces, tarUvFaces, tarUvs, tol=tol, pBar=pBar)
	tarVerts = applyTransfer(srcVerts, srcFaces, corr, len(oldTarVerts))

	# Apply as a delta
	deltas = tarVerts - tarVerts[0][None, ...]
	writeVerts = oldTarVerts[None, ...] + deltas

	jsString, name = _loadJSString(srcSmpxPath)
	oarch = OArchive(str(outPath), OGAWA) # false for HDF5
	buildAbc(
		oarch, writeVerts, tarFaces, uvs=tarUvs, uvFaces=tarUvFaces,
		name=name, shapeSuffix='', propDict=dict(simplex=jsString)
	)


