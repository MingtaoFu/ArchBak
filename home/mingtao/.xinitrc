#!/bin/sh

# /etc/X11/xinit/xinitrc
#
# global xinitrc file, used by all X sessions started by xinit (startx)

# invoke global X session script
export GTK_IM_MODULE=fcitx
     export QT_IM_MODULE=fcitx
	      export XMODIFIERS="@im=fcitx"
. /etc/X11/Xsession

