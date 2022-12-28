''' -----------------------------------------------------------------------------------
    Title:        	God Summoner Mesh Importer
    Description:  	Imports models from God Summoner on the PC
    Release:       	December 27 2022 
    Author:       	mariokart64n
    
    Notes:
    # ------------------------------------------------------------------------------ #
        Unknown data between buffers could cause files to crach due reading in the
        the wrong place.
        normals and other data are unknown in the vertex data, therefore it isn't
        really possible to write models back - Dec 27 2022
        
        When I reviewed this topic in relation to the mesh format there was mention
        of the files being compressed by lzo1x.
            https://forum.xentax.com/viewtopic.php?f=16&t=21385
        
        No samples were provided, but I located some source code on lzo1x decoding.
            https://github.com/ARM-software/u-boot/blob/master/lib/lzo/lzo1x_decompress.c
        
        This other game 'Goddess of Genesis' may also have the same formats,
        but I was unable to secure file samples, links were down.
            https://forum.xentax.com/viewtopic.php?t=22942

    
    Change Log:
    # ------------------------------------------------------------------------------ #
    
    [2022-12-27]
        Wrote it!
    

   ----------------------------------------------------------------------------------- '''



useOpenDialog = True

# ====================================================================================
# MAXCSRIPT FUNCTIONS
# ====================================================================================
# These function are written to mimic native functions in
# maxscript. This is to make porting my old maxscripts
# easier, so alot of these functions may be redundant..
# ====================================================================================
# ChangeLog:
#   2022-12-24
#       fixed bad indents from using pyCharm to format the indents lol... fuuukk
#       additional tweaks to the maxscript module, changed mesh validate
#
#   2022-12-23
#       Code was reformated in pyCharm, added a few more functions;
#       matchpattern, format, hide, unhide, freeze, unfreeze, select
#
#
# ====================================================================================

from pathlib import Path  # Needed for os stuff
import random
import struct  # Needed for Binary Reader
import math
import bpy
import mathutils  # this i'm guessing is a branch of the bpy module specifically for math operations
import os

signed, unsigned = 0, 1  # Enums for read function
seek_set, seek_cur, seek_end = 0, 1, 2  # Enums for seek function
SEEK_ABS, SEEK_REL, SEEK_END = 0, 1, 2  # Enums for seek function
on, off = True, False


def format(text="", args=[]):
    # prints in blender are annoying this is a hack so i don't have to keep explicitly denoting the type
    ns = ""
    i = 0
    if len(text) > 1 and text[len(text) - 1:len(text)] == "\n":
        text = text[0:-1]

    isArr = (type(args).__name__ == "tuple" or type(args).__name__ == "list")

    if isArr == True and len(args) > 0:
        for s in text:
            t = s
            if s == "%":
                if i < len(args):
                    t = str(args[i])
                elif i == 0:
                    t = str(args)
                else:
                    t = ""
                i = i + 1
            ns = ns + t
        print(ns)
    elif text.find("%") > -1:
        for s in text:
            t = s
            if s == "%":
                if i == 0:
                    t = str(args)
                else:
                    t = ""
                i = i + 1
            ns = ns + t
        print(ns)
    else:
        print(text)
    return None


def subString(s, start=0, end=-1, base=1):
    # base is a starting index of 1 as used in maxscript
    start -= base
    if start < 0: start = 0
    if end > -1:
        end += start
    else:
        end = len(s)
    return s[start:end:1]


def matchPattern(s="", pattern="", ignoreCase=True):
    # This is a hack, this does not function the same as in maxscript
    isfound = False
    pattern = pattern.replace('*', '')
    if ignoreCase:
        if s.lower().find(pattern.lower()) != -1: isfound = True
    else:
        if s.find(pattern) != -1: isfound = True
    return isfound


def as_filename(name):  # could reuse for other presets
    # AFAICT is for, as the name suggests storing a filename.
    # Filenames cannot contain certain characters.
    # It doesn't appear to in anyway auto-parse.
    # The Paint Palettes addon uses the subtype for preset file names.
    # The following method is used to parse out illegal / invalid chars.
    for char in " !@#$%^&*(){}:\";'[]<>,.\\/?":
        name = name.replace(char, '_')
    return name.lower().strip()


def rancol4():
    return (random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), 1.0)


def rancol3():
    return (random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0))


def ceil(num):
    n = float(int(num))
    if num > n: n += 1.0
    return n


def cross(vec1=(0.0, 0.0, 0.0), vec2=(0.0, 0.0, 0.0)):
    return (
        vec2[1] * vec1[2] - vec2[2] * vec1[1],
        vec2[2] * vec1[0] - vec2[0] * vec1[2],
        vec2[0] * vec1[1] - vec2[1] * vec1[0]
    )


def dot(a=(0.0, 0.0, 0.0), b=(0.0, 0.0, 0.0)):
    return sum(map(lambda pair: pair[0] * pair[1], zip(a, b)))


def abs(val=0.0):
    # return (-val if val < 0 else val)
    return math.abs(val)


def sqrt(n=0.0, l=0.001):
    # x = n
    # root = 0.0
    # count = 0
    # while True:
    #    count += 1
    #    if x == 0: break
    #    root = 0.5 * (x + (n / x))
    #    if abs(root - x) < l: break
    #    x = root
    # return root
    return math.sqrt(n)


def normalize(vec=(0.0, 0.0, 0.0)):
    div = sqrt((vec[0] * vec[0]) + (vec[1] * vec[1]) + (vec[2] * vec[2]))
    return (
        (vec[0] / div) if vec[0] != 0 else 0.0,
        (vec[1] / div) if vec[1] != 0 else 0.0,
        (vec[2] / div) if vec[2] != 0 else 0.0
    )


def max(val1=0.0, val2=0.0):
    return val1 if val1 > val2 else val2


def distance(vec1=(0.0, 0.0, 0.0), vec2=(0.0, 0.0, 0.0)):
    return (sqrt((pow(vec2[0] - vec1[0], 2)) + (pow(vec2[1] - vec1[1], 2)) + (pow(vec2[2] - vec1[2], 2))))


def radToDeg(radian):
    # return (radian * 57.295779513082320876798154814105170332405472466564)
    return math.degrees(radian)


def degToRad(degree):
    # return (degree * 0.017453292519943295769236907684886127134428718885417)
    return math.radians(degree)


class bit:
    def And(integer1, integer2): return (integer1 & integer2)

    def Or(integer1, integer2): return (integer1 | integer2)

    def Xor(integer1, integer2): return (integer1 ^ integer2)

    def Not(integer1): return (~integer1)

    def Get(integer1, integer2): return ((integer1 & (1 << integer2)) >> integer2)

    def Set(integer1, integer2, boolean): return (
                integer1 ^ ((integer1 * 0 - (int(boolean))) ^ integer1) & ((integer1 * 0 + 1) << integer2))

    def Shift(integer1, integer2): return ((integer1 >> -integer2) if integer2 < 0 else (integer1 << integer2))

    def CharAsInt(string): return ord(str(string))

    def IntAsChar(integer): return chr(int(integer))

    def IntAsHex(integer): return format(integer, 'X')

    def IntAsFloat(integer): return struct.unpack('f', integer.to_bytes(4, byteorder='little'))


def delete(objName):
    select(objName)
    bpy.ops.object.delete(use_global=False)


def delete_all():
    for obj in bpy.context.scene.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    return None


class LayerProperties:
    layer = None

    def __init__(self, name=""):
        self.layer = bpy.data.collections.get(name)

    def addNode(self, obj=None):
        result = False
        if obj != None and self.layer != None:

            # Loop through all collections the obj is linked to
            for col in obj.users_collection:
                # Unlink the object
                col.objects.unlink(obj)

            # Link each object to the target collection
            self.layer.objects.link(obj)
            result = True
        return result


class LayerManager:

    def getLayerFromName(name=""):
        col = bpy.data.collections.get(name)
        result = None
        if col: result = LayerProperties(col.name)
        return result

    def newLayerFromName(name=""):
        col = bpy.data.collections.new(name)
        col.name = name
        bpy.context.scene.collection.children.link(col)
        bpy.context.view_layer.update()
        return LayerProperties(col.name)


class dummy:
    object = None

    def __init__(self, position=(0.0, 0.0, 0.0)):
        self.object = bpy.data.objects.new("Empty", None)
        bpy.context.scene.collection.objects.link(self.object)
        self.object.empty_display_size = 1
        self.object.empty_display_type = 'CUBE'
        self.object.location = position

    def position(self, pos=(0.0, 0.0, 0.0)):
        if self.object != None: self.object.location = pos

    def name(self, name=""):
        if self.object != None and name != "": self.object.name = name

    def showLinks(self, enable=False):
        return enable

    def showLinksOnly(self, enable=False):
        return enable


class matrix3:
    row1 = [1.0, 0.0, 0.0]
    row2 = [0.0, 1.0, 0.0]
    row3 = [0.0, 0.0, 1.0]
    row4 = [0.0, 0.0, 0.0]

    def __init__(self, rowA=[1.0, 0.0, 0.0], rowB=[0.0, 1.0, 0.0], rowC=[0.0, 0.0, 1.0], rowD=[0.0, 0.0, 0.0]):
        if rowA == 0:
            self.row1 = [0.0, 0.0, 0.0]
            self.row2 = [0.0, 0.0, 0.0]
            self.row3 = [0.0, 0.0, 0.0]

        elif rowA == 1:
            self.row1 = [1.0, 0.0, 0.0]
            self.row2 = [0.0, 1.0, 0.0]
            self.row3 = [0.0, 0.0, 1.0]
            self.row4 = [0.0, 0.0, 0.0]
        else:
            self.row1 = rowA
            self.row2 = rowB
            self.row3 = rowC
            self.row4 = rowD

    def __repr__(self):
        return (
                "matrix3([" + str(self.row1[0]) +
                ", " + str(self.row1[1]) +
                ", " + str(self.row1[2]) +
                "], [" + str(self.row2[0]) +
                ", " + str(self.row2[1]) +
                ", " + str(self.row2[2]) +
                "], [" + str(self.row3[0]) +
                ", " + str(self.row3[1]) +
                ", " + str(self.row3[2]) +
                "], [" + str(self.row4[0]) +
                ", " + str(self.row4[1]) +
                ", " + str(self.row4[2]) + "])"
        )

    def setPosition(self, vec=[0.0, 0.0, 0.0]):
        self.row4 = [vec[0], vec[1], vec[2]]
        return None

    def position(self):
        return self.row4

    def asMat3(self):
        return (
            (self.row1[0], self.row1[1], self.row1[2]),
            (self.row2[0], self.row2[1], self.row2[2]),
            (self.row3[0], self.row3[1], self.row3[2]),
            (self.row4[0], self.row4[1], self.row4[2])
        )

    def asMat4(self):
        return (
            (self.row1[0], self.row1[1], self.row1[2], 0.0),
            (self.row2[0], self.row2[1], self.row2[2], 0.0),
            (self.row3[0], self.row3[1], self.row3[2], 0.0),
            (self.row4[0], self.row4[1], self.row4[2], 1.0)
        )

    def asQuat(self):
        r11 = self.row1[0]
        r12 = self.row1[1]
        r13 = self.row1[2]
        r21 = self.row2[0]
        r22 = self.row2[1]
        r23 = self.row2[2]
        r31 = self.row3[0]
        r32 = self.row3[1]
        r33 = self.row3[2]
        q0 = (r11 + r22 + r33 + 1.0) / 4.0;
        q1 = (r11 - r22 - r33 + 1.0) / 4.0;
        q2 = (-r11 + r22 - r33 + 1.0) / 4.0;
        q3 = (-r11 - r22 + r33 + 1.0) / 4.0;
        if q0 < 0.0: q0 = 0.0
        if q1 < 0.0: q1 = 0.0
        if q2 < 0.0: q2 = 0.0
        if q3 < 0.0: q3 = 0.0
        q0 = sqrt(q0)
        q1 = sqrt(q1)
        q2 = sqrt(q2)
        q3 = sqrt(q3)
        if q0 >= q1 and q0 >= q2 and q0 >= q3:
            q0 *= 1.0
            q1 = q1 * 1.0 if (r32 - r23) >= 0.0 else q1 * -1.0
            q2 = q2 * 1.0 if (r13 - r31) >= 0.0 else q2 * -1.0
            q3 = q3 * 1.0 if (r21 - r12) >= 0.0 else q3 * -1.0
        elif q1 >= q0 and q1 >= q2 and q1 >= q3:
            q0 = q0 * 1.0 if (r32 - r23) >= 0.0 else q0 * -1.0
            q1 *= 1.0
            q2 = q2 * 1.0 if (r21 + r12) >= 0.0 else q2 * -1.0
            q3 = q3 * 1.0 if (r13 + r31) >= 0.0 else q3 * -1.0
        elif q2 >= q0 and q2 >= q1 and q2 >= q3:
            q0 = q0 * 1.0 if (r13 - r31) >= 0.0 else q0 * -1.0
            q1 = q1 * 1.0 if (r21 + r12) >= 0.0 else q1 * -1.0
            q2 *= 1.0
            q3 = q3 * 1.0 if (r32 + r23) >= 0.0 else q3 * -1.0
        elif q3 >= q0 and q3 >= q1 and q3 >= q2:
            q0 = q0 * 1.0 if (r21 - r12) >= 0.0 else q0 * -1.0
            q1 = q1 * 1.0 if (r31 + r13) >= 0.0 else q1 * -1.0
            q2 = q2 * 1.0 if (r32 + r23) >= 0.0 else q2 * -1.0
            q3 *= 1.0
        else:
            format("error\n")
        r = sqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3)
        q0 /= r
        q1 /= r
        q2 /= r
        q3 /= r
        return [q0, q1, q2, q3]

    def inverse(self):
        row1_3 = 0.0
        row2_3 = 0.0
        row3_3 = 0.0
        row4_3 = 1.0
        inv = [float] * 16
        inv[0] = (self.row2[1] * self.row3[2] * row4_3 -
                  self.row2[1] * row3_3 * self.row4[2] -
                  self.row3[1] * self.row2[2] * row4_3 +
                  self.row3[1] * row2_3 * self.row4[2] +
                  self.row4[1] * self.row2[2] * row3_3 -
                  self.row4[1] * row2_3 * self.row3[2])
        inv[4] = (-self.row2[0] * self.row3[2] * row4_3 +
                  self.row2[0] * row3_3 * self.row4[2] +
                  self.row3[0] * self.row2[2] * row4_3 -
                  self.row3[0] * row2_3 * self.row4[2] -
                  self.row4[0] * self.row2[2] * row3_3 +
                  self.row4[0] * row2_3 * self.row3[2])
        inv[8] = (self.row2[0] * self.row3[1] * row4_3 -
                  self.row2[0] * row3_3 * self.row4[1] -
                  self.row3[0] * self.row2[1] * row4_3 +
                  self.row3[0] * row2_3 * self.row4[1] +
                  self.row4[0] * self.row2[1] * row3_3 -
                  self.row4[0] * row2_3 * self.row3[1])
        inv[12] = (-self.row2[0] * self.row3[1] * self.row4[2] +
                   self.row2[0] * self.row3[2] * self.row4[1] +
                   self.row3[0] * self.row2[1] * self.row4[2] -
                   self.row3[0] * self.row2[2] * self.row4[1] -
                   self.row4[0] * self.row2[1] * self.row3[2] +
                   self.row4[0] * self.row2[2] * self.row3[1])
        inv[1] = (-self.row1[1] * self.row3[2] * row4_3 +
                  self.row1[1] * row3_3 * self.row4[2] +
                  self.row3[1] * self.row1[2] * row4_3 -
                  self.row3[1] * row1_3 * self.row4[2] -
                  self.row4[1] * self.row1[2] * row3_3 +
                  self.row4[1] * row1_3 * self.row3[2])
        inv[5] = (self.row1[0] * self.row3[2] * row4_3 -
                  self.row1[0] * row3_3 * self.row4[2] -
                  self.row3[0] * self.row1[2] * row4_3 +
                  self.row3[0] * row1_3 * self.row4[2] +
                  self.row4[0] * self.row1[2] * row3_3 -
                  self.row4[0] * row1_3 * self.row3[2])
        inv[9] = (-self.row1[0] * self.row3[1] * row4_3 +
                  self.row1[0] * row3_3 * self.row4[1] +
                  self.row3[0] * self.row1[1] * row4_3 -
                  self.row3[0] * row1_3 * self.row4[1] -
                  self.row4[0] * self.row1[1] * row3_3 +
                  self.row4[0] * row1_3 * self.row3[1])
        inv[13] = (self.row1[0] * self.row3[1] * self.row4[2] -
                   self.row1[0] * self.row3[2] * self.row4[1] -
                   self.row3[0] * self.row1[1] * self.row4[2] +
                   self.row3[0] * self.row1[2] * self.row4[1] +
                   self.row4[0] * self.row1[1] * self.row3[2] -
                   self.row4[0] * self.row1[2] * self.row3[1])
        inv[2] = (self.row1[1] * self.row2[2] * row4_3 -
                  self.row1[1] * row2_3 * self.row4[2] -
                  self.row2[1] * self.row1[2] * row4_3 +
                  self.row2[1] * row1_3 * self.row4[2] +
                  self.row4[1] * self.row1[2] * row2_3 -
                  self.row4[1] * row1_3 * self.row2[2])
        inv[6] = (-self.row1[0] * self.row2[2] * row4_3 +
                  self.row1[0] * row2_3 * self.row4[2] +
                  self.row2[0] * self.row1[2] * row4_3 -
                  self.row2[0] * row1_3 * self.row4[2] -
                  self.row4[0] * self.row1[2] * row2_3 +
                  self.row4[0] * row1_3 * self.row2[2])
        inv[10] = (self.row1[0] * self.row2[1] * row4_3 -
                   self.row1[0] * row2_3 * self.row4[1] -
                   self.row2[0] * self.row1[1] * row4_3 +
                   self.row2[0] * row1_3 * self.row4[1] +
                   self.row4[0] * self.row1[1] * row2_3 -
                   self.row4[0] * row1_3 * self.row2[1])
        inv[14] = (-self.row1[0] * self.row2[1] * self.row4[2] +
                   self.row1[0] * self.row2[2] * self.row4[1] +
                   self.row2[0] * self.row1[1] * self.row4[2] -
                   self.row2[0] * self.row1[2] * self.row4[1] -
                   self.row4[0] * self.row1[1] * self.row2[2] +
                   self.row4[0] * self.row1[2] * self.row2[1])
        inv[3] = (-self.row1[1] * self.row2[2] * row3_3 +
                  self.row1[1] * row2_3 * self.row3[2] +
                  self.row2[1] * self.row1[2] * row3_3 -
                  self.row2[1] * row1_3 * self.row3[2] -
                  self.row3[1] * self.row1[2] * row2_3 +
                  self.row3[1] * row1_3 * self.row2[2])
        inv[7] = (self.row1[0] * self.row2[2] * row3_3 -
                  self.row1[0] * row2_3 * self.row3[2] -
                  self.row2[0] * self.row1[2] * row3_3 +
                  self.row2[0] * row1_3 * self.row3[2] +
                  self.row3[0] * self.row1[2] * row2_3 -
                  (self.row3[0] * row1_3 * self.row2[2]))
        inv[11] = (-self.row1[0] * self.row2[1] * row3_3 +
                   self.row1[0] * row2_3 * self.row3[1] +
                   self.row2[0] * self.row1[1] * row3_3 -
                   self.row2[0] * row1_3 * self.row3[1] -
                   self.row3[0] * self.row1[1] * row2_3 +
                   self.row3[0] * row1_3 * self.row2[1])
        inv[15] = (self.row1[0] * self.row2[1] * self.row3[2] -
                   self.row1[0] * self.row2[2] * self.row3[1] -
                   self.row2[0] * self.row1[1] * self.row3[2] +
                   self.row2[0] * self.row1[2] * self.row3[1] +
                   self.row3[0] * self.row1[1] * self.row2[2] -
                   self.row3[0] * self.row1[2] * self.row2[1])
        det = self.row1[0] * inv[0] + self.row1[1] * inv[4] + self.row1[2] * inv[8] + row1_3 * inv[12]
        if det != 0:
            det = 1.0 / det
            return (matrix3(
                [inv[0] * det, inv[1] * det, inv[2] * det],
                [inv[4] * det, inv[5] * det, inv[6] * det],
                [inv[8] * det, inv[9] * det, inv[10] * det],
                [inv[12] * det, inv[13] * det, inv[14] * det]
            ))
        else:
            return matrix3(self.row1, self.row2, self.row3, self.row4)

    def multiply(self, B):
        C = matrix3()
        A_row1_3, A_row2_3, A_row3_3, A_row4_3 = 0.0, 0.0, 0.0, 1.0
        if type(B).__name__ == "matrix3":
            C.row1 = [
                self.row1[0] * B.row1[0] + self.row1[1] * B.row2[0] + self.row1[2] * B.row3[0] + A_row1_3 * B.row4[0],
                self.row1[0] * B.row1[1] + self.row1[1] * B.row2[1] + self.row1[2] * B.row3[1] + A_row1_3 * B.row4[1],
                self.row1[0] * B.row1[2] + self.row1[1] * B.row2[2] + self.row1[2] * B.row3[2] + A_row1_3 * B.row4[2]
            ]
            C.row2 = [
                self.row2[0] * B.row1[0] + self.row2[1] * B.row2[0] + self.row2[2] * B.row3[0] + A_row2_3 * B.row4[0],
                self.row2[0] * B.row1[1] + self.row2[1] * B.row2[1] + self.row2[2] * B.row3[1] + A_row2_3 * B.row4[1],
                self.row2[0] * B.row1[2] + self.row2[1] * B.row2[2] + self.row2[2] * B.row3[2] + A_row2_3 * B.row4[2],
            ]
            C.row3 = [
                self.row3[0] * B.row1[0] + self.row3[1] * B.row2[0] + self.row3[2] * B.row3[0] + A_row3_3 * B.row4[0],
                self.row3[0] * B.row1[1] + self.row3[1] * B.row2[1] + self.row3[2] * B.row3[1] + A_row3_3 * B.row4[1],
                self.row3[0] * B.row1[2] + self.row3[1] * B.row2[2] + self.row3[2] * B.row3[2] + A_row3_3 * B.row4[2]
            ]
            C.row4 = [
                self.row4[0] * B.row1[0] + self.row4[1] * B.row2[0] + self.row4[2] * B.row3[0] + A_row4_3 * B.row4[0],
                self.row4[0] * B.row1[1] + self.row4[1] * B.row2[1] + self.row4[2] * B.row3[1] + A_row4_3 * B.row4[1],
                self.row4[0] * B.row1[2] + self.row4[1] * B.row2[2] + self.row4[2] * B.row3[2] + A_row4_3 * B.row4[2]
            ]
        elif (type(B).__name__ == "tuple" or type(B).__name__ == "list"):
            C.row1 = [
                self.row1[0] * [0][0] + self.row1[1] * [1][0] + self.row1[2] * [2][0] + A_row1_3 * [3][0],
                self.row1[0] * [0][1] + self.row1[1] * [1][1] + self.row1[2] * [2][1] + A_row1_3 * [3][1],
                self.row1[0] * [0][2] + self.row1[1] * [1][2] + self.row1[2] * [2][2] + A_row1_3 * [3][2]
            ]
            C.row2 = [
                self.row2[0] * [0][0] + self.row2[1] * [1][0] + self.row2[2] * [2][0] + A_row2_3 * [3][0],
                self.row2[0] * [0][1] + self.row2[1] * [1][1] + self.row2[2] * [2][1] + A_row2_3 * [3][1],
                self.row2[0] * [0][2] + self.row2[1] * [1][2] + self.row2[2] * [2][2] + A_row2_3 * [3][2],
            ]
            C.row3 = [
                self.row3[0] * [0][0] + self.row3[1] * [1][0] + self.row3[2] * [2][0] + A_row3_3 * [3][0],
                self.row3[0] * [0][1] + self.row3[1] * [1][1] + self.row3[2] * [2][1] + A_row3_3 * [3][1],
                self.row3[0] * [0][2] + self.row3[1] * [1][2] + self.row3[2] * [2][2] + A_row3_3 * [3][2]
            ]
            C.row4 = [
                self.row4[0] * [0][0] + self.row4[1] * [1][0] + self.row4[2] * [2][0] + A_row4_3 * [3][0],
                self.row4[0] * [0][1] + self.row4[1] * [1][1] + self.row4[2] * [2][1] + A_row4_3 * [3][1],
                self.row4[0] * [0][2] + self.row4[1] * [1][2] + self.row4[2] * [2][2] + A_row4_3 * [3][2]
            ]
        return C


def eulerAnglesToMatrix3(rotXangle=0.0, rotYangle=0.0, rotZangle=0.0):
    # https://stackoverflow.com/a/47283530
    cosY = math.cos(rotZangle)
    sinY = math.sin(rotZangle)
    cosP = math.cos(rotYangle)
    sinP = math.sin(rotYangle)
    cosR = math.cos(rotXangle)
    sinR = math.sin(rotXangle)
    m = matrix3(
        [cosP * cosY, cosP * sinY, -sinP],
        [sinR * cosY * sinP - sinY * cosR, cosY * cosR + sinY * sinP * sinR, cosP * sinR],
        [sinY * sinR + cosR * cosY * sinP, cosR * sinY * sinP - sinR * cosY, cosR * cosP],
        [0.0, 0.0, 0.0]
    )
    return m


def transMatrix(t=[0.0, 0.0, 0.0]):
    mat = matrix3(
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (t[0], t[1], t[2])
    )
    return mat


def inverse(mat=matrix3()):
    return mat.inverse()


def quatToMatrix3(q=[0.0, 0.0, 0.0, 0.0]):
    """
        Covert a quaternion into a full three-dimensional rotation matrix.

        Input
        :param Q: A 4 element array representing the quaternion (q0,q1,q2,q3)

        Output
        :return: A 3x3 element matrix representing the full 3D rotation matrix.
                 This rotation matrix converts a point in the local reference
                 frame to a point in the global reference frame.
    """

    sqw = q[3] * q[3]
    sqx = q[0] * q[0]
    sqy = q[1] * q[1]
    sqz = q[2] * q[2]

    # invs (inverse square length) is only required if quaternion is not already normalised
    invs = 1.0
    if (sqx + sqy + sqz + sqw) > 0.0: invs = 1.0 / (sqx + sqy + sqz + sqw)
    m00 = (sqx - sqy - sqz + sqw) * invs  # since sqw + sqx + sqy + sqz =1/invs*invs
    m11 = (-sqx + sqy - sqz + sqw) * invs
    m22 = (-sqx - sqy + sqz + sqw) * invs

    tmp1 = q[0] * q[1]
    tmp2 = q[2] * q[3]
    m10 = 2.0 * (tmp1 + tmp2) * invs
    m01 = 2.0 * (tmp1 - tmp2) * invs

    tmp1 = q[0] * q[2]
    tmp2 = q[1] * q[3]
    m20 = 2.0 * (tmp1 - tmp2) * invs
    m02 = 2.0 * (tmp1 + tmp2) * invs

    tmp1 = q[1] * q[2]
    tmp2 = q[0] * q[3]
    m21 = 2.0 * (tmp1 + tmp2) * invs
    m12 = 2.0 * (tmp1 - tmp2) * invs

    # 3x3 rotation matrix
    mat = matrix3(
        (m00, m10, m20),
        (m01, m11, m21),
        (m02, m12, m22),
        (0.0, 0.0, 0.0)
    )
    return mat


class skinOps:
    mesh = None
    skin = None
    armature = None

    def __init__(self, meshObj, armObj, skinName="Skin"):
        self.mesh = meshObj
        self.armature = armObj
        if self.mesh != None:
            for m in self.mesh.modifiers:
                if m.type == "ARMATURE":
                    self.skin = m
                    break
            if self.skin == None:
                self.skin = self.mesh.modifiers.new(type="ARMATURE", name=skinName)
            self.skin.use_vertex_groups = True
            self.skin.object = self.armature
            self.mesh.parent = self.armature

    def addbone(self, boneName, update_flag=0):
        # Adds a bone to the vertex group list
        # print("boneName:\t%s" % boneName)
        vertGroup = self.mesh.vertex_groups.get(boneName)
        if not vertGroup:
            self.mesh.vertex_groups.new(name=boneName)
        return None

    def NormalizeWeights(self, weight_array, roundTo=0):
        # Makes All weights in the weight_array sum to 1.0
        # Set roundTo 0.01 to limit weight; 0.33333 -> 0.33
        n = []
        if len(weight_array) > 0:
            s = 0.0
            n = [float] * len(weight_array)
            for i in range(0, len(weight_array)):
                if roundTo != 0:
                    n[i] = (float(int(weight_array[i] * (1.0 / roundTo)))) / (1.0 / roundTo)
                else:
                    n[i] = weight_array[i]
                s += n[i]
            s = 1.0 / s
            for i in range(0, len(weight_array)):
                n[i] *= s
        return n

    def GetNumberBones(self):
        # Returns the number of bones present in the vertex group list
        num = 0
        for b in self.armature.data.bones:
            if self.mesh.vertex_groups.get(b.name):
                num += 1
        return num

    def GetNumberVertices(self):
        # Returns the number of vertices for the object the Skin modifier is applied to.
        return len(self.mesh.data.vertices)

    def ReplaceVertexWeights(self, vertex_integer, vertex_bone_array, weight_array):
        # Sets the influence of the specified bone(s) to the specified vertex.
        # Any influence weights for the bone(s) that are not specified are erased.
        # If the bones and weights are specified as arrays, the arrays must be of the same size.

        # Check that both arrays match
        numWeights = len(vertex_bone_array)
        if len(weight_array) == numWeights and numWeights > 0:

            # Erase Any Previous Weight

            # for g in self.mesh.data.vertices[vertex_integer].groups:
            #    self.mesh.vertex_groups[g.index].add([vertex_integer], 0.0, 'REPLACE')

            for g in range(0, len(self.mesh.data.vertices[vertex_integer].groups)):
                self.mesh.vertex_groups[g].add([vertex_integer], 0.0, 'REPLACE')

            # Add New Weights
            for i in range(0, numWeights):
                self.mesh.vertex_groups[vertex_bone_array[i]].add([vertex_integer], weight_array[i], 'REPLACE')
            return True
        return False

    def GetVertexWeightCount(self, vertex_integer):
        # Returns the number of bones (vertex groups) influencing the specified vertex.
        num = 0
        for g in self.mesh.vertices[vertex_integer].groups:
            # need to write more crap
            # basically i need to know if the vertex group is for a bone and is even label as deformable
            # but lzy, me fix l8tr
            num += 1
        return num

    def boneAffectLimit(self, limit):
        # Reduce the number of bone influences affecting a single vertex
        # I copied and pasted busted ass code from somewhere as an example to
        # work from... still need to write this out but personally dont have a
        # need for it
        # for v in self.mesh.vertices:

        #     # Get a list of the non-zero group weightings for the vertex
        #     nonZero = []
        #     for g in v.groups:

        #         g.weight = round(g.weight, 4)

        #         if g.weight & lt; .0001:
        #             continue

        #         nonZero.append(g)

        #     # Sort them by weight decending
        #     byWeight = sorted(nonZero, key=lambda group: group.weight)
        #     byWeight.reverse()

        #     # As long as there are more than 'maxInfluence' bones, take the lowest influence bone
        #     # and distribute the weight to the other bones.
        #     while len(byWeight) & gt; limit:

        #         #print("Distributing weight for vertex %d" % (v.index))

        #         # Pop the lowest influence off and compute how much should go to the other bones.
        #         minInfluence = byWeight.pop()
        #         distributeWeight = minInfluence.weight / len(byWeight)
        #         minInfluence.weight = 0

        #         # Add this amount to the other bones
        #         for influence in byWeight:
        #             influence.weight = influence.weight + distributeWeight

        #         # Round off the remaining values.
        #         for influence in byWeight:
        #             influence.weight = round(influence.weight, 4)
        return None

    def GetVertexWeightBoneID(self, vertex_integer, vertex_bone_integer):
        # Returns the vertex group index of the Nth bone affecting the specified vertex.

        return None

    def GetVertexWeight(self, vertex_integer, vertex_bone_integer):
        # Returns the influence of the Nth bone affecting the specified vertex.
        for v in mesh.data.vertices:  # <MeshVertex>                              https://docs.blender.org/api/current/bpy.types.MeshVertex.html
            weights = [g.weight for g in v.groups]
            boneids = [g.group for g in v.groups]
        # return [vert for vert in bpy.context.object.data.vertices if bpy.context.object.vertex_groups['vertex_group_name'].index in [i.group for i in vert.groups]]
        return [vert for vert in bpy.context.object.data.vertices if
                bpy.context.object.vertex_groups['vertex_group_name'].index in [i.group for i in vert.groups]]

    def GetVertexWeightByBoneName(self, vertex_bone_name):
        return [vert for vert in self.mesh.data.vertices if
                self.mesh.data.vertex_groups[vertex_bone_name].index in [i.group for i in vert.groups]]

    def GetSelectedBone(self):
        # Returns the index of the current selected bone in the Bone list.
        return self.mesh.vertex_groups.active_index

    def GetBoneName(self, bone_index, nameflag_index=0):
        # Returns the bone name or node name of a bone specified by ID.
        name = ""
        try:
            name = self.mesh.vertex_groups[bone_index].name
        except:
            pass
        return name

    def GetListIDByBoneID(self, BoneID_integer):
        # Returns the ListID index given the BoneID index value.
        # The VertexGroupListID index is the index into the name-sorted.
        # The BoneID index is the non-sorted index, and is the index used by other methods that require a bone index.
        index = -1
        try:
            index = self.mesh.vertex_groups[self.armature.data.bones[BoneID_integer]].index
        except:
            pass
        return index

    def GetBoneIDByListID(self, bone_index):
        # Returns the BoneID index given the ListID index value. The ListID index is the index into the name-sorted bone listbox.
        # The BoneID index is the non-sorted index, and is the index used by other methods that require a bone index
        index = -1
        try:
            index = self.armature.data.bones[self.mesh.vertex_groups[bone_index].name].index
        except:
            pass
        return index

    def weightAllVertices(self):
        # Ensure all weights have weight and that are equal to a sum of 1.0
        return None

    def clearZeroWeights(self, limit=0.0):
        # Removes weights that are a threshold
        # for v in self.mesh.vertices:
        #     nonZero = []
        #     for g in v.groups:

        #         g.weight = round(g.weight, 4)

        #         if g.weight & le; limit:
        #             continue

        #         nonZero.append(g)

        #     # Sort them by weight decending
        #     byWeight = sorted(nonZero, key=lambda group: group.weight)
        #     byWeight.reverse()

        #     # As long as there are more than 'maxInfluence' bones, take the lowest influence bone
        #     # and distribute the weight to the other bones.
        #     while len(byWeight) & gt; limit:

        #         #print("Distributing weight for vertex %d" % (v.index))

        #         # Pop the lowest influence off and compute how much should go to the other bones.
        #         minInfluence = byWeight.pop()
        #         distributeWeight = minInfluence.weight / len(byWeight)
        #         minInfluence.weight = 0

        #         # Add this amount to the other bones
        #         for influence in byWeight:
        #             influence.weight = influence.weight + distributeWeight

        #         # Round off the remaining values.
        #         for influence in byWeight:
        #             influence.weight = round(influence.weight, 4)
        return None

    def SelectBone(self, bone_integer):
        # Selects the specified bone in the Vertex Group List
        self.mesh.vertex_groups.active_index = bone_integer
        return None

    # Probably wont bother writing this unless I really need this ability
    def saveEnvelope(self):
        # Saves Weight Data to an external binary file
        return None

    def saveEnvelopeAsASCII(self):
        # Saves Weight Data to an external ASCII file
        envASCII = "ver 3\n"
        envASCII = "numberBones " + str(self.GetNumberBones()) + "\n"
        num = 0
        for b in self.armature.data.bones:
            if self.mesh.vertex_groups.get(b.name):
                envASCII += "[boneName] " + b.name + "\n"
                envASCII += "[boneID] " + str(num) + "\n"
                envASCII += "  boneFlagLock 0\n"
                envASCII += "  boneFlagAbsolute 2\n"
                envASCII += "  boneFlagSpline 0\n"
                envASCII += "  boneFlagSplineClosed 0\n"
                envASCII += "  boneFlagDrawEnveloe 0\n"
                envASCII += "  boneFlagIsOldBone 0\n"
                envASCII += "  boneFlagDead 0\n"
                envASCII += "  boneFalloff 0\n"
                envASCII += "  boneStartPoint 0.000000 0.000000 0.000000\n"
                envASCII += "  boneEndPoint 0.000000 0.000000 0.000000\n"
                envASCII += "  boneCrossSectionCount 2\n"
                envASCII += "    boneCrossSectionInner0 3.750000\n"
                envASCII += "    boneCrossSectionOuter0 13.125000\n"
                envASCII += "    boneCrossSectionU0 0.000000\n"
                envASCII += "    boneCrossSectionInner1 3.750000\n"
                envASCII += "    boneCrossSectionOuter1 13.125000\n"
                envASCII += "    boneCrossSectionU1 1.000000\n"
                num += 1
        envASCII += "[Vertex Data]\n"
        envASCII += "  nodeCount 1\n"
        envASCII += "  [baseNodeName] " + self.mesh.name + "\n"
        envASCII += "    vertexCount " + str(len(self.mesh.vertices)) + "\n"
        for v in self.mesh.vertices:
            envASCII += "    [vertex" + str(v.index) + "]\n"
            envASCII += "      vertexIsModified 0\n"
            envASCII += "      vertexIsRigid 0\n"
            envASCII += "      vertexIsRigidHandle 0\n"
            envASCII += "      vertexIsUnNormalized 0\n"
            envASCII += "      vertexLocalPosition 0.000000 0.000000 24.38106\n"
            envASCII += "      vertexWeightCount " + str(len(v.groups)) + "\n"
            envASCII += "      vertexWeight "
            for g in v.groups:
                envASCII += str(g.group) + ","
                envASCII += str(g.weight) + " "
            envASCII += "      vertexSplineData 0.000000 0 0 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000   "
        envASCII += "  numberOfExclusinList 0\n"
        return envASCII

    def loadEnvelope(self):
        # Imports Weight Data to an external Binary file
        return None

    def loadEnvelopeAsASCII(self):
        # Imports Weight Data to an external ASCII file
        return None


class boneSys:
    armature = None
    layer = None

    def __init__(self, armatureName="Skeleton", layerName="", rootName="Scene Root"):

        # Clear Any Object Selections
        # for o in bpy.context.selected_objects: o.select = False
        bpy.context.view_layer.objects.active = None

        # Get Collection (Layers)
        if self.layer == None:
            if layerName != "":
                # make collection
                self.layer = bpy.data.collections.new(layerName)
                bpy.context.scene.collection.children.link(self.layer)
            else:
                self.layer = bpy.data.collections[0]

        # Check for Armature
        armName = armatureName
        if armatureName == "": armName = "Skeleton"
        self.armature = bpy.context.scene.objects.get(armName)

        if self.armature == None:
            # Create Root Bone
            root = bpy.data.armatures.new(rootName)
            root.name = rootName

            # Create Armature
            self.armature = bpy.data.objects.new(armName, root)
            self.layer.objects.link(self.armature)

        self.armature.display_type = 'WIRE'
        self.armature.show_in_front = True

    def editMode(self, enable=True):
        #
        # Data Pointers Seem to get arranged between
        # Entering and Exiting EDIT Mode, which is
        # Required to make changes to the bones
        #
        # This needs to be called beofre and after making changes
        #

        if enable:
            # Clear Any Object Selections
            bpy.context.view_layer.objects.active = None

            # Set Armature As Active Selection
            if bpy.context.view_layer.objects.active != self.armature:
                bpy.context.view_layer.objects.active = self.armature

            # Switch to Edit Mode
            if bpy.context.object.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        else:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        return None

    def count(self):
        return len(self.armature.data.bones)

    def getNodeByName(self, boneName):
        # self.editMode(True)
        node = None
        try:
            # node = self.armature.data.bones.get('boneName')
            node = self.armature.data.edit_bones[boneName]
        except:
            pass
        # self.editMode(False)
        return node

    def getChildren(self, boneName):
        childs = []
        b = self.getNodeByName(boneName)
        if b != None:
            for bone in self.armature.data.edit_bones:
                if bone.parent == b: childs.append(bone)
        return childs

    def setParent(self, boneName, parentName):
        b = self.getNodeByName(boneName)
        p = self.getNodeByName(parentName)
        if b != None and p != None:
            b.parent = p
            return True
        return False

    def getParent(self, boneName):
        par = None
        b = self.getNodeByName(boneName)
        if b != None: par = b.parent
        return par

    def getPosition(self, boneName):
        position = (0.0, 0.0, 0.0)
        b = self.getNodeByName(boneName)
        if b != None:
            position = (
                self.armature.location[0] + b.head[0],
                self.armature.location[1] + b.head[1],
                self.armature.location[2] + b.head[2],
            )
        return position

    def setPosition(self, boneName, position):
        b = self.getNodeByName(boneName)
        pos = (
            position[0] - self.armature.location[0],
            position[1] - self.armature.location[1],
            position[2] - self.armature.location[2]
        )
        if b != None and distance(b.tail, pos) > 0.0000001: b.head = pos
        return None

    def getEndPosition(self, boneName):
        position = (0.0, 0.0, 0.0)
        b = self.getNodeByName(boneName)
        if b != None:
            position = (
                self.armature.location[0] + b.tail[0],
                self.armature.location[1] + b.tail[1],
                self.armature.location[2] + b.tail[2],
            )
        return position

    def setEndPosition(self, boneName, position):
        b = self.getNodeByName(boneName)
        pos = (
            position[0] - self.armature.location[0],
            position[1] - self.armature.location[1],
            position[2] - self.armature.location[2]
        )
        if b != None and distance(b.head, pos) > 0.0000001: b.tail = pos
        return None

    def setUserProp(self, boneName, key_string, value):
        b = self.getNodeByName(boneName)
        try:
            if b != None: b[key_string] = value
            return True
        except:
            return False

    def getUserProp(self, boneName, key_string):
        value = None
        b = self.getNodeByName(boneName)
        if b != None:
            try:
                value = b[key_string]
            except:
                pass
        return value

    def setTransform(self, boneName, matrix=((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (1.0, 0.0, 0.0, 1.0))):
        b = self.getNodeByName(boneName)
        if b != None:
            b.matrix = matrix
            return True
        return False

    def getTransform(self, boneName):
        # lol wtf does blender not store a transform for the bone???
        mat = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (1.0, 0.0, 0.0, 1.0))
        b = self.getNodeByName(boneName)
        if b != None:
            mat = (
                (b.matrix[0][0], b.matrix[0][1], b.matrix[0][2], 0.0),
                (b.matrix[1][0], b.matrix[1][1], b.matrix[1][2], 0.0),
                (b.matrix[2][0], b.matrix[2][1], b.matrix[2][2], 0.0),
                (b.head[0] - self.armature.location[0],
                 b.head[1] - self.armature.location[1],
                 b.head[2] - self.armature.location[2], 1.0)
            )
        return mat

    def setVisibility(self, boneName, visSet=(
            True, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False,
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False)):
        # Assign Visible Layers
        b = self.getNodeByName(boneName)
        if b != None:
            b.layers = visSet
            return True
        return False

    def setBoneGroup(self, boneName, normalCol=(0.0, 0.0, 0.0), selctCol=(0.0, 0.0, 0.0), activeCol=(0.0, 0.0, 0.0)):
        # Create Bone Group (custom bone colours ??)
        b = self.getNodeByName(boneName)
        if b != None:
            # arm = bpy.data.objects.new("Armature", bpy.data.armatures.new("Skeleton"))
            # layer.objects.link(arm)
            # obj.parent = arm
            # bgrp = self.armature.pose.bone_groups.new(name=msh.name)
            # bgrp.color_set = 'CUSTOM'
            # bgrp.colors.normal = normalCol
            # bgrp.colors.select = selctCol
            # bgrp.colors.active = activeCol
            # for b in obj.vertex_groups.keys():
            #    self.armature.pose.bones[b].bone_group = bgrp
            return True
        return False

    def createBone(self, boneName="", startPos=(0.0, 0.0, 0.0), endPos=(0.0, 0.0, 1.0), zAxis=(1.0, 0.0, 0.0)):

        self.editMode(True)

        # Check if bone exists
        b = None
        if boneName != "":
            try:
                b = self.armature.data.edit_bones[boneName]
                return False
            except:
                pass

        if b == None:

            # Generate Bone Name
            bName = boneName
            if bName == "": bName = "Bone_" + '{:04d}'.format(len(self.armature.data.edit_bones))

            # Create Bone
            b = self.armature.data.edit_bones.new(bName)
            # b = self.armature.data.edit_bones.new(bName.decode('utf-8', 'replace'))
            b.name = bName

            # Set As Deform Bone
            b.use_deform = True

            # Set Rotation
            roll, pitch, yaw = 0.0, 0.0, 0.0
            try:
                roll = math.acos((dot(zAxis, (1, 0, 0))) / (
                        math.sqrt(((pow(zAxis[0], 2)) + (pow(zAxis[1], 2)) + (pow(zAxis[2], 2)))) * 1.0))
            except:
                pass
            try:
                pitch = math.acos((dot(zAxis, (0, 1, 0))) / (
                        math.sqrt(((pow(zAxis[0], 2)) + (pow(zAxis[1], 2)) + (pow(zAxis[2], 2)))) * 1.0))
            except:
                pass
            try:
                yaw = math.acos((dot(zAxis, (0, 0, 1))) / (
                        math.sqrt(((pow(zAxis[0], 2)) + (pow(zAxis[1], 2)) + (pow(zAxis[2], 2)))) * 1.0))
            except:
                pass

            su = math.sin(roll)
            cu = math.cos(roll)
            sv = math.sin(pitch)
            cv = math.cos(pitch)
            sw = math.sin(yaw)
            cw = math.cos(yaw)

            b.matrix = (
                (cv * cw, su * sv * cw - cu * sw, su * sw + cu * sv * cw, 0.0),
                (cv * sw, cu * cw + su * sv * sw, cu * sv * sw - su * cw, 0.0),
                (-sv, su * cv, cu * cv, 0.0),
                (startPos[0], startPos[1], startPos[2], 1.0)
            )

            # Set Length (has to be larger then 0.1?)
            b.length = 1.0
            if startPos != endPos:
                b.head = startPos
                b.tail = endPos

        # Exit Edit Mode
        self.editMode(False)
        return True

    def rebuildEndPositions(self, mscale=1.0):
        for b in self.armature.data.edit_bones:
            children = self.getChildren(b.name)
            if len(children) == 1:  # Only One Child, Link End to the Child
                self.setEndPosition(b.name, self.getPosition(children[0].name))
            elif len(children) > 1:  # Multiple Children, Link End to the Average Position of all Children
                childPosAvg = [0.0, 0.0, 0.0]
                for c in children:
                    childPos = self.getPosition(c.name)
                    childPosAvg[0] += childPos[0]
                    childPosAvg[1] += childPos[1]
                    childPosAvg[2] += childPos[2]
                self.setEndPosition(b.name,
                                    (childPosAvg[0] / len(children),
                                     childPosAvg[1] / len(children),
                                     childPosAvg[2] / len(children))
                                    )
            elif b.parent != None:  # No Children use inverse of parent position
                childPos = self.getPosition(b.name)
                parPos = self.getPosition(b.parent.name)

                boneLength = distance(parPos, childPos)
                boneLength = 0.04 * mscale
                boneNorm = normalize(
                    (childPos[0] - parPos[0],
                     childPos[1] - parPos[1],
                     childPos[2] - parPos[2])
                )

                self.setEndPosition(b.name,
                                    (childPos[0] + boneLength * boneNorm[0],
                                     childPos[1] + boneLength * boneNorm[1],
                                     childPos[2] + boneLength * boneNorm[2])
                                    )
        return None


def messageBox(message="", title="Message Box", icon='INFO'):
    def draw(self, context): self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
    return None


def getNodeByName(nodeName):
    return bpy.context.scene.objects.get(nodeName)


def hide(nodeObj=None):
    if nodeObj != None:
        nodeObj.hide_set(True)
        nodeObj.hide_render = True
        return True
    return False


def unhide(nodeObj=None):
    if nodeObj != None:
        nodeObj.hide_set(False)
        nodeObj.hide_render = False
        return True
    return False


def select(nodeObj=None):
    if nodeObj != None:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        nodeObj.select_set(True)
        bpy.context.view_layer.objects.active = nodeObj
        return True
    return False


def selectmore(nodeObj=None):
    if nodeObj != None:
        nodeObj.select_set(True)
        bpy.context.view_layer.objects.active = nodeObj
        return True
    return False


def freeze(nodeObj=None):
    if nodeObj != None:
        nodeObj.hide_select(True)
        return True
    return False


def unfreeze(nodeObj=None):
    if nodeObj != None:
        nodeObj.hide_select(False)
        return True
    return False


def classof(nodeObj):
    try:
        return str(nodeObj.type)
    except:
        return None


def makeDir(folderName):
    return Path(folderName).mkdir(parents=True, exist_ok=True)


def setUserProp(node, key_string, value):
    try:
        node[key_string] = value
        return True
    except:
        return False


def getUserProp(node, key_string):
    value = None
    try:
        value = node[key_string]
    except:
        pass
    return value


def getFileSize(filename):
    return Path(filename).stat().st_size


def doesFileExist(filename):
    file = Path(filename)
    if file.is_file():
        return True
    elif file.is_dir():
        return True
    else:
        return False


def clearListener(len=64):
    for i in range(0, len): print('')


def getFiles(filepath=""):
    files = []

    fpath = '.'
    pattern = "*.*"

    # try to split the pattern from the path
    index = filepath.rfind('/')
    if index < 0: index = filepath.rfind('\\')
    if index > -1:
        fpath = filepath[0:index + 1]
        pattern = filepath[index + 1:]

    # print("fpath:\t%s" % fpath)
    # print("pattern:\t%s" % pattern)

    currentDirectory = Path(fpath)
    for currentFile in currentDirectory.glob(pattern):
        files.append(currentFile)

    return files


def filenameFromPath(file):  # returns: "myImage.jpg"
    return Path(file).name


def getFilenamePath(file):  # returns: "g:\subdir1\subdir2\"
    return (str(Path(file).resolve().parent) + "\\")


def getFilenameFile(file):  # returns: "myImage"
    return Path(file).stem


def getFilenameType(file):  # returns: ".jpg"
    return Path(file).suffix


def toUpper(string):
    return string.upper()


def toLower(string):
    return string.upper()


def padString(string, length=2, padChar="0", toLeft=True):
    s = str(string)
    if len(s) > length:
        s = s[0:length]
    else:
        p = ""
        for i in range(0, length): p += padChar
        if toLeft:
            s = p + s
            s = s[len(s) - length: length + 1]
        else:
            s = s + p
            s = s[0: length]
    return s


def filterString(string, string_search):
    for s in enumerate(string_search):
        string.replace(s[1], string_search[0])
    return string.split(string_search[0])


def findString(string="", token_string=""):
    return string.find(token_string)


def findItem(array, value):
    index = -1
    try:
        index = array.index(value)
    except:
        pass
    return index


def append(array, value):
    array.append(value)
    return None


def appendIfUnique(array, value):
    try:
        array.index(value)
    except:
        array.append(value)
    return None


class StandardMaterial:
    data = None
    bsdf = None

    maxWidth = 1024
    nodeHeight = 512
    nodeWidth = 256
    nodePos = [0.0, 256.0]

    def __init__(self, name="Material"):
        # make material
        self.nodePos[0] -= self.nodeWidth
        self.data = bpy.data.materials.new(name=name)
        self.data.use_nodes = True
        self.data.use_backface_culling = True
        self.bsdf = self.data.node_tree.nodes["Principled BSDF"]
        self.bsdf.label = "Standard"
        pass

    def addNodeArea(self, nodeObj):
        nodeObj.location.x = self.nodePos[0]
        nodeObj.location.y = self.nodePos[1]
        self.nodePos[0] -= self.nodeWidth
        if nodeObj.dimensions[1] > self.nodeHeight: self.nodeHeight = nodeObj.dimensions[1]
        if -nodeObj.location.x > self.maxWidth:
            self.nodePos[0] = -self.nodeWidth
            self.nodePos[1] -= self.nodeHeight

    def add(self, node_type):
        nodeObj = self.data.node_tree.nodes.new(node_type)
        self.addNodeArea(nodeObj)
        return nodeObj

    def attach(self, node_out, node_in):
        self.data.node_tree.links.new(node_in, node_out)
        return None

    def detach(self, node_con):
        self.data.node_tree.links.remove(node_con.links[0])
        return None

    def AddColor(self, name="", colour=(0.0, 0.0, 0.0, 0.0)):
        rgbaColor = self.data.node_tree.nodes.new('ShaderNodeRGB')
        self.addNodeArea(rgbaColor)
        if name != "":
            rgbaColor.label = name
        rgbaColor.outputs[0].default_value = (colour[0], colour[1], colour[2], colour[3])
        if self.bsdf != None and self.bsdf.inputs['Base Color'] == None:
            self.data.node_tree.links.new(self.bsdf.inputs['Base Color'], rgbaColor.outputs['Color'])
        return rgbaColor

    def Bitmaptexture(self, filename="", alpha=False, name="ShaderNodeTexImage"):
        imageTex = self.data.node_tree.nodes.new('ShaderNodeTexImage')
        imageTex.label = name
        self.addNodeArea(imageTex)
        try:
            imageTex.image = bpy.data.images.load(
                filepath=filename,
                check_existing=False
            )
            imageTex.image.name = filenameFromPath(filename)
            imageTex.image.colorspace_settings.name = 'sRGB'
            if not alpha:
                imageTex.image.alpha_mode = 'NONE'
            else:
                imageTex.image.alpha_mode = 'STRAIGHT'  # PREMUL
        except:
            imageTex.image = bpy.data.images.new(
                name=filename,
                width=8,
                height=8,
                alpha=False,
                float_buffer=False
            )
        return imageTex

    def diffuseMap(self, imageTex=None, alpha=False, name="ShaderNodeTexImage"):
        imageMap = None
        if imageTex != None and self.bsdf != None:
            imageMap = self.Bitmaptexture(filename=imageTex, alpha=alpha, name=name)
            self.data.node_tree.links.new(self.bsdf.inputs['Base Color'], imageMap.outputs['Color'])
        return imageMap

    def opacityMap(self, imageTex=None, name="ShaderNodeTexImage"):
        imageMap = None
        if imageTex != None and self.bsdf != None:
            self.data.blend_method = 'BLEND'
            self.data.shadow_method = 'HASHED'
            self.data.show_transparent_back = False
            imageMap = self.Bitmaptexture(filename=imageTex, alpha=True, name=name)
            self.data.node_tree.links.new(self.bsdf.inputs['Alpha'], imageMap.outputs['Alpha'])
        return imageMap

    def normalMap(self, imageTex=None, alpha=False, name="ShaderNodeTexImage"):
        imageMap = None
        if imageTex != None and self.bsdf != None:
            imageMap = self.Bitmaptexture(filename=imageTex, alpha=alpha, name=name)
            imageMap.image.colorspace_settings.name = 'Linear'
            normMap = self.add('ShaderNodeNormalMap')
            normMap.label = 'ShaderNodeNormalMap'
            self.attach(imageMap.outputs['Color'], normMap.inputs['Color'])
            self.attach(normMap.outputs['Normal'], self.bsdf.inputs['Normal'])
        return imageMap

    def specularMap(self, imageTex=None, invert=True, alpha=False, name="ShaderNodeTexImage"):
        imageMap = None
        if imageTex != None and self.bsdf != None:
            imageMap = self.Bitmaptexture(filename=imageTex, alpha=True, name=name)
            if invert:
                invertRGB = self.add('ShaderNodeInvert')
                invertRGB.label = 'ShaderNodeInvert'
                self.data.node_tree.links.new(invertRGB.inputs['Color'], imageMap.outputs['Color'])
                self.data.node_tree.links.new(self.bsdf.inputs['Roughness'], invertRGB.outputs['Color'])
            else:
                self.data.node_tree.links.new(self.bsdf.inputs['Roughness'], imageMap.outputs['Color'])
        return imageMap

    def pack_nodes_partition(self, array, begin, end):
        pivot = begin
        for i in range(begin + 1, end + 1):
            if array[i].dimensions[1] >= array[begin].dimensions[1]:
                pivot += 1
                array[i], array[pivot] = array[pivot], array[i]
        array[pivot], array[begin] = array[begin], array[pivot]
        return pivot

    def pack_nodes_qsort(self, array, begin=0, end=None):
        if end is None:
            end = len(array) - 1

        def _quicksort(array, begin, end):
            if begin >= end:
                return
            pivot = self.pack_nodes_partition(array, begin, end)
            _quicksort(array, begin, pivot - 1)
            _quicksort(array, pivot + 1, end)

        return _quicksort(array, begin, end)

    def pack_nodes(self, boxes=[], areaRatio=0.95, padding=0.0):
        # https://observablehq.com/@mourner/simple-rectangle-packing
        bArea = 0
        maxWidth = 0
        for i in range(0, len(boxes)):
            bArea += (boxes[i].dimensions.x + padding) * (boxes[i].dimensions.y + padding)
            maxWidth = max(maxWidth, (boxes[i].dimensions.x + padding))

        self.pack_nodes_qsort(boxes)
        startWidth = max(ceil(sqrt(bArea / areaRatio)), maxWidth)
        spaces = [[0, 0, 0, startWidth, startWidth * 2]]
        last = []
        for i in range(0, len(boxes)):
            for p in range(len(spaces) - 1, -1, -1):
                if (boxes[i].dimensions.x + padding) > spaces[p][3] or (boxes[i].dimensions.y + padding) > spaces[p][
                    4]: continue
                boxes[i].location.x = spaces[p][0] - (boxes[i].dimensions.x + padding)
                boxes[i].location.y = spaces[p][1] + (boxes[i].dimensions.y + padding)
                if (boxes[i].dimensions.x + padding) == spaces[p][3] and (boxes[i].dimensions.y + padding) == spaces[p][
                    4]:
                    last = spaces.pop()
                    if p < spaces.count: spaces[p] = last
                elif (boxes[i].dimensions.y + padding) == spaces[p][4]:
                    spaces[p][0] += (boxes[i].dimensions.x + padding)
                    spaces[p][3] -= (boxes[i].dimensions.x + padding)
                elif (boxes[i].dimensions.x + padding) == spaces[p][3]:
                    spaces[p][1] += (boxes[i].dimensions.y + padding)
                    spaces[p][4] -= (boxes[i].dimensions.y + padding)
                else:
                    spaces.append([
                        spaces[p][0] - (boxes[i].dimensions.x + padding),
                        spaces[p][1],
                        0.0,
                        spaces[p][3] - (boxes[i].dimensions.x + padding),
                        (boxes[i].dimensions.y + padding)
                    ])
                    spaces[p][1] += (boxes[i].dimensions.y + padding)
                    spaces[p][4] -= (boxes[i].dimensions.y + padding)
                break
        return None

    def sort(self):
        self.pack_nodes([n for n in self.data.node_tree.nodes if n.type != 'OUTPUT_MATERIAL'], 0.45, -10)
        for n in self.data.node_tree.nodes:
            # print("%s\t%i\t%i\t%s" % (n.dimensions, n.width, n.height, n.name))
            n.update()
        return None


def MultiMaterial(numsubs=1):
    # this is a hack, blender doesn't have a multi material equelevent
    mats = []
    if numsubs > 0:
        numMats = len(bpy.data.materials)
        for i in range(0, numsubs):
            mats.append(StandardMaterial("Material #" + str(numMats)))
    return mats


class fopen:
    little_endian = True
    file = ""
    mode = 'rb'
    data = bytearray()
    size = 0
    pos = 0
    isGood = False

    def __init__(self, filename=None, mode='rb', isLittleEndian=True):
        if mode == 'rb':
            if filename != None and Path(filename).is_file():
                self.data = open(filename, mode).read()
                self.size = len(self.data)
                self.pos = 0
                self.mode = mode
                self.file = filename
                self.little_endian = isLittleEndian
                self.isGood = True
        else:
            self.file = filename
            self.mode = mode
            self.data = bytearray()
            self.pos = 0
            self.size = 0
            self.little_endian = isLittleEndian
            self.isGood = False

        pass

    # def __del__(self):
    #    self.flush()

    def resize(self, dataSize=0):
        if dataSize > 0:
            self.data = bytearray(dataSize)
        else:
            self.data = bytearray()
        self.pos = 0
        self.size = dataSize
        self.isGood = False
        return None

    def flush(self):
        print("flush")
        print("file:\t%s" % self.file)
        print("isGood:\t%s" % self.isGood)
        print("size:\t%s" % len(self.data))
        if self.file != "" and not self.isGood and len(self.data) > 0:
            self.isGood = True

            s = open(self.file, 'w+b')
            s.write(self.data)
            s.close()

    def read_and_unpack(self, unpack, size):
        '''
          Charactor, Byte-order
          @,         native, native
          =,         native, standard
          <,         little endian
          >,         big endian
          !,         network

          Format, C-type,         Python-type, Size[byte]
          c,      char,           byte,        1
          b,      signed char,    integer,     1
          B,      unsigned char,  integer,     1
          h,      short,          integer,     2
          H,      unsigned short, integer,     2
          i,      int,            integer,     4
          I,      unsigned int,   integer,     4
          f,      float,          float,       4
          d,      double,         float,       8
        '''
        value = 0
        if self.size > 0 and self.pos + size <= self.size:
            value = struct.unpack_from(unpack, self.data, self.pos)[0]
            self.pos += size
        return value

    def pack_and_write(self, pack, size, value):
        if self.pos + size > self.size:
            self.data.extend(b'\x00' * ((self.pos + size) - self.size))
            self.size = self.pos + size
        try:
            struct.pack_into(pack, self.data, self.pos, value)
        except:
            # print('Pos:\t%i / %i (buf:%i) [val:%i:%i:%s]' % (self.pos, self.size, len(self.data), value, size, pack))
            pass
        self.pos += size
        return None

    def set_pointer(self, offset):
        self.pos = offset
        return None

    def set_endian(self, isLittle=True):
        self.little_endian = isLittle
        return isLittle


def fclose(bitStream=fopen()):
    bitStream.flush()
    bitStream.isGood = False


def fseek(bitStream=fopen(), offset=0, dir=0):
    if dir == 0:
        bitStream.set_pointer(offset)
    elif dir == 1:
        bitStream.set_pointer(bitStream.pos + offset)
    elif dir == 2:
        bitStream.set_pointer(bitStream.pos - offset)
    return None


def ftell(bitStream=fopen()):
    return bitStream.pos


def readByte(bitStream=fopen(), isSigned=0):
    fmt = 'b' if isSigned == 0 else 'B'
    return (bitStream.read_and_unpack(fmt, 1))


def readShort(bitStream=fopen(), isSigned=0):
    fmt = '>' if not bitStream.little_endian else '<'
    fmt += 'h' if isSigned == 0 else 'H'
    return (bitStream.read_and_unpack(fmt, 2))


def readLong(bitStream=fopen(), isSigned=0):
    fmt = '>' if not bitStream.little_endian else '<'
    fmt += 'i' if isSigned == 0 else 'I'
    return (bitStream.read_and_unpack(fmt, 4))


def readLongLong(bitStream=fopen(), isSigned=0):
    fmt = '>' if not bitStream.little_endian else '<'
    fmt += 'q' if isSigned == 0 else 'Q'
    return (bitStream.read_and_unpack(fmt, 8))


def readFloat(bitStream=fopen()):
    fmt = '>f' if not bitStream.little_endian else '<f'
    return (bitStream.read_and_unpack(fmt, 4))


def readDouble(bitStream=fopen()):
    fmt = '>d' if not bitStream.little_endian else '<d'
    return (bitStream.read_and_unpack(fmt, 8))


def readHalf(bitStream=fopen()):
    uint16 = bitStream.read_and_unpack('>H' if not bitStream.little_endian else '<H', 2)
    uint32 = (
            (((uint16 & 0x03FF) << 0x0D) | ((((uint16 & 0x7C00) >> 0x0A) + 0x70) << 0x17)) |
            (((uint16 >> 0x0F) & 0x00000001) << 0x1F)
        )
    return struct.unpack('f', struct.pack('I', uint32))[0]


def readString(bitStream=fopen(), length=0):
    string = ''
    pos = bitStream.pos
    lim = length if length != 0 else bitStream.size - bitStream.pos
    for i in range(0, lim):
        b = bitStream.read_and_unpack('B', 1)
        if b != 0:
            string += chr(b)
        else:
            if length > 0:
                bitStream.set_pointer(pos + length)
            break
    return string


def writeByte(bitStream=fopen(), value=0):
    bitStream.pack_and_write('B', 1, int(value))
    return None


def writeShort(bitStream=fopen(), value=0):
    fmt = '>H' if not bitStream.little_endian else '<H'
    bitStream.pack_and_write(fmt, 2, int(value))
    return None


def writeLong(bitStream=fopen(), value=0):
    fmt = '>I' if not bitStream.little_endian else '<I'
    bitStream.pack_and_write(fmt, 4, int(value))
    return None


def writeFloat(bitStream=fopen(), value=0.0):
    fmt = '>f' if not bitStream.little_endian else '<f'
    bitStream.pack_and_write(fmt, 4, value)
    return None


def writeLongLong(bitStream=fopen(), value=0):
    fmt = '>Q' if not bitStream.little_endian else '<Q'
    bitStream.pack_and_write(fmt, 8, value)
    return None


def writeDoube(bitStream=fopen(), value=0.0):
    fmt = '>d' if not bitStream.little_endian else '<d'
    bitStream.pack_and_write(fmt, 8, value)
    return None

def writeHalf(bitStream=fopen(), value=0.0):
    # https://galfar.vevb.net/wp/2011/16bit-half-float-in-pascaldelphi/

    result = 0
    Src = int(struct.pack("f", value))

    # Extract sign, exponentonent, and mantissa from Single number
    Sign = Src << 31
    exponent = ((Src & 0x7F800000) << 23) - 127 + 15
    Mantissa = Src & 0x007FFFFF
    if exponent >= 0 and exponent <= 30:
        # Simple case - round the significand and combine it with the sign and exponentonent
        result = (Sign >> 15) | ((exponent >> 10) | ((Mantissa + 0x00001000) << 13))

    else:
        if Src == 0:
            # Input float is zero - return zero
            result = 0

        else:
            # Difficult case - lengthy conversion
            if exponent <= 0:
                if exponent <= -10:
                    # Input float's value is less than HalfMin, return zero
                    result = 0

                else:
                    # Float is a normalized Single whose magnitude is less than HalfNormMin.
                    # We convert it to denormalized half.
                    Mantissa = (Mantissa | 0x00800000) << (1 - exponent)
                    # Round to nearest
                    if (Mantissa | 0x00001000) >= 0:
                        Mantissa = Mantissa + 0x00002000
                    # Assemble Sign and Mantissa (exponent is zero to get denormalized number)
                    result = (Sign >> 15) | (Mantissa << 13)


            else:
                if exponent == 255 - 127 + 15:
                    if Mantissa == 0:
                        # Input float is infinity, create infinity half with original sign
                        result = (Sign >> 15) or 0x7C00

                    else:
                        # Input float is NaN, create half NaN with original sign and mantissa
                        result = (Sign >> 15) | (0x7C00 | (Mantissa << 13))


                else:
                    # exponent is > 0 so input float is normalized Single
                    # Round to nearest
                    if (Mantissa & 0x00001000) >= 0:
                        Mantissa = Mantissa + 0x00002000
                        if (Mantissa & 0x00800000) >= 0:
                            Mantissa = 0
                            exponent = exponent + 1

                    if exponent >= 30:
                        # exponentonent overflow - return infinity half
                        result = (Sign >> 15) | 0x7C00

                    else:
                        # Assemble normalized half
                        result = (Sign >> 15) | ((exponent >> 10) | (Mantissa << 13))
    self.writeShort(bitStream, result, unsigned)
    return None


def writeString(bitStream=fopen(), string="", length=0):
    strLen = len(string)
    if length == 0: length = strLen + 1
    for i in range(0, length):
        if i < strLen:
            bitStream.pack_and_write('b', 1, ord(string[i]))
        else:
            bitStream.pack_and_write('B', 1, 0)
    return None


def mesh_validate(vertices=[], faces=[]):
    # basic face index check
    # blender will crash if the mesh data is bad

    # Check an Array was given
    result = (type(faces).__name__ == "tuple" or type(faces).__name__ == "list")
    if result == True:

        # Check the the array is Not empty
        if len(faces) > 0:

            # check that the face is a vector
            if (type(faces[0]).__name__ == "tuple" or type(faces[0]).__name__ == "list"):

                # Calculate the Max face index from supplied vertices
                face_min = 0
                face_max = len(vertices) - 1

                # Check face indeices
                for face in faces:
                    for side in face:

                        # Check face index is in range
                        if side < face_min and side > face_max:
                            print("MeshValidation: \tFace Index Out of Range:\t[%i / %i]" % (side, face_max))
                            result = False
                            break
            else:
                print("MeshValidation: \tFace In Array is Invalid")
                result = False
        else:
            print("MeshValidation: \tFace Array is Empty")
    else:
        print("MeshValidation: \tArray Invalid")
        result = False
    return result


def mesh(
        vertices=[],
        faces=[],
        materialIDs=[],
        tverts=[],
        normals=[],
        colours=[],
        materials=[],
        mscale=1.0,
        flipAxis=False,
        obj_name="Object",
        lay_name='',
        position=(0.0, 0.0, 0.0)
):
    #
    # This function is pretty, ugly
    # imports the mesh into blender
    #
    # Clear Any Object Selections
    # for o in bpy.context.selected_objects: o.select = False
    bpy.context.view_layer.objects.active = None

    # Get Collection (Layers)
    if lay_name != '':
        # make collection
        layer = bpy.data.collections.get(lay_name)
        if layer == None:
            layer = bpy.data.collections.new(lay_name)
            bpy.context.scene.collection.children.link(layer)
    else:
        if len(bpy.data.collections) == 0:
            layer = bpy.data.collections.new("Collection")
            bpy.context.scene.collection.children.link(layer)
        else:
            try:
                layer = bpy.data.collections[bpy.context.view_layer.active_layer_collection.name]
            except:
                layer = bpy.data.collections[0]

    # make mesh
    msh = bpy.data.meshes.new('Mesh')

    # msh.name = msh.name.replace(".", "_")

    # Apply vertex scaling
    # mscale *= bpy.context.scene.unit_settings.scale_length
    vertArray = []
    if len(vertices) > 0:
        vertArray = [[float] * 3] * len(vertices)
        if flipAxis:
            for v in range(0, len(vertices)):
                vertArray[v] = (
                    vertices[v][0] * mscale,
                    -vertices[v][2] * mscale,
                    vertices[v][1] * mscale
                )
        else:
            for v in range(0, len(vertices)):
                vertArray[v] = (
                    vertices[v][0] * mscale,
                    vertices[v][1] * mscale,
                    vertices[v][2] * mscale
                )

    # assign data from arrays
    if not mesh_validate(vertArray, faces):
        # Erase Mesh
        msh.user_clear()
        bpy.data.meshes.remove(msh)
        print("Mesh Deleted!")
        return None

    msh.from_pydata(vertArray, [], faces)

    # set surface to smooth
    msh.polygons.foreach_set("use_smooth", [True] * len(msh.polygons))

    # Set Normals
    if len(faces) > 0:
        if len(normals) > 0:
            msh.use_auto_smooth = True
            if len(normals) == (len(faces) * 3):
                msh.normals_split_custom_set(normals)
            else:
                normArray = [[float] * 3] * (len(faces) * 3)
                if flipAxis:
                    for i in range(0, len(faces)):
                        for v in range(0, 3):
                            normArray[(i * 3) + v] = (
                                [normals[faces[i][v]][0],
                                 -normals[faces[i][v]][2],
                                 normals[faces[i][v]][1]]
                            )
                else:
                    for i in range(0, len(faces)):
                        for v in range(0, 3):
                            normArray[(i * 3) + v] = (
                                [normals[faces[i][v]][0],
                                 normals[faces[i][v]][1],
                                 normals[faces[i][v]][2]]
                            )
                msh.normals_split_custom_set(normArray)

        # create texture corrdinates
        # print("tverts ", len(tverts))
        # this is just a hack, i just add all the UVs into the same space <<<
        if len(tverts) > 0:
            uvw = msh.uv_layers.new()
            # if len(tverts) == (len(faces) * 3):
            #    for v in range(0, len(faces) * 3):
            #        msh.uv_layers[uvw.name].data[v].uv = tverts[v]
            # else:
            uvwArray = [[float] * 2] * len(tverts[0])
            for i in range(0, len(tverts[0])):
                uvwArray[i] = [0.0, 0.0]

            for v in range(0, len(tverts[0])):
                for i in range(0, len(tverts)):
                    uvwArray[v][0] += tverts[i][v][0]
                    uvwArray[v][1] += 1.0 - tverts[i][v][1]

            for i in range(0, len(faces)):
                for v in range(0, 3):
                    msh.uv_layers[uvw.name].data[(i * 3) + v].uv = (
                        uvwArray[faces[i][v]][0],
                        uvwArray[faces[i][v]][1]
                    )

        # create vertex colours
        if len(colours) > 0:
            col = msh.vertex_colors.new()
            if len(colours) == (len(faces) * 3):
                for v in range(0, len(faces) * 3):
                    msh.vertex_colors[col.name].data[v].color = colours[v]
            else:
                colArray = [[float] * 4] * (len(faces) * 3)
                for i in range(0, len(faces)):
                    for v in range(0, 3):
                        msh.vertex_colors[col.name].data[(i * 3) + v].color = colours[faces[i][v]]
        else:
            # Use colours to make a random display
            col = msh.vertex_colors.new()
            random_col = rancol4()
            for v in range(0, len(faces) * 3):
                msh.vertex_colors[col.name].data[v].color = random_col

    # Create Face Maps?
    # msh.face_maps.new()

    # Check mesh is Valid
    # Without this blender may crash!!! lulz
    # However the check will throw false positives so
    # an additional or a replacement valatiation function
    # would be required

    if msh.validate(clean_customdata=False):
        print("Warning, Blender Deleted (" + obj_name + "), reason unspecified, likely empty")

    # Update Mesh
    msh.update()

    # Assign Mesh to Object
    obj = bpy.data.objects.new(obj_name, msh)
    obj.location = position
    # obj.name = obj.name.replace(".", "_")

    for i in range(0, len(materials)):
        if len(obj.material_slots) < (i + 1):
            # if there is no slot then we append to create the slot and assign
            if type(materials[i]).__name__ == 'StandardMaterial':
                obj.data.materials.append(materials[i].data)
            else:
                obj.data.materials.append(materials[i])
        else:
            # we always want the material in slot[0]
            if type(materials[i]).__name__ == 'StandardMaterial':
                obj.material_slots[0].material = materials[i].data
            else:
                obj.material_slots[0].material = materials[i]
        # obj.active_material = obj.material_slots[i].material

    if len(materialIDs) == len(obj.data.polygons):
        for i in range(0, len(materialIDs)):
            obj.data.polygons[i].material_index = materialIDs[i]
            if materialIDs[i] > len(materialIDs):
                materialIDs[i] = materialIDs[i] % len(materialIDs)

    elif len(materialIDs) > 0:
        print("Error:\tMaterial Index Out of Range")

    # obj.data.materials.append(material)
    layer.objects.link(obj)

    # Generate a Material
    # img_name = "Test.jpg"  # dummy texture
    # mat_count = len(texmaps)

    # if mat_count == 0 and len(materialIDs) > 0:
    #    for i in range(0, len(materialIDs)):
    #        if (materialIDs[i] + 1) > mat_count: mat_count = materialIDs[i] + 1

    # Assign Material ID's
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.context.tool_settings.mesh_select_mode = [False, False, True]

    bpy.ops.object.mode_set(mode='OBJECT')
    # materialIDs

    # Redraw Entire Scene
    # bpy.context.scene.update()

    return obj


def rancol4():
    return (random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), 1.0)


def rancol3():
    return (random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0))


def deleteScene(include=[]):
    if len(include) > 0:
        # Exit and Interactions
        if bpy.context.view_layer.objects.active != None:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Select All
        bpy.ops.object.select_all(action='SELECT')

        # Loop Through Each Selection
        for o in bpy.context.view_layer.objects.selected:
            for t in include:
                if o.type == t:
                    bpy.data.objects.remove(o, do_unlink=True)
                    break

        # De-Select All
        bpy.ops.object.select_all(action='DESELECT')
    return None


class fmtSM2_Bone:  # 36 Bytes or:32 bytes if in the SKIN file
    '''char[4]'''
    name = ""

    '''float[3]'''
    position = [0.0, 0.0, 0.0]

    '''float[3]'''
    rotation = [0.0, 0.0, 0.0, 0.0]

    '''uint16_t'''
    unk006 = 0  # Always 1?

    '''uint16_t'''
    unk007 = 0  # always 2928? flag?

    # for SKIN file
    '''uint16_t'''
    boneid = -1

    '''float[16]'''
    matrix = matrix3()

    def asMat4x3(self):
        # ((self.matrix[0][0] + self.matrix[0][3], self.matrix[0][1] + self.matrix[0][3], self.matrix[0][2] + self.matrix[0][3]), (self.matrix[1][0] + self.matrix[1][3], self.matrix[1][1] + self.matrix[1][3], self.matrix[1][2] + self.matrix[1][3]), (self.matrix[2][0] + self.matrix[2][3], self.matrix[2][1] + self.matrix[2][3], self.matrix[2][2] + self.matrix[2][3]), (self.matrix[3][0] * self.matrix[3][3], self.matrix[3][1] * self.matrix[3][3], self.matrix[3][2] * self.matrix[3][3]))
        return self.matrix

    def read(self, f=fopen(), type=0):
        if type == 0x00534D32:
            self.name = ""
            for i in range(0, 4):
                b = readByte(f, unsigned)
                if b > 0: self.name += bit.IntAsChar(b)

            self.position = [readFloat(f), readFloat(f), readFloat(f)]
            self.rotation = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
            self.unk006 = readShort(f, unsigned)
            self.unk007 = readShort(f, unsigned)

            # patch to SKI2
            self.boneid = -1
            m = quatToMatrix3(self.rotation)
            self.matrix = matrix3(
                [m.row1[0], m.row1[1], m.row1[2], 0.0],
                [m.row2[0], m.row2[1], m.row2[2], 0.0],
                [m.row3[0], m.row3[1], m.row3[2], 0.0],
                [self.position[0], self.position[1], self.position[2], 1.0]
            )


        elif type == 0x534B4932:
            self.boneid = readShort(f, unsigned)
            m = ([readHalf(f), readHalf(f), readHalf(f), readHalf(f)],
                 [readHalf(f), readHalf(f), readHalf(f), readHalf(f)],
                 [readHalf(f), readHalf(f), readHalf(f), readHalf(f)],
                 [readHalf(f), readHalf(f), readHalf(f), readHalf(f)])
            self.matrix = matrix3(
                [m[0][0] + m[0][3], m[0][1] + m[0][3], m[0][2] + m[0][3]],
                [m[1][0] + m[1][3], m[1][1] + m[1][3], m[1][2] + m[1][3]],
                [m[2][0] + m[2][3], m[2][1] + m[2][3], m[2][2] + m[2][3]],
                [m[3][0] * m[3][3], m[3][1] * m[3][3], m[3][2] * m[3][3]],
            )
            # Patch to SM file
            self.name = "Bone " + str(self.boneid)
            self.position = self.matrix.position()
            r = self.asMat4x3()
            self.rotation = r.asQuat()
        return None

    def write(self, s=fopen(), type=0):
        if type == 0x00534D32:
            self.name_len = len(self.name)
            for i in range(0, 4):
                b = 0
                if i < self.name_len: b = bit.CharAsInt(subString(self.name, i, 1))
                writeByte(s, b, unsigned)

            for i in range(0, 3): writeFloat(s, self.position[i])
            writeFloat(s, self.rotation[0])
            writeFloat(s, self.rotation[1])
            writeFloat(s, self.rotation[2])
            writeFloat(s, self.rotation[3])
            writeShort(s, self.unk006, unsigned)
            writeShort(s, self.unk007, unsigned)

        elif type == 0x534B4932:
            writeShort(s, self.boneid, unsigned)
            m = self.matrix.asMat4()
            for i in range(0, 4):
                for j in range(0, 4):
                    writeHalf(s, m[i][j])
        return None


class fmtSKEL_Hierarchy:  # 12 Bytes
    '''uint32_t'''
    index = -1

    '''uint32_t'''
    parent = -1

    '''uint32_t'''
    unk017 = 0

    def read(self, f=fopen()):
        self.index = readLong(f, signed)
        self.parent = readLong(f, signed)
        self.unk017 = readLong(f, signed)
        return None

    def write(self, s=fopen()):
        writeLong(s, self.index, signed)
        writeLong(s, self.parent, signed)
        writeLong(s, self.unk017, signed)
        return None


class fmtSKEL:  # 24 Bytes + n Bytes:bone info
    '''char[4]'''
    type = ""

    '''uint16_t'''
    unk010 = 0

    '''uint32_t'''
    unk011 = 0

    '''float'''
    unk012 = 0

    '''uint32_t'''
    num_bones = 0

    '''string[n]'''
    names = []

    '''uint32_t'''
    unk013 = 0

    '''uint32_t'''
    unk014 = 0

    '''Hierarchy[n]'''
    parents = []

    def name(self, index=-1):
        n = ""
        if index > -1:
            for i in range(0, len(self.parents)):
                if index == self.parents[i].index and i < len(self.names):
                    n = self.names[i]
                    break
        return n

    def parent(self, index=-1):
        par = -1
        if index > -1:
            for i in self.parents:
                if index == i.index:
                    par = i.parent
                    break
        return par

    def size(self):
        nsize = 32 + len(self.parents) * 12
        return nsize

    def readFixedString(self, f=fopen(), len=0):
        s, p = "", ftell(f) + len
        for i in range(0, len):
            b = readByte(f, unsigned)
            if b == 0: break
            s += bit.IntAsChar(b)
        fseek(f, p, seek_set)
        return s

    def read(self, f=fopen()):
        self.type = ""
        for i in range(0, 5):
            b = readShort(f, unsigned)
            if b > 0: self.type += bit.IntAsChar(b)
        if self.type == "SKEL":
            self.unk010 = readShort(f, unsigned)
            self.unk011 = readLong(f, unsigned)
            self.unk012 = readFloat(f)
            self.num_bones = readLong(f, unsigned)
            self.names = []
            self.parents = []
            format("self.num_bones: \t%\n", (self.num_bones))
            if self.num_bones > 0:
                self.names = [str] * self.num_bones
                self.parents = [fmtSKEL_Hierarchy] * self.num_bones
                for i in range(0, self.num_bones):
                    self.names[i] = self.readFixedString(f, readLong(f, unsigned))

                self.unk013 = readLong(f, unsigned)
                self.unk014 = readLong(f, unsigned)
                for i in range(0, self.num_bones):
                    self.parents[i] = fmtSKEL_Hierarchy()
                    self.parents[i].read(f)
        else:
            format("Error: \tInvalid File Type {%}\n", (self.type))
        return None

    def write(self, s=fopen()):
        writeShort(s, 0x53, unsigned)
        writeShort(s, 0x4B, unsigned)
        writeShort(s, 0x45, unsigned)
        writeShort(s, 0x4C, unsigned)
        writeShort(s, 0x00, unsigned)
        writeShort(s, self.unk010, unsigned)
        writeLong(s, self.unk011, unsigned)
        writeFloat(s, self.unk012)
        self.num_bones = len(self.parents)
        writeLong(s, self.num_bones, unsigned)
        for i in range(0, self.num_bones):
            if i < len(self.names):
                writeLong(s, len(self.names[i]) + 1, unsigned)
                writeString(s, self.names[i])
            else:
                writeLong(s, 0, unsigned)
        writeLong(s, self.unk013, unsigned)
        writeLong(s, self.unk014, unsigned)
        for i in range(0, self.num_bones): self.parents[i].write(s)
        return None

    def open(self, file=""):
        result = False
        if file != None and file != "":
            f = fopen(file, "rb")
            if f != None:
                self.read(f)
                fclose(f)
                result = True
            else:
                format("Error: \tFailed to open file {%}\n", (file))
        return result

    def save(self, file=""):
        result = False
        if file != None and file != "":
            s = fopen(file, "wb")
            if s != None:
                self.write(s)
                fclose(s)
                result = True
            else:
                format("Error: \tFailed to save file {%}\n", (file))
        return result


class fmtSM2_Skeleton:  # 4 Bytes + n bytes:Bone Data
    '''uint32_t'''
    num_bones = 0,

    '''Bone[n]'''
    bones = []

    # for SKEL file
    '''fmtSKEL'''
    skel = fmtSKEL()

    def size(self, type=0):
        nsize = 4
        if type == 0x00534D32:
            nsize += len(self.bones) * 36
        elif type == 0x534B4932:
            nsize += len(self.bones) * 32
        return nsize

    def read(self, f=fopen(), type=0):
        self.num_bones = readLong(f, unsigned)
        self.bones = []
        if self.num_bones > 0:
            self.bones = [fmtSM2_Bone] * self.num_bones
            for i in range(0, self.num_bones):
                self.bones[i] = fmtSM2_Bone()
                self.bones[i].read(f, type)
        return None

    def write(self, s=fopen()):
        self.num_bones = len(self.bones)
        writeLong(s, self.num_bones, unsigned)
        for i in range(0, self.num_bones):
            self.bones[i].write(s, type)
        return None


class fmtSM2_FaceBuf:  # 4 Bytes + n bytes:faces indices
    '''uint32_t'''
    num_faces = 0,

    '''uint16_t[3]'''
    faces = []

    def size(self):
        nsize = 4 + len(self.faces) * 3 * 2
        return nsize

    def read(self, f=fopen()):
        result = False
        self.num_faces = readLong(f, unsigned)
        self.faces = []
        if self.num_faces > 0:
            self.faces = [[int] * 3] * self.num_faces
            for i in range(0, self.num_faces):
                self.faces[i] = [readShort(f, unsigned), readShort(f, unsigned), readShort(f, unsigned)]
            result = True
        return result

    def write(self, s=fopen()):
        result = False
        self.num_faces = len(self.faces)
        writeLong(s, self.num_faces, unsigned)
        for i in range(0, self.num_faces):
            for v in range(0, 3): writeShort(s, self.faces[i][v], unsigned)
            result = True
        return result


class fmtSM2_Object:
    '''uint32_t'''
    name_len = 0

    '''char[n]'''
    name = ""

    '''uint16_t'''
    unk003 = 0  # ?? padding ??? insufficient samples to determine

    '''uint32_t'''
    max_index = 0  # same as vertex count from header

    '''uint8_t'''
    unk004 = 0  # ?? padding ??? insufficient samples to determine

    '''float[3]'''
    bb_max = [0.0, 0.0, 0.0]  # same as in header

    '''float[3]'''
    bb_min = [0.0, 0.0, 0.0]  # same as in header

    '''FaceBuf[n]'''
    faceBuf = []  # no count? read until end is reached

    '''uint32_t'''
    unk005 = 0  # ?? padding ??? insufficient samples to determine
    '''
        its unknown how this block terminates, and theres not enough samples to
        investigate..
        I assume that when a 4byte null is reached the read is terminated

        however the padding afterwards seems to vary in sample
    '''
    '''uint32_t'''
    padding = 0

    def size(self):
        nsize = 46 + self.padding + len(self.name)
        for i in range(0, len(self.faceBuf)):
            nsize += self.faceBuf[i].size()
        return nsize

    def seekPastWhiteSpace(self, f=fopen(), len=16):
        '''
            this is a hack to skip and 0's or padding after the face buffer
        '''
        p = ftell(f)
        for i in range(0, len):
            b = readByte(f, unsigned)
            if b > 0 or b == None:
                fseek(f, -1, seek_cur)
                break
        # return number of bytes skipped
        return (ftell(f) - p)

    def read(self, f=fopen(), stopAddr=0):
        self.name_len = readLong(f, unsigned)
        self.name = ""
        for i in range(0, self.name_len):
            b = readByte(f, unsigned)
            if b > 0: self.name += bit.IntAsChar(b)

        self.unk003 = readShort(f, unsigned)
        self.max_index = readLong(f, unsigned)
        self.unk004 = readByte(f, unsigned)
        self.bb_max = [readFloat(f), readFloat(f), readFloat(f)]
        self.bb_min = [readFloat(f), readFloat(f), readFloat(f)]
        self.faceBuf = []
        fb = fmtSM2_FaceBuf()
        while ftell(f) < stopAddr:
            fb = fmtSM2_FaceBuf()
            if not fb.read(f): break
            append(self.faceBuf, fb)

        self.unk005 = readLong(f, unsigned)

        # Unsure how the padding in this area works, skip until a none 0 is reached
        padding = self.seekPastWhiteSpace(f)
        format("padding: \t%:@ %\n", (padding, ftell(f)))
        return None

    def write(self, s=fopen()):
        self.name_len = len(self.name) + 1
        writeLong(s, self.name_len, unsigned)
        writeString(s, self.name)
        writeShort(s, self.unk003, unsigned)
        writeLong(s, self.max_index, unsigned)
        writeByte(s, self.unk004, unsigned)
        for i in range(0, 3): writeFloat(s, self.bb_max[i])
        for i in range(0, 3): writeFloat(s, self.bb_min[i])
        for i in range(0, len(self.faceBuf)): self.faceBuf[i].write(s)
        writeLong(s, 0, unsigned)
        writeLong(s, self.unk005, unsigned)
        for i in range(0, self.padding): writeByte(s, 0, unsigned)
        return None


class fmtSM2_Vertex:  # 20 Bytes
    '''
        I'm unable to decode the normals and what could be also be bi-normals
        writing new geometry back to the file is therefore not possible or advise.
    '''

    '''float[3]'''
    position = [0.0, 0.0, 0.0]

    '''float[2]'''
    texcorrd = [0.0, 0.0, 0.0]

    '''float[4]'''
    weight = [1.0, 0.0, 0.0, 0.0]

    '''uint8_t[4]'''
    normal = [0.0, 0.0, 0.0, 0.0]

    '''uint8_t[4]'''
    boneid = [0, -1, -1, -1]

    '''uint8_t[4]'''
    binormal = [0.0, 0.0, 0.0, 0.0]

    def read(self, f=fopen(), type=0):
        self.position = [readHalf(f), readHalf(f), readHalf(f)]
        w = readHalf(f)
        self.position = [self.position[0] + w, self.position[1] + w, self.position[2] + w]
        self.texcorrd = [readHalf(f), readHalf(f), 0.0]
        if type == 0x00534D32:  # 'SM2' 20 Bytes
            self.normal = [readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned),
                           readByte(f, unsigned)]  # normal?
            self.binormal = [readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned),
                             readByte(f, unsigned)]  # tangent?
        elif type == 0x534B4932:  # 'SKI2' 32 Bytes
            self.weight = [readHalf(f), readHalf(f), readHalf(f), readHalf(f)]  # weight
            self.normal = [readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned),
                           readByte(f, unsigned)]  # normal?
            self.boneid = [readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned),
                           readByte(f, unsigned)]  # boneid
            self.binormal = [readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned),
                             readByte(f, unsigned)]  # tangent?
            # round off the weights, theres some issues with the half float function
            for i in range(0, len(self.weight)): self.weight[i] = float(int(self.weight[i] * 1000)) / 1000.0
        return None

    def write(self, s=fopen()):
        for i in range(0, 3): writeHalf(s, self.position[i])
        self.texcorrd = [self.texcorrd[1], self.texcorrd[1], 0.0]
        for i in range(0, 2): writeHalf(s, self.texcorrd[i])
        #for i in range(0, 4): writeShort(s, self.unk009[i], unsigned)
        return None


class fmtSM2:  # 60 Bytes + n Bytes:Buffers
    '''uint32_t'''
    type = 0x00534D32  # SM2, SKI2

    '''uint32_t'''
    version = 0x0105011B

    '''uint32_t'''
    num_verts = 0

    '''float[3]'''
    bb_min = [0.0, 0.0, 0.0]

    '''float[3]'''
    bb_max = [0.0, 0.0, 0.0]

    '''float'''
    draw_dist = [0.0, 0.0, 0.0]

    '''uint32_t'''
    unk001 = 0  # Padding?

    '''uint32_t'''
    unk002 = 0  # Padding?

    '''uint32_t'''
    verts_addr = 0

    '''uint32_t'''
    meshs_addr = 0

    '''uint32_t'''
    bones_addr = 0

    '''Vertex'''
    verts = []

    '''Object'''
    meshs = fmtSM2_Object()

    '''Skeleton'''
    bones = fmtSM2_Skeleton()

    def size(self, type=0):
        nsize = 52
        if self.type == 0x00534D32:
            nsize += 8 + len(self.verts) * 20 + self.meshs.size() + self.bones.size()
        else:
            nsize += 8 + len(self.verts) * 32 + self.meshs.size() + self.bones.size(self.type)
        return nsize

    def read(self, f=fopen(), skelfile=""):
        fsize = f.size
        result = False
        if fsize > 52:
            self.type = readLong(f, unsigned)
            if self.type == 0x00534D32 or self.type == 0x534B4932:
                self.version = readLong(f, unsigned)
                if self.type == 0x00534D32:
                    self.num_verts = readLong(f, unsigned)

                elif self.type == 0x534B4932:
                    self.num_verts = readShort(f, unsigned)
                    self.verts_addr = readShort(f, unsigned)

                self.bb_min = [readFloat(f), readFloat(f), readFloat(f)]
                self.bb_max = [readFloat(f), readFloat(f), readFloat(f)]
                self.draw_dist = readFloat(f)
                if self.type == 0x00534D32:
                    self.unk001 = readLong(f, unsigned)
                    self.unk002 = readLong(f, unsigned)
                    self.verts_addr = readLong(f, unsigned)

                self.meshs_addr = readLong(f, unsigned)
                self.bones_addr = readLong(f, unsigned)

                self.verts = []
                if self.verts_addr > 0 and self.num_verts > 0:
                    self.verts = [fmtSM2_Vertex] * self.num_verts
                    fseek(f, self.verts_addr, seek_set)
                    for i in range(0, self.num_verts):
                        self.verts[i] = fmtSM2_Vertex()
                        self.verts[i].read(f, self.type)

                if self.type == 0x534B4932: self.meshs_addr = ftell(f)

                self.meshs = []
                if self.meshs_addr > 0 and self.meshs_addr < fsize:
                    fseek(f, self.meshs_addr, seek_set)
                    self.meshs = fmtSM2_Object()
                    self.meshs.read(f, fsize)

                if self.type == 0x534B4932: self.bones_addr = ftell(f)

                self.bones = []
                if self.bones_addr > 0 and self.bones_addr < fsize:
                    fseek(f, self.bones_addr, seek_set)
                    self.bones = fmtSM2_Skeleton()
                    self.bones.read(f, self.type)

                    if self.type == 0x534B4932 and skelfile != None and skelfile != "" and doesFileExist(
                            skelfile) == True:
                        if not self.bones.skel.open(skelfile):
                            format("Warning: \tFailed to locate SKEL file\n")

                result = True
            else:
                format("Error: \tUnsupported File Type:0x\n", (self.type))
        else:
            format("Error: \tInvalid File Size {%}\n", (fsize))
        return result

    def write(self, s=fopen()):
        ptr = 60  # Vertex Buffer Position, Always 60
        self.num_self.verts = len(self.verts)
        writeLong(s, 0x00534D32, unsigned)  # 'SM2'
        writeLong(s, self.version, unsigned)
        writeLong(s, self.num_self.verts, unsigned)
        for i in range(0, 3): writeFloat(s, self.bb_min[i])
        for i in range(0, 3): writeFloat(s, self.bb_max[i])
        writeFloat(s, self.draw_dist)
        writeLong(s, self.unk001, unsigned)
        writeLong(s, self.unk002, unsigned)
        writeLong(s, ptr, unsigned)  # Vertices Address
        ptr += self.num_self.verts * 20
        writeLong(s, ptr, unsigned)  # Objects Address
        ptr += self.meshs.size()
        writeLong(s, ptr, unsigned)  # Bones Address
        for i in range(0, self.num_self.verts): self.verts[i].write(s)
        self.meshs.write(s)
        self.bones.write(s)
        return None

    def build(self, texName="", mscale=0.00254, clear_scene=False, impSkin=True, skelName = "Skeleton", rotOff=(matrix3([-1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]))):

        # ClearScene
        if clear_scene == True: deleteScene(['MESH', 'ARMATURE'])

        # Build Skeleton
        boneNames = []
        boneArray = boneSys(skelName)

        for i in range(0, len(self.bones.bones)):
            bname = self.bones.bones[i].name
            n = self.bones.skel.name(self.bones.bones[i].boneid)
            if n != "": bname = n
            boneArray.createBone(
                bname,
                [self.bones.bones[i].position[0] * mscale, self.bones.bones[i].position[1] * mscale,
                 self.bones.bones[i].position[2] * mscale],
                [self.bones.bones[i].position[0] * mscale, (self.bones.bones[i].position[1] + 60) * mscale,
                 self.bones.bones[i].position[2] * mscale],
                [0, 1, 0]
                )
                
            m = inverse(self.bones.bones[i].asMat4x3())
            m = m.multiply(rotOff)
            k = m.position()
            m.setPosition([-(k[0] * mscale), k[1] * mscale, k[2] * mscale])
            
            
            boneArray.editMode(True)
            # -------------------------- B O N E  E D I T  M O D E  O P E N E D -------------------------- #
            boneArray.setTransform(bname, m.asMat4())
            
            # -------------------------- B O N E  E D I T  M O D E  C L O S E D -------------------------- #
            boneArray.editMode(False)


            append(boneNames, bname)
        
        
        
        boneArray.editMode(True)
        # -------------------------- B O N E  E D I T  M O D E  O P E N E D -------------------------- #
        for i in range(0, len(self.bones.bones)):
            p = self.bones.skel.parent(self.bones.bones[i].boneid)
            if p > -1:
                for j in range(0, len(self.bones.bones)):
                    if self.bones.bones[j].boneid == p:
                        boneArray.setParent(boneNames[i], boneNames[j])
                        break
        
        boneArray.rebuildEndPositions(mscale=mscale)
        
        # -------------------------- B O N E  E D I T  M O D E  C L O S E D -------------------------- #
        boneArray.editMode(False)


        # Build Meshes
        vertArray = []
        tvertArray = []
        
        if len(self.verts) > 0:
            vertArray = [[float] * 3] * self.num_verts
            tvertArray = [[float] * 3] * self.num_verts

            for i in range(0, len(self.verts)):
                vertArray[i] = [self.verts[i].position[0] * mscale, self.verts[i].position[2] * mscale,
                                self.verts[i].position[1] * mscale]
                tvertArray[i] = [self.verts[i].texcorrd[0], self.verts[i].texcorrd[1], 0.0]

        for i in range(0, len(self.meshs.faceBuf)):  # these appear to be Level of Details meshes
            if len(self.meshs.faceBuf[i].faces) == 0: continue
            
            mshName = "Mesh " + str(i)
            if self.meshs.name != "": mshName = self.meshs.name + " (" + str(i) + ")"
            
            mat = StandardMaterial()
            
            if texName != "" and doesFileExist(texName) == True:
                mat.diffuseMap(str(texName))
            
            msh = mesh(
                vertices=vertArray,
                tverts=[tvertArray],
                faces=self.meshs.faceBuf[i].faces,
                obj_name=mshName,
                materials=[mat]
                )
            
            if i > 0: hide(msh)
            
            
            # Import Weights
            if impSkin==True and len(self.bones.bones) > 0:

                weights = []
                boneids = []

                # Create Skin Modifier
                skinMod = skinOps(msh, boneArray.armature)

                # Add self.bones to modifier
                vi = 1
                bu = 0
                for vi in range(0, len(self.bones.bones)):
                    if vi + 1 == len(self.bones.bones): bu = 1
                    skinMod.addbone(boneNames[vi], bu)

                # Get Number of Bones in Skin Modifier
                boneListCount = skinMod.GetNumberBones()

                # Build Bone List Map
                boneMap = []
                nodeName = ""
                if boneListCount > 0:

                    # dimension bone map
                    boneMap = [int] * boneListCount

                    # Search for Bone Id in boneArray:Array with all the self.bones
                    for vi in range(0, boneListCount):
                        # Initialize Bone Map to 1st bone
                        boneMap[vi] = 0

                        # get bone name from skin modifier list
                        nodeName = skinMod.GetBoneName(vi, 0)

                        # search bonearray
                        for fi in range(0, len(self.bones.bones)):
                            # if bone name is found, assign to bone map

                            if boneNames[fi] == nodeName:
                                boneMap[vi] = fi

                # apply weights to skin modifier
                bi = []
                we = []
                for vi in range(0, len(self.verts)):
                    bi = []
                    we = []
                    for fi in range(0, len(self.verts[vi].weight)):
                        if self.verts[vi].weight[fi] > 0.0:
                            x = findItem(boneMap, self.verts[vi].boneid[fi])
                            if x > 0:
                                append(bi, x)
                                append(we, self.verts[vi].weight[fi])
                    if len(we) == 0:
                        we = [1.0]
                        bi = [0]
                    skinMod.ReplaceVertexWeights(vi, bi, we)
        return None


def read (file="", impSkin=True, mscale=0.00254, skelName = ""):
    if file != None and file != "":
        
                
        fext = getFilenameType(file)


        if matchPattern(fext, pattern=".sm") or matchPattern(fext, pattern=".skin"):
            f = fopen(file, "rb")
            if f != None:
                fpath = getFilenamePath(file)
                fname = getFilenameFile(file)
                skel_file = fpath + fname + ".skel"
                mapd_file = fpath + fname + ".dds"
                if not doesFileExist(skel_file):
                    file = ""
                    files = getFiles(fpath + "*.skel")
                    for file in files:
                        skel_file = file
                        break

                if not doesFileExist(mapd_file):
                    file = ""
                    files = getFiles(fpath + "*.dds")
                    for file in files:
                        mapd_file = file
                        break

                sm = fmtSM2()
                sm.read(f, skelfile=skel_file)
                sm.build(mapd_file, impSkin=impSkin, mscale=mscale, skelName=skelName)
                del sm
                fclose(f)
            else:
                format("failed to open file {%}\n", (file))
        else:
            format("file extension not supported {%}\n", (fext))
    return None


def write(sm = fmtSM2(), file=""):
    if file != None and file != "" and sm != None:
        fext = getFilenameType(file)
        if matchPattern(fext, pattern=".sm"):
            s = fopen(file, "wb")
            if s != None:
                sm.write(s)

                fclose(s)
            else: format("failed to save file {%}\n", (file))
        else: format("file extension not supported {%}\n", (fext))
    return None







# Callback when file(s) are selected

def smimp_callback(fpath="", files=[], clearScene=True, armName="Armature", impWeights=False, mscale=0.00254):
    if len(files) > 0 and clearScene: deleteScene(['MESH', 'ARMATURE'])
    for file in files:
        read (fpath + file.name, impSkin=impWeights, mscale=mscale, skelName = armName)
    if len(files) > 0:
        messageBox("Done!")
        return True
    else:
        return False


# Wrapper that Invokes FileSelector to open files from blender
def smimp(reload=False):
    # Un-Register Operator
    if reload and hasattr(bpy.types, "IMPORTHELPER_OT_smimp"):  # print(bpy.ops.importhelper.smimp.idname())

        try:
            bpy.types.TOPBAR_MT_file_import.remove(
                bpy.types.Operator.bl_rna_get_subclass_py('IMPORTHELPER_OT_smimp').menu_func_import)
        except:
            print("Failed to Unregister2")

        try:
            bpy.utils.unregister_class(bpy.types.Operator.bl_rna_get_subclass_py('IMPORTHELPER_OT_smimp'))
        except:
            print("Failed to Unregister1")

    # Define Operator
    class ImportHelper_smimp(bpy.types.Operator):

        # Operator Path
        bl_idname = "importhelper.smimp"
        bl_label = "Select File"

        # Operator Properties
        # filter_glob: bpy.props.StringProperty(default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp', options={'HIDDEN'})
        filter_glob: bpy.props.StringProperty(default='*.sm;*.skin', options={'HIDDEN'}, subtype='FILE_PATH')

        # Variables
        filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # full path of selected item (path+filename)
        filename: bpy.props.StringProperty(subtype="FILE_NAME")  # name of selected item
        directory: bpy.props.StringProperty(subtype="FILE_PATH")  # directory of the selected item
        files: bpy.props.CollectionProperty(
            type=bpy.types.OperatorFileListElement)  # a collection containing all the selected items f filenames

        # Controls
        my_int1: bpy.props.IntProperty(name="Some Integer", description="Tooltip")
        my_float1: bpy.props.FloatProperty(name="Scale", default=0.00254, description="Changes Scale of the imported Mesh")
        # my_float2: bpy.props.FloatProperty(name="Some Float point", default = 0.25, min = -0.25, max = 0.5)
        my_bool1: bpy.props.BoolProperty(name="Clear Scene", default=True, description="Deletes everything in the scene prior to importing")
        #my_bool2: bpy.props.BoolProperty(name="Skeleton", default=False, description="Imports Bones to an Armature")
        my_bool3: bpy.props.BoolProperty(name="Vertex Weights", default=False, description="Builds Vertex Groups")
        #my_bool4: bpy.props.BoolProperty(name="Vertex Normals", default=False, description="Applies Custom Normals")
        #my_bool5: bpy.props.BoolProperty(name="Vertex Colours", default=False, description="Builds Vertex Colours")
        #my_bool6: bpy.props.BoolProperty(name="Guess Parents", default=False, description="Uses algorithm to Guess Bone Parenting")
        #my_bool7: bpy.props.BoolProperty(name="Dump Textures", default=False, description="Writes Textures from a file pair '_tex.bin'")
        my_string1: bpy.props.StringProperty(name="", default="Armature", description="Name of Armature to Import Bones to")


        # Runs when this class OPENS
        def invoke(self, context, event):

            # Retrieve Settings
            try: self.filepath = bpy.types.Scene.smimp_filepath
            except: bpy.types.Scene.smimp_filepath = bpy.props.StringProperty(subtype="FILE_PATH")

            try: self.directory = bpy.types.Scene.smimp_directory
            except: bpy.types.Scene.smimp_directory = bpy.props.StringProperty(subtype="FILE_PATH")

            try: self.my_float1 = bpy.types.Scene.smimp_my_float1
            except: bpy.types.Scene.smimp_my_float1 = bpy.props.FloatProperty(default=0.1)

            try: self.my_bool1 = bpy.types.Scene.smimp_my_bool1
            except: bpy.types.Scene.smimp_my_bool1 = bpy.props.BoolProperty(default=False)
            
            try: self.my_bool3 = bpy.types.Scene.smimp_my_bool3
            except: bpy.types.Scene.smimp_my_bool3 = bpy.props.BoolProperty(default=False)

            try: self.my_string1 = bpy.types.Scene.my_string1
            except: bpy.types.Scene.my_string1 = bpy.props.BoolProperty(default=False)

            # Open File Browser
            # Set Properties of the File Browser
            context.window_manager.fileselect_add(self)
            context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        # Runs when this Window is CANCELLED
        def cancel(self, context):
            print("run bitch")

        # Runs when the class EXITS
        def execute(self, context):

            # Save Settings
            bpy.types.Scene.smimp_filepath = self.filepath
            bpy.types.Scene.smimp_directory = self.directory
            bpy.types.Scene.smimp_my_float1 = self.my_float1
            bpy.types.Scene.smimp_my_bool1 = self.my_bool1
            bpy.types.Scene.smimp_my_bool3 = self.my_bool3
            bpy.types.Scene.smimp_my_string1 = self.my_string1

            # Run Callback
            smimp_callback(
                self.directory,
                self.files,
                self.my_bool1,
                self.my_string1,
                self.my_bool3,
                self.my_float1
                )

            return {"FINISHED"}

            # Window Settings

        def draw(self, context):

            # Set Properties of the File Browser
            # context.space_data.params.use_filter = True
            # context.space_data.params.use_filter_folder=True #to not see folders

            # Configure Layout
            # self.layout.use_property_split = True       # To Enable Align
            # self.layout.use_property_decorate = False   # No animation.

            self.layout.row().label(text="Import Settings")

            self.layout.separator()
            self.layout.row().prop(self, "my_bool1")
            self.layout.row().prop(self, "my_float1")

            box = self.layout.box()
            box.label(text="Include")
            box.prop(self, "my_bool3")
            box = self.layout.box()
            box.label(text="Misc")
            box.label(text="Import Bones To:")
            box.prop(self, "my_string1")

            self.layout.separator()

            col = self.layout.row()
            col.alignment = 'RIGHT'
            col.label(text="  Author:", icon='QUESTION')
            col.alignment = 'LEFT'
            col.label(text="mariokart64n")

            col = self.layout.row()
            col.alignment = 'RIGHT'
            col.label(text="Release:", icon='GRIP')
            col.alignment = 'LEFT'
            col.label(text="Decemeber 27, 2022")

        def menu_func_import(self, context):
            self.layout.operator("importhelper.smimp", text="God Summoner (*.sm, *.skin)")

    # Register Operator
    bpy.utils.register_class(ImportHelper_smimp)
    bpy.types.TOPBAR_MT_file_import.append(ImportHelper_smimp.menu_func_import)

    # Assign Shortcut key
    # bpy.context.window_manager.keyconfigs.active.keymaps["Window"].keymap_items.new('bpy.ops.text.run_script()', 'E', 'PRESS', ctrl=True, shift=False, repeat=False)

    # Call ImportHelper
    bpy.ops.importhelper.smimp('INVOKE_DEFAULT')


# END OF MAIN FUNCTION ##############################################################

clearListener()  # clears out console
if not useOpenDialog:

    deleteScene(['MESH', 'ARMATURE'])
    
    read (
        #"E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\Shinobi Master Senran Kagura New Link\\cos_model\\ne453_model\\ne453_mdl.bum"
        #"E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\Shinobi Master Senran Kagura New Link\\cos_model\\ne453_model\\ne453_mdl.bum"
        "E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\Shinobi Master Senran Kagura New Link\\hair_model\\hr140_model\\hr140_mdl.bum"
        )
    messageBox("Done!")
else: smimp(True)

# bpy.context.scene.unit_settings.system = 'METRIC'

# bpy.context.scene.unit_settings.scale_length = 1.001