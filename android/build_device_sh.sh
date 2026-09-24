set -e
cd /data/data/com.termux/files/home/rs485
export PREFIX=/data/data/com.termux/files/usr
export PATH="$PREFIX/bin:$PATH"
rm -rf build/moc build/obj
mkdir -p build/moc build/obj
echo "=== moc ==="
moc -E -DQT_WIDGETS_LIB -DQT_GUI_LIB -DQT_SERIALPORT_LIB -DQT_CORE_LIB > build/moc/moc_predefs.h 2>/dev/null || true
moc --include build/moc/moc_predefs.h -Isrc -I$PREFIX/include/QtWidgets -I$PREFIX/include/QtGui -I$PREFIX/include/QtSerialPort -I$PREFIX/include/QtCore src/applogic.h -o build/moc/moc_applogic.cpp
moc --include build/moc/moc_predefs.h -Isrc -I$PREFIX/include/QtWidgets -I$PREFIX/include/QtGui -I$PREFIX/include/QtSerialPort -I$PREFIX/include/QtCore src/appui.h -o build/moc/moc_appui.cpp
moc --include build/moc/moc_predefs.h -Isrc -I$PREFIX/include/QtWidgets -I$PREFIX/include/QtGui -I$PREFIX/include/QtSerialPort -I$PREFIX/include/QtCore src/rs485device.h -o build/moc/moc_rs485device.cpp
echo "=== compile ==="
for cpp in src/main.cpp src/controlalgorithm.cpp src/appui.cpp src/applogic.cpp src/rs485device.cpp build/moc/moc_applogic.cpp build/moc/moc_appui.cpp build/moc/moc_rs485device.cpp; do
    base=$(basename "$cpp" .cpp)
    obj="build/obj/$base.o"
    echo "--- $cpp"
    clang++ -std=c++11 -O2 -fPIC -DQT_DEPRECATED_WARNINGS -DQT_NO_DEBUG -DQT_WIDGETS_LIB -DQT_GUI_LIB -DQT_CORE_LIB -I$PREFIX/include -I$PREFIX/include/QtCore -I$PREFIX/include/QtGui -I$PREFIX/include/QtWidgets -I$PREFIX/include/QtSerialPort -Isrc -Ibuild/moc -c "$cpp" -o "$obj"
done
echo "=== link ==="
clang++ build/obj/main.o build/obj/controlalgorithm.o build/obj/appui.o build/obj/applogic.o build/obj/rs485device.o build/obj/moc_applogic.o build/obj/moc_appui.o build/obj/moc_rs485device.o -o RS485Control -L$PREFIX/lib -lQt5Widgets -lQt5Gui -lQt5Core -lQt5SerialPort
echo "=== result ==="
ls -la RS485Control
file RS485Control 2>/dev/null || true
echo BUILD_OK
