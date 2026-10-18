#ifndef APPUI_H
#define APPUI_H

#include "applogic.h"
#include "controlalgorithm.h"

#include <QFrame>
#include <QMainWindow>
#include <QMap>
#include <QPoint>
#include <QSet>
#include <QThreadPool>
#include <QVector>
#include <QWidget>
#include <QDialog>

class QComboBox;
class QDateEdit;
class QDoubleSpinBox;
class QFrame;
class QLabel;
class QMouseEvent;
class QPushButton;
class QScrollBar;
class QGridLayout;
class QSlider;
class QSpinBox;
class QStackedWidget;
class QTableWidget;
class QTimer;

/** 总览页可点击状态卡片，显示运行模式、三个加热器档位和状态指示。 */
class OverviewCard : public QFrame
{
    Q_OBJECT
public:
    explicit OverviewCard(QWidget *parent = nullptr);

    void updateState(const DeviceState &state, bool automatic);

signals:
    void clicked();

protected:
    void mouseReleaseEvent(QMouseEvent *event) override;

private:
    QLabel *m_identity = nullptr;
    QLabel *m_mode = nullptr;
    QLabel *m_status = nullptr;
    QVector<QLabel *> m_measurements;
    QVector<QLabel *> m_heaters;
    QMap<int, QLabel *> m_indicators;
    // 手动模式告警长亮: 切到手动(自动温控没在保护)时报警灯 label 常带红色 ⚠ 前缀。
    // 曾经做成 500 ms 交替闪烁, 现场反馈"应该长亮"—— 闪是为了提醒, 但手动模式
    // 会持续很久(可能整个班次), 一直闪反而让人眼花, 且容易和真报警的闪烁混淆。
    bool m_manualMode = false;
    void refreshIndicatorLabels();
};

/** 所有已发现子板的可点击状态卡片总览。 */
class FleetOverviewPanel : public QWidget
{
    Q_OBJECT
public:
    explicit FleetOverviewPanel(DeviceManager *manager,
                                QWidget *parent = nullptr);

    void setAutoDevices(const QSet<int> &keys);

signals:
    void deviceActivated(const DeviceProfile::DeviceKey &key);

public slots:
    void refreshDevices();

private slots:
    void refreshDevice(const DeviceProfile::DeviceKey &key);

private:
    void refreshSummary();
    void updateCard(const DeviceState &state);

    DeviceManager *m_manager = nullptr;
    QLabel *m_summary = nullptr;
    QWidget *m_cardContainer = nullptr;
    QGridLayout *m_cardGrid = nullptr;
    QMap<int, OverviewCard *> m_cards;
    QSet<int> m_autoDevices;
};

/** 手动和自动页共用的子板选择与传感器数据卡片。 */
class DeviceOverviewWidget : public QWidget
{
    Q_OBJECT
public:
    explicit DeviceOverviewWidget(DeviceManager *manager, QWidget *parent = nullptr);

    DeviceProfile::DeviceKey currentDevice() const;
    DeviceState currentState() const;
    void selectDevice(const DeviceProfile::DeviceKey &key);

signals:
    void currentDeviceChanged(const DeviceProfile::DeviceKey &key);

public slots:
    void refreshDevices();
    void refreshDevice(const DeviceProfile::DeviceKey &key);
    /** 加热器档位 (key=portIndex*256+slaveId, 值 0=关闭 1=1档 2=2档 3=3档) */
    void setHeaterGearsForCurrent(int gearA, int gearB, int gearC);

private:
    void refreshValues();

    DeviceManager *m_manager = nullptr;
    QLabel *m_deviceTitle = nullptr;
    QComboBox *m_deviceBox = nullptr;
    QLabel *m_linkState = nullptr;
    QLabel *m_lastUpdate = nullptr;
    QMap<QString, QLabel *> m_values;
    struct HeaterStatusRow {
        QLabel *target = nullptr;
        QVector<QLabel *> boxes;
    };
    // 加热器状态卡: [加热器A, 加热器B, 加热器C] 目标温度 + 三个档位方框
    QVector<HeaterStatusRow> m_heaterStatus;
};

/** 按实际用途显示加热器、加热回路、状态指示和扩展设备。 */
class ManualPanel : public QWidget
{
    Q_OBJECT
public:
    explicit ManualPanel(DeviceManager *manager, QWidget *parent = nullptr);

    DeviceProfile::DeviceKey currentDevice() const;
    void setCurrentDevice(const DeviceProfile::DeviceKey &key);
    void setAutoDevices(const QSet<int> &keys);
    void refreshParameters();
    void refreshSettings();
    /** 推送各子板加热器档位 (key=portIndex*256+slaveId, 值 0~3) */
    void setHeaterGears(const QMap<int, int> &gears);

signals:
    void writeRequested(const DeviceProfile::DeviceKey &key,
                        const QMap<QString, QVariant> &fields);
    void runningChanged(const DeviceProfile::DeviceKey &key, bool running);
    /** 屏幕按键请求加热器进一档 (heaterIndex: 0=A 1=B 2=C) */
    void heaterCycleRequested(const DeviceProfile::DeviceKey &key, int heaterIndex);

private slots:
    void refreshControls();
    void toggleOutput();

private:
    DeviceManager *m_manager = nullptr;
    DeviceOverviewWidget *m_overview = nullptr;
    QLabel *m_operationBanner = nullptr;
    QLabel *m_runState = nullptr;
    QLabel *m_workState = nullptr;
    QLabel *m_averageTemp = nullptr;
    QLabel *m_autoSummary = nullptr;
    QPushButton *m_start = nullptr;
    QPushButton *m_stop = nullptr;
    QPushButton *m_ot3 = nullptr;
    QPushButton *m_ot4 = nullptr;
    QMap<QString, QPushButton *> m_spareOutputs;
    QMap<QString, QPushButton *> m_lightOutputs;
    QVector<QLabel *> m_expInLabels;
    QMap<QString, QPushButton *> m_expOutButtons;
    QSet<int> m_autoDevices;
    // 手动模式告警长亮: 切到手动(自动温控没在保护)时 runState 常带红底。
    // 曾经做成 500 ms 交替闪烁, 现场反馈"应该长亮" —— 手动模式会持续很久,
    // 一直闪既刺眼又容易和真报警混。
    bool m_manualMode = false;
    // 加热器手动按键与档位缓存 (key=portIndex*256+slaveId, 值 0~3)
    QMap<int, int> m_heaterGears;
    QVector<QPushButton *> m_heaterButtons;
};

/** 自动运行：状态监视、阈值摘要和启停。 */
class AutoPanel : public QWidget
{
    Q_OBJECT
public:
    explicit AutoPanel(DeviceManager *manager, QWidget *parent = nullptr);

    void setRunning(bool running);
    void refreshParameters();
    void setCurrentDevice(const DeviceProfile::DeviceKey &key);

signals:
    void runningChanged(bool running);

private slots:
    void refreshState();

private:
    DeviceManager *m_manager = nullptr;
    DeviceOverviewWidget *m_overview = nullptr;
    QLabel *m_runState = nullptr;
    QLabel *m_workState = nullptr;
    QLabel *m_averageTemp = nullptr;
    QLabel *m_ruleText = nullptr;
    QPushButton *m_start = nullptr;
    QPushButton *m_stop = nullptr;
    bool m_running = false;
};

/** 历史数据折线图，不引入 Qt Charts，便于 RK3568 部署。 */
class HistoryChart : public QWidget
{
    Q_OBJECT
public:
    explicit HistoryChart(QWidget *parent = nullptr);
    void setRecords(const QVector<HistoryQuery::Record> &records);
    void appendRecord(const HistoryQuery::Record &record);
    void refreshRecords();
    /** 实时模式: 裁掉 cutoff 之前的点, 正在查看的十字线随记录一起左移 */
    void trimRecords(const QDateTime &cutoff);
    int recordCount() const { return m_records.size(); }
    int visiblePointCount() const;
    int maxViewStart() const;
    int viewStart() const { return m_viewStart; }
    /** 图例栏就是序列开关: 点一下藏起该条曲线, 再点一下恢复 */
    void toggleSeriesVisible(int index);
    bool isSeriesVisible(int index) const;
    // 上一次绘制算出的曲线上标签框(按可见序列顺序), 供测试校验"有几条曲线
    // 就有几个标签"以及"标签之间不互相遮挡"
    QVector<QRectF> labelBoxes() const { return m_labelBoxes; }
    // 上一次绘制算出的图例栏: 栏矩形与对应序列一一对应, 含被用户藏起来的
    // 序列 —— 图例必须留着, 否则藏过的曲线点不回来
    QVector<QRectF> legendBoxes() const { return m_legendBoxes; }
    QVector<int> legendSeries() const { return m_legendSeries; }
    void followLatest();

public slots:
    void setViewStart(int start);

signals:
    void viewStartChanged(int start);
    void inspectionChanged(const QString &summary);

protected:
    void paintEvent(QPaintEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;

private:
    void inspectAtX(int x);
    void refreshAfterRecordsChanged(bool keepCrosshair = false);
    /** 图例栏命中测试: 命中返回栏序号, 未命中返回 -1 */
    int legendIndexAt(const QPoint &pos) const;

    QVector<HistoryQuery::Record> m_records;
    QVector<QRectF> m_labelBoxes;   // 仅供 labelBoxes() 测试读取
    QVector<bool> m_seriesHidden;   // 按序列下标, true=用户点图例藏起该曲线
    QVector<int> m_legendSeries;    // 图例栏对应的序列下标(数据有效的全部)
    QVector<QRectF> m_legendBoxes;  // 图例栏矩形, 与 m_legendSeries 一一对应
    int m_pressedLegend = -1;       // 按下的图例栏序号(触摸高亮), -1=无
    int m_viewStart = 0;
    int m_crosshairRecordIndex = -1;
    int m_dragViewStart = 0;
    QPoint m_dragOrigin;
    bool m_dragging = false;
    bool m_followLatest = true;
};

/** 历史数据：按日期和子板查询，同时显示曲线与明细。 */
class HistoryWidget : public QWidget
{
    Q_OBJECT
public:
    explicit HistoryWidget(HistoryQuery *query,
                           DeviceManager *manager,
                           QWidget *parent = nullptr);
    ~HistoryWidget() override;

public slots:
    void activate();
    void refreshDevices();
    void reloadDevices();
    void onDataFilesChanged();
    void queryRecords();
    void onRecordAppended(const QDateTime &timestamp,
                          const DeviceProfile::DeviceKey &key,
                          const QString &deviceName,
                          DeviceProfile::DeviceType type,
                          const QMap<QString, QVariant> &values);
    void onQueryPoll();
    /** 顶部"实时数据"按钮: 进入后只看最近一段时间并持续跟随最新,
     *  不受日期筛选(23:59:59 换日)限制; 退出后恢复原查询区间。 */
    void setLiveMode(bool live);

private:
    void loadRecords(bool resetToLatest);
    /** 实时模式: 把窗口外的旧点从内存记录与图表里一起裁掉 */
    void trimLiveRecords(const QDateTime &cutoff);
    void updateTimeScroll();
    void setTableRow(int row, const HistoryQuery::Record &record);
    QString deviceIndexPath() const;
    bool loadDeviceIndex();
    void saveDeviceIndex();

    HistoryQuery *m_query = nullptr;
    DeviceManager *m_manager = nullptr;
    QDateEdit *m_dateFrom = nullptr;
    QDateEdit *m_dateTo = nullptr;
    QComboBox *m_deviceBox = nullptr;
    QLabel *m_resultSummary = nullptr;
    QLabel *m_crosshairInfo = nullptr;
    HistoryChart *m_chart = nullptr;
    QScrollBar *m_timeScroll = nullptr;
    QTableWidget *m_table = nullptr;
    QMap<QPair<int, int>, QString> m_historicalDevices;
    QVector<HistoryQuery::Record> m_chartRecords;
    int m_rawRecordCount = 0;
    bool m_loaded = false;
    bool m_deviceIndexLoaded = false;
    QDate m_loadedDateFrom;
    QDate m_loadedDateTo;
    QString m_loadedDevice;
    bool m_liveAppendPaused = false;
    bool m_pendingResetToLatest = false;
    // 实时数据模式: 日期筛选被强制为今天并禁用, 退出时恢复原区间
    bool m_liveMode = false;
    QDate m_historyDateFrom;
    QDate m_historyDateTo;
    // 后台查询共享状态: 工作线程写入, UI 线程轮询取走, 部件销毁后
    // 共享状态仍被线程安全持有, 无生命周期风险
    struct QueryState {
        QMutex mutex;
        bool done = false;
        HistoryQuery::DisplayResult result;
    };
    QSharedPointer<QueryState> m_queryState;
    QTimer *m_queryPollTimer = nullptr;
    QThreadPool m_queryPool;
};

/** 参数设置与扩展设置分别显示各自负责的配置。 */
class SettingsWidget : public QWidget
{
    Q_OBJECT
public:
    /** advancedOnly=true 时显示运维、联锁及扩展配置，否则显示温控参数。 */
    explicit SettingsWidget(StorageRotator *rotator, bool advancedOnly = false,
                            QWidget *parent = nullptr);
    void showActionFeedback(const QString &message, bool success);
    void refreshStorageInfo();
    bool confirmLeavingPage();

signals:
    void settingsSaved();
    void rescanRequested();
    void dataFilesChanged();
    void brightnessPreview(int percent);

public slots:
    void updateExpInputStates(const QMap<QString, QVariant> &values);

private slots:
    bool saveSettings();
    void deleteOldData();

private:
    bool eventFilter(QObject *watched, QEvent *event) override;

    QMap<QWidget *, QVariant> settingsValues() const;
    QMap<QWidget *, QVariant> m_savedControlValues;

    StorageRotator *m_rotator = nullptr;
    QComboBox *m_controlMode = nullptr;
    QComboBox *m_targetSource = nullptr;
    QDoubleSpinBox *m_heaterTargetA = nullptr;
    QDoubleSpinBox *m_heaterTargetB = nullptr;
    QDoubleSpinBox *m_heaterTargetC = nullptr;
    QDoubleSpinBox *m_thresholdSingleStage = nullptr;
    QDoubleSpinBox *m_thresholdSecondStage = nullptr;
    QDoubleSpinBox *m_thresholdDualStage = nullptr;
    QDoubleSpinBox *m_thresholdHysteresis = nullptr;
    QDoubleSpinBox *m_pidKp = nullptr;
    QDoubleSpinBox *m_pidKi = nullptr;
    QDoubleSpinBox *m_pidKd = nullptr;
    QDoubleSpinBox *m_pidSingleStage = nullptr;
    QDoubleSpinBox *m_pidSecondStage = nullptr;
    QDoubleSpinBox *m_pidDualStage = nullptr;
    QComboBox *m_pidFirstStageOutput = nullptr;
    QDoubleSpinBox *m_dewPointSingleStage = nullptr;
    QDoubleSpinBox *m_dewPointSecondStage = nullptr;
    QDoubleSpinBox *m_dewPointDualStage = nullptr;
    QDoubleSpinBox *m_dewPointHysteresis = nullptr;
    QDoubleSpinBox *m_humidityTemperatureLimit = nullptr;
    QLabel *m_humidityFormula = nullptr;
    QComboBox *m_displayTheme = nullptr;
    QComboBox *m_highVoltageDetectionMode = nullptr;
    QComboBox *m_highVoltageDigitalTrigger = nullptr;
    QDoubleSpinBox *m_highVoltageThreshold = nullptr;
    QSpinBox *m_relaySwitchInterval = nullptr;
    QDoubleSpinBox *m_pollInterval = nullptr;
    QDoubleSpinBox *m_recordInterval = nullptr;
    QSlider *m_brightnessSlider = nullptr;
    QLabel *m_brightnessValue = nullptr;
    QSpinBox *m_idleDimMinutes = nullptr;
    QSpinBox *m_idleDimPercent = nullptr;
    // 外扩输入接入配置: 每行一个功能下拉 + 一个实时状态标签
    QMap<int, QComboBox *> m_expInCombos;
    QMap<int, QLabel *> m_expInStateLabels;
    // 加热器输出映射: 每行一个 OT 继电器对下拉
    QMap<int, QComboBox *> m_heaterPairCombos;
    // 操作提示音开关 (蜂鸣器确认音)
    QComboBox *m_soundFeedback = nullptr;
    QSpinBox *m_maxStorageGB = nullptr;
    QSpinBox *m_deleteAge = nullptr;
    QComboBox *m_deleteAgeUnit = nullptr;
    QMap<int, QComboBox *> m_spareOutputModes;
    QLabel *m_storageSummary = nullptr;
    QLabel *m_deleteDateReference = nullptr;
    QLabel *m_formula = nullptr;
    QLabel *m_actionFeedback = nullptr;
    QTimer *m_feedbackTimer = nullptr;
    bool m_advancedOnly = false;

    QDate deleteCutoffDate() const;
};

/** 关于本机信息页。 */
class AboutWidget : public QWidget
{
    Q_OBJECT
public:
    explicit AboutWidget(QWidget *parent = nullptr);

    /**
     * 刷新本机网络信息 (IP / MAC)。
     * 现场屏多为 DHCP, 地址可能变化, 因此每次进入本页都重新取,
     * 而不是在构造时固化成一个可能过期的值。
     */
    void refreshNetworkInfo();

private:
    QLabel *m_networkInterfaceLabel = nullptr;
    QLabel *m_ipLabel = nullptr;
    QLabel *m_macLabel = nullptr;
};

/**
 * 设置页密码对话框。
 * 现场为纯触摸屏、无鼠标, 因此自带大按钮数字小键盘, 不依赖系统输入法;
 * 输满 6 位即自动校验, 错误则清空重输, 避免多余的一次确认点击。
 */
class PasswordDialog : public QDialog
{
    Q_OBJECT
public:
    explicit PasswordDialog(QWidget *parent = nullptr,
                            const QString &expected = QString());

    /** 弹出密码框, 校验通过返回 true (密码由调用方给定, 错误可重试)。 */
    static bool verify(QWidget *parent, const QString &expected);

private:
    void appendDigit(const QString &digit);
    void backspace();
    void clearInput();
    void submit();
    void refreshDisplay();

    QLabel *m_display = nullptr;
    QLabel *m_hint = nullptr;
    QString m_expected;
    QString m_entered;
};

/**
 * 顶部"实时数据"左侧的呼吸指示灯: 有数据流入时持续渐变闪烁。
 * 用自绘小圆点而不是样式表 —— 样式表只能整块改色, 做不出渐变;
 * 也不用 QGraphicsOpacityEffect, 那个在 RK3562 上每帧都要重算图层合成。
 */
class LivePulseIndicator : public QWidget
{
    Q_OBJECT
public:
    explicit LivePulseIndicator(QWidget *parent = nullptr);

    /** true = 正在接收实时数据 (呼吸); false = 静止隐藏 */
    void setActive(bool active);
    bool isActive() const { return m_active; }

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QTimer m_timer;
    qreal m_phase = 0.0;
    bool m_active = false;
};

/** 1024x600 触摸屏主窗口。 */
class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private slots:
    void switchPage(int index);
    void writeToDevice(const DeviceProfile::DeviceKey &key,
                       const QMap<QString, QVariant> &fields);
    void setDeviceAutoRunning(const DeviceProfile::DeviceKey &key, bool running);
    void cycleHeater(const DeviceProfile::DeviceKey &key, int heaterIndex);
    void onDeviceUpdated(const DeviceProfile::DeviceKey &key);
    void onWriteCompleted(const DeviceProfile::DeviceKey &key,
                          bool success,
                          const QString &error);
    void onSettingsSaved();
    void rescanDevices();
    void updateClock();

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    void setupUi();
    void startServices();
    void refreshIndicatorLights();
    /** 手动加热器连续工作满 2 小时强制休息 15 分钟, 并刷新顶部超持提示 */
    void tickHeaterWorkClocks();
    void refreshOverholdLabel();
    void syncAutoPanels();
    void applyAutomaticControl(const DeviceProfile::DeviceKey &key);
    void enterHighVoltageAlarm();
    void leaveHighVoltageAlarm();
    void evaluateSensorSelfCheck(const DeviceProfile::DeviceKey &key,
                                 const DeviceState &state);
    void enterSensorFault(const DeviceProfile::DeviceKey &key,
                          const QString &reason);
    void leaveSensorFault(const DeviceProfile::DeviceKey &key);
    void initializeSafeOutputs(const DeviceProfile::DeviceKey &key);
    void refreshHighVoltageAlarm();
    void addConfiguredSpareOutputs(const DeviceProfile::DeviceKey &key,
                                   QMap<QString, QVariant> &fields,
                                   const QMap<QString, QVariant> &currentValues =
                                       QMap<QString, QVariant>(),
                                   bool initializeManual = false) const;
    void refreshSystemState();
    void checkSystemTimeAnomaly();
    /** 操作确认音: 接在 OUT5 上的蜂鸣器闭合 0.2 秒; 无子板时回退软件音 */
    void beepConfirmation();
    void onBeepTimeout();
    /** 切到自动温控前: 三路加热器一律退到关闭 (继电器+灯), 清理档位会话 */
    void resetHeaterGears(const DeviceProfile::DeviceKey &key);
    /** 灯随输出状态同步: 任何来源 (手动/自动) 的档位变化都点亮对应灯 */
    void syncHeaterLamps(const DeviceProfile::DeviceKey &key,
                         const DeviceState &state);

    DeviceManager m_deviceManager;
    DataLogger m_logger;
    HistoryQuery m_historyQuery;
    StorageRotator m_rotator;
    PollScheduler *m_scheduler = nullptr;

    QStackedWidget *m_pages = nullptr;
    QVector<QPushButton *> m_navigation;
    FleetOverviewPanel *m_fleetOverview = nullptr;
    ManualPanel *m_manualPanel = nullptr;
    SettingsWidget *m_settingsWidget = nullptr;
    SettingsWidget *m_advancedWidget = nullptr;
    HistoryWidget *m_historyWidget = nullptr;
    AboutWidget *m_aboutWidget = nullptr;
    QLabel *m_pageTitle = nullptr;
    QLabel *m_clock = nullptr;
    QLabel *m_versionLabel = nullptr;
    QLabel *m_systemState = nullptr;
    QLabel *m_selfCheckNotice = nullptr;
    // 顶部"实时数据"开关: 所有页面都能看到并点击(在别的页点它 = 跳到数据
    // 浏览页并开启实时模式), 与自检 pill 同款外观
    QPushButton *m_realtimeButton = nullptr;
    // "实时数据"左侧的呼吸指示灯: 有数据流入时持续渐变
    LivePulseIndicator *m_livePulse = nullptr;
    // 距上次收到数据的毫秒数; 超过 kLivePulseIdleMs 视为"没有实时数据"
    qint64 m_livePulseIdleMs = 0;
    // "实时数据"左侧的手动超持提示 (手动加热器连续工作满 2 小时强制休息)
    QLabel *m_overholdLabel = nullptr;
    // 手动加热器连续工作计时 (key=commandKey*4+heaterIndex)
    // work=本轮连续工作秒数, rest=强制休息剩余秒数
    struct HeaterWorkClock {
        qint64 work = 0;
        qint64 rest = 0;
    };
    QMap<int, HeaterWorkClock> m_heaterClocks;
    QLabel *m_statusBar = nullptr;
    QSet<int> m_autoDevices;
    bool m_highVoltageAlarm = false;
    bool m_schedulerFault = false;
    bool m_timeAnomaly = false;
    BrightnessController *m_brightness = nullptr;
    QString m_configError;
    QDateTime m_startedAt;
    QMap<int, QPair<int, int>> m_lastAutoCommands;
    QMap<int, QDateTime> m_lastAutoCommandTimes;
    QMap<int, ControlAlgorithm::PidState> m_pidStates;
    QMap<int, QString> m_sensorFaults;
    // 加热器档位与外扩输入上一周期状态 (实体按键上升沿检测用)
    QMap<int, int> m_heaterGears;
    QMap<int, int> m_prevExpInMask;
    // 手自动开关: 上次驱动时刻 (开关与界面冲突时按开关纠正, 限流避免状态栏刷屏)
    QMap<int, qint64> m_lastManualAutoMs;
    QVector<int> m_appliedHeaterPairs;
    QSet<int> m_retiredHeaterPairs;
    // 蜂鸣器确认音: 待断开蜂鸣器的子板与断开定时器
    QList<DeviceProfile::DeviceKey> m_beepDevices;
    QTimer *m_beepOffTimer = nullptr;
    // 加热器灯上次同步的档位 (key=portIndex*256+slaveId)*4+heaterIndex
    QMap<int, int> m_lastLampGear;
    QMap<int, int> m_sensorRecoveryCounts;
    QSet<int> m_sensorHealthyDevices;
    QSet<int> m_initializedDevices;
};

#endif // APPUI_H
