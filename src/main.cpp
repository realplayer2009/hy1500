#include "appui.h"
#include <QApplication>
#include <QFileInfo>
#include <QDir>
#ifdef RS485_NATIVE_ANDROID
#include <QFile>
#include <QStandardPaths>
#include <QDebug>
#endif

static QString locateConfigFile()
{
    const QStringList candidates = {
        QDir::currentPath() + "/config/app.local.ini",
        QDir::currentPath() + "/config/app.ini",
        QDir::currentPath() + "/app.ini",
        QApplication::applicationDirPath() + "/config/app.local.ini",
        QApplication::applicationDirPath() + "/config/app.ini",
        QApplication::applicationDirPath() + "/app.ini"
    };
    for (const QString &path : candidates) {
        if (QFileInfo::exists(path))
            return path;
    }
    return candidates.last();
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("RS485Control");
    app.setOrganizationName("RS485Control");

#ifdef RS485_NATIVE_ANDROID
    // APK assets are read-only; keep editable settings and logs in app storage.
    const QString appData = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    if (appData.isEmpty() || !QDir().mkpath(appData + "/config")
        || !QDir().mkpath(appData + "/assets") || !QDir::setCurrent(appData)) {
        qCritical() << "Cannot prepare Android app storage:" << appData;
        return 1;
    }
    for (const QString &relativePath : { QString("config/app.ini"),
                                        QString("assets/click.wav") }) {
        if (!QFileInfo::exists(relativePath)
            && (!QFile::copy("assets:/" + relativePath, relativePath)
                || !QFile::setPermissions(relativePath, QFile::ReadOwner | QFile::WriteOwner))) {
            qCritical() << "Cannot initialize Android app file:" << relativePath;
            return 1;
        }
    }
#endif

    // 注册跨线程信号槽所需的自定义类型
    qRegisterMetaType<DeviceProfile::DeviceKey>("DeviceProfile::DeviceKey");
    qRegisterMetaType<SerialPortWorker::PollTask>("SerialPortWorker::PollTask");
    qRegisterMetaType<SerialPortWorker::WriteTask>("SerialPortWorker::WriteTask");
    qRegisterMetaType<QVector<SerialPortWorker::PollTask>>(
        "QVector<SerialPortWorker::PollTask>");

    const QString configPath = locateConfigFile();
    if (!AppConfig::instance().load(configPath)) {
        // 配置文件不存在时仍启动，便于首次运行
    }

    MainWindow w;
    w.showFullScreen();

    return app.exec();
}
