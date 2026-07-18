{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.chromium
    pkgs.nss
    pkgs.nspr
    pkgs ATK
    pkgs.atk
    pkgs.at-spi2-atk
    pkgs.XDG_SESSION_TYPE
    pkgs.libdrm
    pkgs.libgbm
    pkgs.gtk3
    pkgs.pango
    pkgs.cairo
    pkgs.glib
    pkgs.gdk-pixbuf
    pkgs.xorg.libX11
    pkgs.xorg.libXcomposite
    pkgs.xorg.libXdamage
    pkgs.xorg.libXrandr
    pkgs.xorg.libXss
    pkgs.xorg.libXtst
    pkgs.xorg.libXi
    pkgs.xorg.libXext
    pkgs.xorg.libXfixes
    pkgs.fontconfig
    pkgs.freetype
    pkgs.dbus
  ];
}
