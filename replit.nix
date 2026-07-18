{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.chromium

    # Playwright system deps (Chromium)
    pkgs.nss
    pkgs.nspr
    pkgs.nssTools

    # GTK / accessibility
    pkgs.ATK
    pkgs.at-spi2-atk
    pkgs.gtk3
    pkgs.glib

    # Graphics
    pkgs.cairo
    pkgs.pango
    pkgs.gdk-pixbuf
    pkgs.libdrm
    pkgs.libgbm

    # X11
    pkgs.xorg.libX11
    pkgs.xorg.libXcomposite
    pkgs.xorg.libXdamage
    pkgs.xorg.libXrandr
    pkgs.xorg.libXss
    pkgs.xorg.libXtst
    pkgs.xorg.libXi
    pkgs.xorg.libXext
    pkgs.xorg.libXfixes
    pkgs.xorg.libxcb

    # Fonts & misc
    pkgs.fontconfig
    pkgs.freetype
    pkgs.dbus
    pkgs.expat
  ];
}
