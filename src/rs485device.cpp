// ============================================================
// RS485 与设备交互层实现
// 合并自: deviceprofile.cpp / modbusframe.cpp / modbusrtu.cpp
//         / serialportworker.cpp
// ============================================================

#include "rs485device.h"
#include <QThread>
#include <QDateTime>
#include <QDebug>

// ============================================================
// DeviceProfile: PCB 板寄存器映射与解析
// 协议: Modbus 地址表 [26.08.17]
// ============================================================

QString DeviceProfile::deviceTypeToString(DeviceType t)
{
    Q_UNUSED(t)
    return "PcbBoard";
}

DeviceProfile::DeviceType DeviceProfile::deviceTypeFromString(const QString &s)
{
    // 兼容旧配置/旧 CSV 中的历史类型字符串, 统一收敛为 PCB 板
    Q_UNUSED(s)
    return PcbBoard;
}

QString DeviceProfile::deviceTypeDisplayName(DeviceType t)
{
    Q_UNUSED(t)
    return QString::fromUtf8("PCB板");
}

namespace {

DeviceProfile::ReadSegment makeSegment(quint16 addr, quint16 count)
{
    DeviceProfile::ReadSegment s;
    s.startAddr = addr;
    s.count = count;
    return s;
}

// 温度类寄存器按 INT16 补码解析: 正整数与 UINT 结果一致, 兼容零下温度
int toInt16(quint16 raw)
{
    return static_cast<qint16>(raw);
}

} // namespace

DeviceProfile::RegisterMap DeviceProfile::defaultRegisterMap(DeviceType t)
{
    Q_UNUSED(t)
    RegisterMap m;

    // 0x0000 软件版本号 (1 寄存器)
    m.readSegments.append(makeSegment(RegVersion, 1));
    // 0x0001~0x000B 为连续的输入采集区
    m.readSegments.append(makeSegment(RegHvInput, 11));
    // 0x000C 外扩 5 路输入状态 (1 寄存器, 现场 firmware 实测地址)
    m.readSegments.append(makeSegment(RegExpInputC, 1));
    // 0x000E 协议文档地址, 现场实测恒为 0; 保留作为旧 firmware 回退
    m.readSegments.append(makeSegment(RegExpInput, 1));
    // 0x0031 OT01~OT10 位掩码 (1 寄存器)
    m.readSegments.append(makeSegment(RegOtMask, 1));
    // 0x0033 外扩 OUT1~OUT7 位掩码 (1 寄存器)
    m.readSegments.append(makeSegment(RegExpOutput, 1));
    return m;
}

void DeviceProfile::parseSegment(quint16 startAddr, const QVector<quint16> &regs,
                                 QMap<QString, QVariant> &out)
{
    switch (startAddr) {
    case RegVersion:
        if (!regs.isEmpty())
            out["software_version"] = regs.at(0);
        break;
    case RegHvInput:
        if (regs.size() >= 11) {
            out["hv_input"]         = regs.at(0);
            out["reserved"]         = regs.at(1);
            out["external_voltage"] = regs.at(2);
            for (int i = 0; i < 3; ++i) {
                out[QString("th%1_temp").arg(i + 1)] = toInt16(regs.at(3 + i * 2));
                out[QString("th%1_humi").arg(i + 1)] = regs.at(4 + i * 2);
            }
            out["pt1_temp"] = toInt16(regs.at(9));
            out["pt2_temp"] = toInt16(regs.at(10));
        }
        break;
    case RegExpInputC:
        if (!regs.isEmpty()) {
            // 现场 firmware 实测: IN1~IN5 对应 bit1~bit5, bit0 为常置状态位
            const quint16 mask = regs.at(0);
            for (int i = 0; i < 5; ++i)
                out[QString("exp_in%1").arg(i + 1)] = (mask >> (i + 1)) & 1;
        }
        break;
    case RegExpInput:
        // 旧 firmware 回退: 仅当该地址非零才写入, 避免覆盖 0x000C 的结果
        if (!regs.isEmpty() && regs.at(0) != 0) {
            const quint16 mask = regs.at(0);
            for (int i = 0; i < 5; ++i)
                out[QString("exp_in%1").arg(i + 1)] = (mask >> i) & 1;
        }
        break;
    case RegOtMask:
        if (!regs.isEmpty()) {
            const quint16 mask = regs.at(0);
            for (int i = 0; i < 10; ++i)
                out[QString("ot%1").arg(i + 1, 2, 10, QChar('0'))] = (mask >> i) & 1;
        }
        break;
    case RegExpOutput:
        if (!regs.isEmpty()) {
            const quint16 mask = regs.at(0);
            for (int i = 0; i < 7; ++i)
                out[QString("exp_out%1").arg(i + 1)] = (mask >> i) & 1;
        }
        break;
    default:
        // 未知段兑底: 按原始寄存器展示
        for (int i = 0; i < regs.size(); ++i)
            out[QString("reg_0x%1").arg(startAddr + i, 4, 16, QChar('0'))] = regs.at(i);
        break;
    }
}

QVector<DeviceProfile::WriteItem> DeviceProfile::encodeWriteValues(
    DeviceType t, const QMap<QString, QVariant> &fields)
{
    Q_UNUSED(t)

    // OT01~OT10 -> 0x0031 位掩码
    quint16 otMask = 0;
    bool otExplicit = false;
    for (int i = 0; i < 10; ++i) {
        const QString key = QString("ot%1").arg(i + 1, 2, 10, QChar('0'));
        if (fields.contains(key)) {
            otExplicit = true;
            if (fields.value(key).toBool())
                otMask |= (1u << i);
        }
    }

    // 外扩 OUT1~OUT7 -> 0x0033 位掩码
    quint16 expMask = 0;
    bool expExplicit = false;
    for (int i = 0; i < 7; ++i) {
        const QString key = QString("exp_out%1").arg(i + 1);
        if (fields.contains(key)) {
            expExplicit = true;
            if (fields.value(key).toBool())
                expMask |= (1u << i);
        }
    }

    QVector<WriteItem> items;
    if (otExplicit) {
        WriteItem item;
        item.startAddr = RegOtMask;
        item.values.append(otMask);
        items.append(item);
    }
    if (expExplicit) {
        WriteItem item;
        item.startAddr = RegExpOutput;
        item.values.append(expMask);
        items.append(item);
    }
    return items;
}

QVector<quint16> DeviceProfile::applyBitmaskFields(quint16 startAddr,
                                                    const QVector<quint16> &currentRegs,
                                                    const QMap<QString, QVariant> &fields)
{
    if (startAddr == RegOtMask && !currentRegs.isEmpty()) {
        quint16 mask = currentRegs.at(0);
        for (int i = 0; i < 10; ++i) {
            const QString key = QString("ot%1").arg(i + 1, 2, 10, QChar('0'));
            if (fields.contains(key)) {
                if (fields.value(key).toBool())
                    mask |= (1u << i);
                else
                    mask &= ~(1u << i);
            }
        }
        return { mask };
    }
    if (startAddr == RegExpOutput && !currentRegs.isEmpty()) {
        quint16 mask = currentRegs.at(0);
        for (int i = 0; i < 7; ++i) {
            const QString key = QString("exp_out%1").arg(i + 1);
            if (fields.contains(key)) {
                if (fields.value(key).toBool())
                    mask |= (1u << i);
                else
                    mask &= ~(1u << i);
            }
        }
        return { mask };
    }
    return currentRegs;
}

QStringList DeviceProfile::orderedFields()
{
    static const QStringList order = {
        "software_version",
        "hv_input", "reserved", "external_voltage",
        "th1_temp", "th1_humi", "th2_temp", "th2_humi",
        "th3_temp", "th3_humi",
        "pt1_temp", "pt2_temp",
        "exp_in1", "exp_in2", "exp_in3", "exp_in4", "exp_in5",
        "ot01", "ot02", "ot03", "ot04", "ot05",
        "ot06", "ot07", "ot08", "ot09", "ot10",
        "exp_out1", "exp_out2", "exp_out3", "exp_out4", "exp_out5",
        "exp_out6", "exp_out7"
    };
    return order;
}

QString DeviceProfile::fieldDisplayName(const QString &field)
{
    static const QMap<QString, QString> names = {
        { "software_version", QString::fromUtf8("软件版本号") },
        { "hv_input",      QString::fromUtf8("高压通电输入状态") },
        { "reserved",      QString::fromUtf8("备用输入") },
        { "external_voltage", QString::fromUtf8("外部电压采样输入值") },
        { "pt1_temp",      QString::fromUtf8("PT100-1 温度") },
        { "pt2_temp",      QString::fromUtf8("PT100-2 温度") },
    };
    if (names.contains(field))
        return names.value(field);
    // th1_temp ~ th3_humi
    if (field.size() == 8 && field.startsWith("th") && field.endsWith("_temp"))
        return QString::fromUtf8("温湿度%1-温度").arg(field.mid(2, 1));
    if (field.size() == 8 && field.startsWith("th") && field.endsWith("_humi"))
        return QString::fromUtf8("温湿度%1-湿度").arg(field.mid(2, 1));
    // exp_in1 ~ exp_in5
    if (field.startsWith("exp_in") && field.length() == 6)
        return QString::fromUtf8("外扩输入%1").arg(field.mid(6));
    // ot01 ~ ot10
    if (field.size() == 4 && field.startsWith("ot"))
        return field.toUpper() + QString::fromUtf8("输出");
    // exp_out1 ~ exp_out7
    if (field.startsWith("exp_out") && field.length() == 7) {
        const int n = field.mid(7).toInt();
        if (n == 6)
            return QString::fromUtf8("外扩输出6(闪烁显示灯)");
        if (n == 7)
            return QString::fromUtf8("外扩输出7(蜂鸣器提示)");
        return QString::fromUtf8("外扩输出%1").arg(n);
    }
    return field;
}

QString DeviceProfile::fieldDisplayValue(const QString &field, const QVariant &value)
{
    const int v = value.toInt();
    if (field == "software_version")
        return QString::fromUtf8("V%1").arg(v);
    if (field == "hv_input")
        return v == 0 ? QString::fromUtf8("无") : QString::fromUtf8("有");
    if (field.startsWith("ot") || field.startsWith("exp_out") || field.startsWith("exp_in"))
        return v == 0 ? QString::fromUtf8("关闭") : QString::fromUtf8("打开");
    if (field == "external_voltage")
        return QString::fromUtf8("%1 V").arg(QString::number(v / 10.0, 'f', 1));
    if (field.endsWith("_temp"))
        return QString::fromUtf8("%1 ℃").arg(QString::number(v / 10.0, 'f', 1));
    if (field.endsWith("_humi"))
        return QString::fromUtf8("%1 %RH").arg(QString::number(v / 10.0, 'f', 1));
    return value.toString();
}

// ============================================================
// ModbusFrame: RTU 帧构建与解析
// ============================================================

quint16 ModbusFrame::crc16(const QByteArray &data)
{
    quint16 crc = 0xFFFF;
    for (int i = 0; i < data.size(); ++i) {
        crc ^= static_cast<quint8>(data.at(i));
        for (int j = 0; j < 8; ++j) {
            if (crc & 0x0001)
                crc = (crc >> 1) ^ 0xA001;
            else
                crc >>= 1;
        }
    }
    return crc;
}

static QByteArray appendCrc(const QByteArray &payload)
{
    QByteArray frame = payload;
    const quint16 crc = ModbusFrame::crc16(payload);
    frame.append(static_cast<char>(crc & 0xFF));
    frame.append(static_cast<char>((crc >> 8) & 0xFF));
    return frame;
}

QByteArray ModbusFrame::buildReadRequest(quint8 slaveId, FunctionCode fc,
                                          quint16 startAddr, quint16 count)
{
    QByteArray payload;
    payload.append(static_cast<char>(slaveId));
    payload.append(static_cast<char>(fc));
    payload.append(static_cast<char>((startAddr >> 8) & 0xFF));
    payload.append(static_cast<char>(startAddr & 0xFF));
    payload.append(static_cast<char>((count >> 8) & 0xFF));
    payload.append(static_cast<char>(count & 0xFF));
    return appendCrc(payload);
}

QByteArray ModbusFrame::buildWriteSingleRequest(quint8 slaveId, quint16 addr,
                                                 quint16 value)
{
    QByteArray payload;
    payload.append(static_cast<char>(slaveId));
    payload.append(static_cast<char>(WriteSingleRegister));
    payload.append(static_cast<char>((addr >> 8) & 0xFF));
    payload.append(static_cast<char>(addr & 0xFF));
    payload.append(static_cast<char>((value >> 8) & 0xFF));
    payload.append(static_cast<char>(value & 0xFF));
    return appendCrc(payload);
}

QByteArray ModbusFrame::buildWriteMultipleRequest(quint8 slaveId, quint16 startAddr,
                                                   const QVector<quint16> &values)
{
    const quint16 count = static_cast<quint16>(values.size());
    const quint8 byteCount = static_cast<quint8>(count * 2);

    QByteArray payload;
    payload.append(static_cast<char>(slaveId));
    payload.append(static_cast<char>(WriteMultipleRegisters));
    payload.append(static_cast<char>((startAddr >> 8) & 0xFF));
    payload.append(static_cast<char>(startAddr & 0xFF));
    payload.append(static_cast<char>((count >> 8) & 0xFF));
    payload.append(static_cast<char>(count & 0xFF));
    payload.append(static_cast<char>(byteCount));
    for (quint16 v : values) {
        payload.append(static_cast<char>((v >> 8) & 0xFF));
        payload.append(static_cast<char>(v & 0xFF));
    }
    return appendCrc(payload);
}

bool ModbusFrame::parseReadResponse(const QByteArray &frame, quint8 expectedSlave,
                                     quint8 expectedFc, QVector<quint16> &outValues)
{
    if (frame.size() < 5)
        return false;

    const QByteArray payload = frame.left(frame.size() - 2);
    const quint16 recvCrc = static_cast<quint8>(frame.at(frame.size() - 2))
                          | (static_cast<quint8>(frame.at(frame.size() - 1)) << 8);
    if (crc16(payload) != recvCrc)
        return false;

    if (static_cast<quint8>(payload.at(0)) != expectedSlave)
        return false;

    const quint8 fc = static_cast<quint8>(payload.at(1));
    if (fc != expectedFc) {
        // Modbus 异常响应: fc | 0x80
        return false;
    }

    const quint8 byteCount = static_cast<quint8>(payload.at(2));
    if (payload.size() != 3 + byteCount)
        return false;

    outValues.clear();
    for (int i = 0; i < byteCount; i += 2) {
        quint16 val = (static_cast<quint8>(payload.at(3 + i)) << 8)
                    | static_cast<quint8>(payload.at(3 + i + 1));
        outValues.append(val);
    }
    return true;
}

bool ModbusFrame::parseWriteResponse(const QByteArray &frame, quint8 expectedSlave,
                                      quint8 expectedFc)
{
    if (frame.size() < 5)
        return false;

    const QByteArray payload = frame.left(frame.size() - 2);
    const quint16 recvCrc = static_cast<quint8>(frame.at(frame.size() - 2))
                          | (static_cast<quint8>(frame.at(frame.size() - 1)) << 8);
    if (crc16(payload) != recvCrc)
        return false;

    return static_cast<quint8>(payload.at(0)) == expectedSlave
        && static_cast<quint8>(payload.at(1)) == expectedFc;
}

bool ModbusFrame::extractFrame(QByteArray &buffer, QByteArray &outFrame)
{
    // RTU 帧最短 5 字节 (异常响应), 读响应至少 5 字节
    while (buffer.size() >= 5) {
        const quint8 fc = static_cast<quint8>(buffer.at(1));
        int expectedLen = 0;

        if (fc & 0x80) {
            expectedLen = 5; // 异常: addr + fc + excode + crc2
        } else if (fc == ReadHoldingRegisters || fc == ReadInputRegisters) {
            if (buffer.size() < 3)
                return false;
            expectedLen = 3 + static_cast<quint8>(buffer.at(2)) + 2;
        } else if (fc == WriteSingleRegister) {
            expectedLen = 8;
        } else if (fc == WriteMultipleRegisters) {
            expectedLen = 8;
        } else {
            // 未知功能码，丢弃首字节重新同步
            buffer.remove(0, 1);
            continue;
        }

        if (buffer.size() < expectedLen)
            return false;

        outFrame = buffer.left(expectedLen);
        buffer.remove(0, expectedLen);
        return true;
    }
    return false;
}

// ============================================================
// ModbusRtu: 高层读写接口
// ============================================================

ModbusRtu::Result ModbusRtu::readHoldingRegisters(TransactFunc transact,
                                                   quint8 slaveId,
                                                   quint16 startAddr,
                                                   quint16 count)
{
    const QByteArray req = ModbusFrame::buildReadRequest(
        slaveId, ModbusFrame::ReadHoldingRegisters, startAddr, count);
    Result r = transact(req, ModbusFrame::ReadHoldingRegisters);
    return r;
}

ModbusRtu::Result ModbusRtu::readInputRegisters(TransactFunc transact,
                                                quint8 slaveId,
                                                quint16 startAddr,
                                                quint16 count)
{
    const QByteArray req = ModbusFrame::buildReadRequest(
        slaveId, ModbusFrame::ReadInputRegisters, startAddr, count);
    return transact(req, ModbusFrame::ReadInputRegisters);
}

ModbusRtu::Result ModbusRtu::writeSingleRegister(TransactFunc transact,
                                                  quint8 slaveId,
                                                  quint16 addr,
                                                  quint16 value)
{
    const QByteArray req = ModbusFrame::buildWriteSingleRequest(slaveId, addr, value);
    Result r = transact(req, ModbusFrame::WriteSingleRegister);
    if (r.success)
        r.registers = { value };
    return r;
}

ModbusRtu::Result ModbusRtu::writeMultipleRegisters(TransactFunc transact,
                                                     quint8 slaveId,
                                                     quint16 startAddr,
                                                     const QVector<quint16> &values)
{
    const QByteArray req = ModbusFrame::buildWriteMultipleRequest(
        slaveId, startAddr, values);
    Result r = transact(req, ModbusFrame::WriteMultipleRegisters);
    return r;
}

// ============================================================
// SerialPortWorker: 串口工作线程对象
// ============================================================

SerialPortWorker::SerialPortWorker(const PortSettings &settings, QObject *parent)
    : QObject(parent)
    , m_settings(settings)
{
    m_serial = new QSerialPort(this);
    connect(m_serial, &QSerialPort::errorOccurred, this,
            &SerialPortWorker::onSerialError);
    m_pollTimer = new QTimer(this);
    m_pollTimer->setSingleShot(false);
    connect(m_pollTimer, &QTimer::timeout, this, &SerialPortWorker::onPollTimer);

    m_queueTimer = new QTimer(this);
    m_queueTimer->setSingleShot(true);
    connect(m_queueTimer, &QTimer::timeout, this, &SerialPortWorker::processQueue);
}

SerialPortWorker::~SerialPortWorker()
{
    stopWork();
}

void SerialPortWorker::startWork()
{
    if (!openPort()) {
        emit portError(m_settings.portIndex,
                       QString::fromUtf8("无法打开串口: %1").arg(m_settings.device));
        m_portAnnounced = true;
        return;
    }
    m_portAnnounced = false;
}

void SerialPortWorker::stopWork()
{
    stopPolling();
    closePort();
}

void SerialPortWorker::startPolling(int intervalMs)
{
    m_pollTimer->setInterval(intervalMs);
    if (!m_pollTimer->isActive())
        m_pollTimer->start();
}

void SerialPortWorker::stopPolling()
{
    if (m_pollTimer->isActive())
        m_pollTimer->stop();
}

void SerialPortWorker::setPollTasks(const QVector<PollTask> &tasks)
{
    m_pollTasks = tasks;
}

void SerialPortWorker::restartDiscovery()
{
    QMutexLocker lock(&m_queueMutex);
    for (int i = m_queue.size() - 1; i >= 0; --i) {
        if (m_queue.at(i).type != Write)
            m_queue.removeAt(i);
    }
    m_nextDiscoverySlaveId = 1;
    // 手动重扫: 执行一轮完整扫描后自动停止, 不做持续发现
    m_discoveryActive = true;
    m_discoveryUntilFirstFound = false;
    m_discoveryProbesRemaining = 247;
}

void SerialPortWorker::enqueueWrite(const WriteTask &task)
{
    QMutexLocker lock(&m_queueMutex);
    QueueItem item;
    item.type = Write;
    item.write = task;

    // 控制命令不应被一整轮读轮询阻塞。特别是队列中含有离线从站时，
    // 每个离线从站都会占用一个完整超时周期，使写入结果受设备排列顺序影响。
    // 将新写任务放到所有待处理轮询之前，但保留已排队写任务的 FIFO 顺序。
    int insertPos = 0;
    while (insertPos < m_queue.size()
           && m_queue.at(insertPos).type == Write) {
        ++insertPos;
    }
    m_queue.insert(insertPos, item);

    if (!m_busy)
        m_queueTimer->start(0);
}

void SerialPortWorker::onPollTimer()
{
    QMutexLocker lock(&m_queueMutex);

    // 上一轮轮询/发现尚未消化完则跳过本 tick，防止队列无限膨胀。
    for (const QueueItem &qi : m_queue) {
        if (qi.type == Poll || qi.type == Discover)
            return;
    }

    // 每个 tick 将本口全部设备入队, 保证所有设备按轮询周期刷新
    for (const PollTask &t : m_pollTasks) {
        QueueItem item;
        item.type = Poll;
        item.poll = t;
        m_queue.enqueue(item);
    }

    // 单板固定现场: 不做持续发现。m_discoveryActive 只在两种情况为真:
    // 1) 尚未发现任何子板 (启动后等待, 含串口迟到打开);
    // 2) 手动重扫触发的一轮完整扫描 (按 m_discoveryProbesRemaining 计数)。
    // 外扩输入 0x000E 已在主轮询读段内, 不再需要独立快速轮询。
    if (m_discoveryActive) {
        const int discoveryBudget = 8;
        int queuedDiscoveries = 0;
        int checkedAddresses = 0;
        while (queuedDiscoveries < discoveryBudget && checkedAddresses < 247
               && (m_discoveryUntilFirstFound || m_discoveryProbesRemaining > 0)) {
            const int slaveId = m_nextDiscoverySlaveId;
            m_nextDiscoverySlaveId = m_nextDiscoverySlaveId == 247
                ? 1 : m_nextDiscoverySlaveId + 1;
            ++checkedAddresses;
            if (!m_discoveryUntilFirstFound)
                --m_discoveryProbesRemaining;

            bool known = false;
            for (const PollTask &task : m_pollTasks) {
                if (task.deviceKey.slaveId == slaveId) {
                    known = true;
                    break;
                }
            }
            if (known)
                continue;

            QueueItem item;
            item.type = Discover;
            item.discoverySlaveId = slaveId;
            m_queue.enqueue(item);
            ++queuedDiscoveries;
        }
        if (!m_discoveryUntilFirstFound && m_discoveryProbesRemaining <= 0)
            m_discoveryActive = false;
    }

    if (!m_busy)
        m_queueTimer->start(0);
}

void SerialPortWorker::processQueue()
{
    // 串口断开 (启动过早/拔插/对端退出): 自动重开, 2 秒退避后重试。
    // 必须在取任务之前处理, 队列里的写任务才不会因提前返回而丢失。
    if (m_reopenPending) {
        m_reopenPending = false;
        closePort();
    }
    if (!m_serial->isOpen()) {
        if (!openPort()) {
            if (!m_portAnnounced) {
                m_portAnnounced = true;
                emit portError(m_settings.portIndex,
                               QString::fromUtf8("无法打开串口: %1")
                                   .arg(m_settings.device));
            }
            m_queueTimer->start(2000);
            return;
        }
        m_portAnnounced = false;
    }

    QueueItem item;
    {
        QMutexLocker lock(&m_queueMutex);
        if (m_queue.isEmpty()) {
            m_busy = false;
            return;
        }
        m_busy = true;
        item = m_queue.dequeue();
    }

    if (item.type == Poll) {
        const PollTask &t = item.poll;

        // 协议寄存器分散在多个区, 逐段 0x03 读取后合并
        // 旧 firmware 可能不支持新地址段，允许部分段失败，只要有任何一段成功即认为在线
        QMap<QString, QVariant> values;
        bool anySuccess = false;
        for (const DeviceProfile::ReadSegment &seg : t.regMap.readSegments) {
            ModbusRtu::Result r = ModbusRtu::readHoldingRegisters(
                [this](const QByteArray &req, quint8 fc) { return transact(req, fc); },
                static_cast<quint8>(t.deviceKey.slaveId),
                seg.startAddr,
                seg.count);
            if (r.success) {
                anySuccess = true;
                DeviceProfile::parseSegment(seg.startAddr, r.registers, values);
            }
        }

        if (anySuccess)
            emit deviceDataReady(t.deviceKey, values, true);
        else
            emit deviceDataReady(t.deviceKey, {}, false);

        // 从站间隔，避免连续占用总线
        m_queueTimer->start(m_settings.interSlaveDelayMs);
    } else if (item.type == Discover) {
        const ModbusRtu::Result result = ModbusRtu::readHoldingRegisters(
            [this](const QByteArray &req, quint8 fc) {
                return transact(req, fc, 150);
            },
            static_cast<quint8>(item.discoverySlaveId),
            DeviceProfile::RegHvInput,
            1);
        if (result.success) {
            DeviceProfile::DeviceKey key;
            key.portIndex = m_settings.portIndex;
            key.slaveId = item.discoverySlaveId;
            emit deviceDataReady(key, {}, true);
            if (m_discoveryUntilFirstFound)
                m_discoveryActive = false;
        }
        m_queueTimer->start(m_settings.interSlaveDelayMs);
    } else {
        const WriteTask &t = item.write;
        const QVector<DeviceProfile::WriteItem> writeItems =
            DeviceProfile::encodeWriteValues(t.deviceType, t.fields);

        ModbusRtu::Result r;
        if (writeItems.isEmpty()) {
            r.success = false;
            r.error = QString::fromUtf8("无有效写入字段");
        } else {
            // 协议规定写统一用 0x10, 单寄存器也走写多个
            for (const DeviceProfile::WriteItem &w : writeItems) {
                // 现场下位机在收到其他从站地址的报文后，若直接对本机
                // 发 0x10 会不回应；先对目标地址成功读一次即可恢复。
                // 写前读同一段同时也确认目标从站当前在线。
                r = ModbusRtu::readHoldingRegisters(
                    [this](const QByteArray &req, quint8 fc) {
                        return transact(req, fc);
                    },
                    static_cast<quint8>(t.deviceKey.slaveId),
                    w.startAddr,
                    static_cast<quint16>(w.values.size()));
                if (!r.success) {
                    r.error = QString::fromUtf8("写前同步失败: %1").arg(r.error);
                    break;
                }

                // 从其他地址超时切回目标从站时，某些现场转换器/下位机
                // 可能丢失第一个写回复。OT 写入是“设置值”语义，重复写同值
                // 是幂等的，因此失败后允许一次延时重试。
                const QVector<quint16> valuesToWrite =
                    DeviceProfile::applyBitmaskFields(w.startAddr, r.registers, t.fields);

                for (int attempt = 0; attempt < 2; ++attempt) {
                    r = ModbusRtu::writeMultipleRegisters(
                        [this](const QByteArray &req, quint8 fc) {
                            return transact(req, fc);
                        },
                        static_cast<quint8>(t.deviceKey.slaveId),
                        w.startAddr,
                        valuesToWrite);
                    if (r.success)
                        break;
                    if (attempt == 0) {
                        QThread::msleep(static_cast<unsigned long>(
                            qMax(m_settings.frameDelayMs,
                                 m_settings.interSlaveDelayMs)));
                    }
                }
                if (!r.success)
                    break;
            }
        }

        emit writeFinished(t.deviceKey, r.success, r.error);
        m_queueTimer->start(m_settings.interSlaveDelayMs);
    }

    // 继续处理队列
    {
        QMutexLocker lock(&m_queueMutex);
        if (!m_queue.isEmpty())
            return; // queueTimer 会在 interSlaveDelay 后再次触发
        m_busy = false;
    }
}

ModbusRtu::Result SerialPortWorker::transact(const QByteArray &request,
                                              quint8 expectedFc,
                                              int timeoutMs)
{
    ModbusRtu::Result result;
    const int transactionTimeout = timeoutMs > 0 ? timeoutMs : m_settings.timeoutMs;
    if (!m_serial->isOpen()) {
        result.error = QString::fromUtf8("串口未打开");
        return result;
    }

    m_rxBuffer.clear();
    // waitForReadyRead() 超时后 QSerialPort 会保留 TimeoutError。
    // 如果不在下一个事务前清除，后续等待可能立即失败，
    // 典型表现是“轮询离线地址超时后，在线地址也写超时”。
    m_serial->clear(QSerialPort::Input);
    m_serial->clearError();

    // RTU 帧前静默
    QThread::msleep(static_cast<unsigned long>(m_settings.frameDelayMs));

    if (m_serial->write(request) != request.size()) {
        // 底层失效 (对端退出/拔插): 标记重开, 由 processQueue 恢复
        m_reopenPending = true;
        result.error = QString::fromUtf8("发送失败");
        return result;
    }
    if (!m_serial->waitForBytesWritten(transactionTimeout)) {
        result.error = QString::fromUtf8("发送超时");
        return result;
    }

    // 等待响应
    const qint64 deadline = QDateTime::currentMSecsSinceEpoch() + transactionTimeout;
    while (QDateTime::currentMSecsSinceEpoch() < deadline) {
        if (m_serial->waitForReadyRead(50)) {
            m_rxBuffer.append(m_serial->readAll());
            QByteArray frame;
            if (ModbusFrame::extractFrame(m_rxBuffer, frame)) {
                if (expectedFc == ModbusFrame::ReadHoldingRegisters
                    || expectedFc == ModbusFrame::ReadInputRegisters) {
                    result.success = ModbusFrame::parseReadResponse(
                        frame,
                        static_cast<quint8>(request.at(0)),
                        expectedFc,
                        result.registers);
                } else {
                    result.success = ModbusFrame::parseWriteResponse(
                        frame,
                        static_cast<quint8>(request.at(0)),
                        expectedFc);
                }
                if (!result.success)
                    result.error = QString::fromUtf8("响应解析失败");
                return result;
            }
        }
    }

    result.error = QString::fromUtf8("接收超时");
    return result;
}

bool SerialPortWorker::openPort()
{
    m_serial->setPortName(m_settings.device);
    m_serial->setBaudRate(m_settings.baudRate);
    m_serial->setDataBits(static_cast<QSerialPort::DataBits>(m_settings.dataBits));
    m_serial->setParity(m_settings.parity);
    m_serial->setStopBits(m_settings.stopBits);
    m_serial->setFlowControl(QSerialPort::NoFlowControl);

    if (!m_serial->open(QIODevice::ReadWrite)) {
        qWarning() << "Open port failed:" << m_settings.device << m_serial->errorString();
        return false;
    }
    return true;
}

void SerialPortWorker::closePort()
{
    if (m_serial->isOpen())
        m_serial->close();
}

void SerialPortWorker::onSerialError(QSerialPort::SerialPortError error)
{
    // 设备级失效 (USB 拔插/PTY 对端退出) 触发重开;
    // 常规超时等错误走正常事务失败路径, 不在这里处理
    switch (error) {
    case QSerialPort::ResourceError:
    case QSerialPort::DeviceNotFoundError:
    case QSerialPort::PermissionError:
        m_reopenPending = true;
        break;
    default:
        break;
    }
}
