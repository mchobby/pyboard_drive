#
#    WORK IN PROGRESS
#
# main.py - controlling TFT LCD ILI9341
# Data transfer using 4-line Serial protocol (Series II)
# 16-bit RGB Color (R:5-bit; G:6-bit; B:5-bit)
# About 30Hz monocolor screen refresh
#

import os
import struct
import math

import pyb, micropython
from pyb import SPI, Pin

micropython.alloc_emergency_exception_buf(100)

rate = 42000000

spi = SPI(1, SPI.MASTER, baudrate=rate, polarity=1, phase=1)
csx = Pin('X4', Pin.OUT_PP)    # CSX Pin
dcx = Pin('X5', Pin.OUT_PP)    # D/Cx Pin
rst = Pin('X3', Pin.OUT_PP)    # Reset Pin


# Color definitions.
#     RGB 16-bit Color (R:5-bit; G:6-bit; B:5-bit)
BLACK       = [0,  0,  0 ]        #   0,   0,   0
NAVY        = [0,  0,  15]        #   0,   0, 128
DARKGREEN   = [0,  31, 0 ]        #   0, 128,   0
DARKCYAN    = [0,  31, 15]        #   0, 128, 128
MAROON      = [15, 0,  0 ]        # 128,   0,   0
PURPLE      = [15, 0,  15]        # 128,   0, 128
OLIVE       = [15, 31, 0 ]        # 128, 128,   0
LIGHTGREY   = [23, 47, 23]        # 192, 192, 192
DARKGREY    = [15, 31, 15]        # 128, 128, 128
BLUE        = [0,  0,  31]        #   0,   0, 255
GREEN       = [0,  63, 0 ]        #   0, 255,   0
CYAN        = [0,  63, 31]        #   0, 255, 255
RED         = [31, 0,  0 ]        # 255,   0,   0
MAGENTA     = [31, 0,  31]        # 255,   0, 255
YELLOW      = [31, 63, 0 ]        # 255, 255,   0
WHITE       = [31, 63, 31]        # 255, 255, 255
ORANGE      = [31, 39, 0 ]        # 255, 165,   0
GREENYELLOW = [18, 63, 4 ]        # 173, 255,  47

TFTWIDTH  = 240
TFTHEIGHT = 320

# LCD control registers
NOP        = 0x00
SWRESET    = 0x01    # Software Reset (page 90)
#     LCD Read status registers
RDDID      = 0x04    # Read display identification 24-bit information (page 91)
RDDST      = 0x09    # Read Display Status 32-bit (page 92)
RDDPM      = 0x0A    # Read Display Power Mode 8-bit (page 94)
RDDMADCTL  = 0x0B    # Read Display MADCTL 8-bit (page 95)
RDPIXFMT   = 0x0C    # Read Display Pixel Format 8-bit (page 96)
RDDIM      = 0x0D    # Read Display Image Format 3-bit (page 97)
RDDSM      = 0x0E    # Read Display Signal Mode 8-bit (page 98)
RDDSDR     = 0x0F    # Read Display Self-Diagnostic Result 8-bit (page 99)
RDID1      = 0xDA
RDID2      = 0xDB
RDID3      = 0xDC
RDID4      = 0xDD
#    LCD settings registers:
SLPIN      = 0x10    # Enter Sleep Mode (page 100)
SLPOUT     = 0x11    # Sleep Out (page 101)

PTLON      = 0x12    # Partial Mode ON (page 103)
NORON      = 0x13    # Partial Mode OFF

INVOFF     = 0x20
INVON      = 0x21
GAMMASET   = 0x26
LCDOFF     = 0x28
LCDON      = 0x29

CASET      = 0x2A
PASET      = 0x2B
RAMWR      = 0x2C
RGBSET     = 0x2D
RAMRD      = 0x2E

PTLAR      = 0x30
MADCTL     = 0x36
PIXFMT     = 0x3A    # Pixel Format Set

IFMODE     = 0xB0    # RGB Interface control (page 154)
FRMCTR1    = 0xB1
FRMCTR2    = 0xB2
FRMCTR3    = 0xB3
INVCTR     = 0xB4    # Frame Inversion control (page 161)
PRCTR      = 0xB5    # Blanking porch control (page 162) VFP, VBP, HFP, HBP
DFUNCTR    = 0xB6

PWCTR1     = 0xC0
PWCTR2     = 0xC1
PWCTR3     = 0xC2
PWCTR4     = 0xC3
PWCTR5     = 0xC4
VMCTR1     = 0xC5
VMCTR2     = 0xC7

GMCTRP1    = 0xE0
GMCTRN1    = 0xE1
#PWCTR6     =  0xFC
IFCTL      = 0xF6

def lcd_reset():
    rst.high()              #
    pyb.delay(1)            #
    rst.low()               #    RESET LCD SCREEN
    pyb.delay(1)            #
    rst.high()              #

def lcd_write(word, dc, recv, recvsize=2):
    dcs = ['cmd', 'data']

    DCX = dcs.index(dc) if dc in dcs else None
    fmt = '<B{0}'.format('B' * recvsize)
    csx.low()
    dcx.value(DCX)
    if recv:
        recv = bytearray(1+recvsize)
        data = spi.send_recv(struct.pack(fmt, word), recv=recv)
        csx.high()
        return data
    else:
        spi.send(word)

    csx.high()

def lcd_write_cmd(word, recv=None):
    data = lcd_write(word, 'cmd', recv)
    return data

def lcd_write_data(word):
    lcd_write(word, 'data', recv=None)

def lcd_write_words(words):
    wordL = len(words)
    wordL = wordL if wordL > 1 else ""
    fmt = '>{0}B'.format(len(words))

    words = struct.pack(fmt, *words)
    lcd_write_data(words)

def lcd_set_window(x0, y0, x1, y1):
    # Column Address Set
    lcd_write_cmd(CASET)
    lcd_write_words([(x0>>8) & 0xFF, x0 & 0xFF, (y0>>8) & 0xFF, y0 & 0xFF])
    # Page Address Set
    lcd_write_cmd(PASET)
    lcd_write_words([(x1>>8) & 0xFF, x1 & 0xFF, (y1>>8) & 0xFF, y1 & 0xFF])
    # Memory Write
    lcd_write_cmd(RAMWR)

def lcd_init(VSYNC=False):
    lcd_reset()

    lcd_write_cmd(LCDOFF)   # Display OFF
    pyb.delay(10)

    lcd_write_cmd(SWRESET)  # Reset SW
    pyb.delay(50)
    lcd_write_cmd(MADCTL)   # Memory Access Control
    # | MY=0 | MX=1 | MV=0 | ML=0 | BGR=1 | MH=0 | 0 | 0 |
    lcd_write_data(0x48)

    lcd_write_cmd(PTLON)    # Partial mode ON

    lcd_write_cmd(PIXFMT)   # Pixel format set
    #lcd_write_data(0x66)    # 18-bit/pixel
    lcd_write_data(0x55)    # 16-bit/pixel

    ##############################################################
    lcd_VSYNC_deinit()
    ###########################################################

    lcd_write_cmd(GAMMASET)
    lcd_write_data(0x01)

    lcd_write_cmd(0xb7)     # Entry mode set
    lcd_write_data(0x07)

    lcd_write_cmd(SLPOUT)   # sleep mode OFF
    pyb.delay(100)
    lcd_write_cmd(LCDON)
    pyb.delay(100)

    lcd_write_cmd(RAMWR)

def lcd_VSYNC_init():
    lcd_write_cmd(IFMODE)   # RGB Interface control
    lcd_write_data(0x60)    # RCM[1:0] = "11" SYNC mode

    lcd_write_cmd(FRMCTR1)  # Frame rate control (in normal mode)
    lcd_write_words([0x00, 0x10])
    #                0x00          DIV[1:0] (x 1/1)
    #                      0x10    112Hz
    #                      0x1B    70Hz (Default)

    lcd_write_cmd(DFUNCTR)  # Display function control
    lcd_write_words([0x0A, 0x80, 0x27, 0x3F])
    #                      0x80                REV = "1" norm. white, ISC[3:0] = "0000" Scan cicle 17ms.
    #                                  0x3F    63 CLK

    #lcd_write_cmd(PRCTR)
    #lcd_write_words([0x72, 0x72, 0x10, 0x18])
    #                0x72                      VFP = 114 lines
    #                      0x72                VBP = 114 lines
    #                            0x10          HFP = 16 CLK
    #                                  0x18    HBP = 24 CLK

    lcd_write_data(INVCTR)  # Frame Inversion control
    lcd_write_data(0x27)    # NL = 320 lines

    lcd_write_cmd(IFMODE)    # RGB Interface Signal Control
    lcd_write_data(0xE0)     # SYNC mode RCM[1:0] = "11"

def lcd_VSYNC_start():
    # Set GRAM Address:
    lcd_set_window(0, 0, TFTWIDTH, TFTHEIGHT)

    # Interface Control:
    lcd_write_cmd(IFCTL)
    lcd_write_words([0x01, 0x00, 0x08])
    #                            0x08    DM[1:0] = "10" VSYNC mode

    lcd_write_cmd(RAMWR)

def lcd_VSYNC_deinit():
    lcd_write_cmd(PTLON)    # Partial mode ON
    lcd_write_cmd(FRMCTR1)  # Frame rate control (in normal mode)
    lcd_write_words([0x00, 0x1b])
    #                0x00          DIV[1:0] (x 1/1)
    #                      0x1B    70Hz (Default)

    lcd_write_cmd(DFUNCTR)  # Display function control
    lcd_write_words([0x0A, 0x80, 0x27, 0x00])
    #                      0x80                REV = "1" norm. white, ISC[3:0] = "0000" Scan cicle 17ms.

    lcd_write_cmd(PRCTR)
    lcd_write_words([0x02, 0x02, 0x0A, 0x14])
    #                0x02                      VFP = 2 lines
    #                      0x02                VBP = 2 lines
    #                            0x0A          HFP = 10 CLK
    #                                  0x14    HBP = 20 CLK

    lcd_write_cmd(PTLON)    # Partial mode ON

    lcd_write_cmd(IFCTL)    # Interface Control
    lcd_write_words([0x01, 0x00, 0x00])
    #                            0x00     DM[1:0] = "00" and RM = 0 is System interface mode
    pyb.delay(4)
    lcd_write_cmd(IFMODE)   # RGB Interface control
    lcd_write_data(0x80)    # RCM[1:0] = "10" DE mode

def get_Npix_monoword(color, pixels=4):
    R, G, B = color
    fmt = '>Q' if pixels == 4 else '>H'
    pixel = (R<<11) | (G<<5) | B
    monocolor = pixel<<(16*3) | pixel<<(16*2) | pixel<<16 | pixel

    word = struct.pack(fmt, monocolor)
    return word

def lcd_test():
    colors = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, PURPLE, WHITE]
    pixels = 10 * TFTWIDTH
    for i in range(TFTHEIGHT//40):
        word = get_Npix_monoword(colors[i]) * pixels
        lcd_write_data(word)

def lcd_random_test():
    colors = [
        BLACK,    NAVY,    DARKGREEN,  DARKCYAN,
        MAROON,   PURPLE,  OLIVE,      LIGHTGREY,
        DARKGREY, BLUE,    GREEN,      CYAN,
        RED,      MAGENTA, YELLOW,     WHITE,
        ORANGE,   GREENYELLOW
        ]
    pixels = TFTWIDTH
    j = 0
    for i in range(TFTHEIGHT//4):
        j = struct.unpack('<B', os.urandom(1))[0]//15
        word = get_Npix_monoword(colors[j]) * pixels
        lcd_write_data(word)

def lcd_draw_pixel(x, y, color):
    lcd_set_window(x, x+1, y, y+1)
    lcd_write_data(get_Npix_monoword(color))

def lcd_draw_Vline(x, y, length, color, width=1):
    if length > 320: length = 320
    if width > 10: width = 10
    lcd_set_window(x, x+(width-1), y, length)
    pixels = width * length
    pixels = pixels//4 if pixels >= 4 else pixels
    word = get_Npix_monoword(color) * pixels
    lcd_write_data(word)

def lcd_draw_Hline(x, y, length, color, width=1):
    if length > 240: length = 240
    if width > 10: width = 10
    lcd_set_window(x, length, y, y+(width-1))
    pixels = width * length
    pixels = pixels//4 if pixels >= 4 else pixels
    word = get_Npix_monoword(color) * pixels
    lcd_write_data(word)

def lcd_draw_rect(x, y, width, height, color, border=1, fillcolor=None):
    if width > 240: width = 240
    if height > 320: height = 320
    if border:
        if border > width//2:
            border = width//2-1
        X, Y = x, y
        for i in range(2):
            Y = y+height-(border-1) if i == 1 else y
            lcd_draw_Hline(X, Y, x+width, color, border)

            Y = y+(border-1) if i == 1 else y
            X = x+width-(border-1) if i == 1 else x
            lcd_draw_Vline(X, Y, y+height, color, border)
    else:
        fillcolor = color

    if fillcolor:
        xsum = x+border
        ysum = y+border
        dborder = border*2
        lcd_set_window(xsum, xsum+width-dborder, ysum, ysum+height-dborder)
        pixels = (width-dborder)*8+border+width
        rows   = (height>>5)

        if rows < 1:
            rows = 1
            word = get_Npix_monoword(fillcolor) * (pixels//4)
        else:
            word = get_Npix_monoword(fillcolor) * pixels

        i=0
        while i < (rows):
            lcd_write_data(word)
            i+=1

def lcd_fill_monocolor(color, margin=0):
    lcd_draw_rect(margin, margin, TFTWIDTH, TFTHEIGHT, color, border=0)

def get_x_perimeter_point(x, degrees, radius):
    sin = math.sin(math.radians(degrees))
    x = int(x+(radius*sin))
    return x

def get_y_perimeter_point(y, degrees, radius):
    cos = math.cos(math.radians(degrees))
    y = int(y-(radius*cos))
    return y

def lcd_draw_circle(x, y, radius, color, border=2):
    for j in range(2):
        R = radius-border*j
        if j == 1: color = RED
        tempY = 0
        for i in range(180):
            xNeg = get_x_perimeter_point(x, 360-i, R)
            xPos = get_x_perimeter_point(x, i, R)
            Y    = get_y_perimeter_point(y, i, R)
            if i > 89: Y = Y-1
            if i == 90: xPos = xPos-1
            if tempY != Y and tempY > 0:
                length = xPos+1
                lcd_draw_Hline(xNeg, Y, length, color, width=2)
            tempY = Y

def lcd_draw_oval(x, y, xradius, yradius, color):
    tempY = 0
    for i in range(180):
        xNeg = get_x_perimeter_point(x, 360-i, xradius)
        xPos = get_x_perimeter_point(x, i, xradius)
        Y    = get_y_perimeter_point(y, i, yradius)

        if i > 89: Y = Y-1
        if tempY != Y and tempY > 0:
            length = xPos+1
            lcd_draw_Hline(xNeg, Y, length, color, width=2)
        tempY = Y


# TEST CODE

lcd_init()

lcd_fill_monocolor(GREEN)
lcd_fill_monocolor(BLUE)

lcd_draw_circle(TFTWIDTH//2, TFTHEIGHT//2, 80, BLACK, border=5)
lcd_VSYNC_init()
lcd_draw_oval(100, 50, 20, 30, RED)

#lcd_VSYNC_start()