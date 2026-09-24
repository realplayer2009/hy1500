#!/data/data/com.termux/files/usr/bin/bash
set -e
cd /data/data/com.termux/files/home/rs485
export PREFIX=/data/data/com.termux/files/usr
export PATH="$PREFIX/bin:$PATH"

rm -rf build/moc build/obj
mkdir -p build/moc build/obj

CXX=clang++
DEFINES="-DQT_WIDGETS_LIB -DQT_GUI_LIB -DQT_SERIALPORT_LIB -DQT_CORE_LIB"
CXXFLAGS="-std=c++11 -O2 -fPIC $DEFINES"
INCPATH="-Isrc -Ibuild/moc -I$PREFIX/include/QtWidgets -I$PREFIX/include/QtGui -I$PREFIX/include/QtSerialPort -I$PREFIX/include/QtCore"
LIBS="-L$PREFIX/lib -lQt5Widgets -lQt5Gui -lQt5Core -lQt5SerialPort"

# Generate moc_predefs.h (best-effort; ignore if unsupported)
moc -E $DEFINES > build/moc/moc_predefs.h 2>/dev/null || true

for h in src/applogic.h src/appui.h src/rs485device.h; do
    base=$(basename "$h" .h)
    moc --include build/moc/moc_predefs.h -Isrc $INCPATH "$h" -o "build/moc/moc_${base}.cpp"
done

SRCS=(src/main.cpp src/controlalgorithm.cpp src/appui.cpp src/applogic.cpp src/rs485device.cpp build/moc/moc_applogic.cpp build/moc/moc_appui.cpp build/moc/moc_rs485device.cpp)
OBJS=()
for s in "${SRCS[@]}"; do
    o="build/obj/$(basename "${s%.cpp}.o")"
    $CXX -c $CXXFLAGS $INCPATH -o "$o" "$s"
    OBJS+=("$o")
done

$CXX -o RS485Control "${OBJS[@]}" $LIBS
ls -la RS485Control
