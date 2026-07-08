import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

// Settings page - theme, language, close behavior, security options
Item {
    id: settingsPage
    objectName: "SettingsPage"

    property var i18n: I18n
    property string lang: settingsPage.i18n ? settingsPage.i18n.language : "zh_CN"
    property int langRev: settingsPage.i18n ? settingsPage.i18n.revision : 0
    function _t(key) { return settingsPage.i18n ? settingsPage.i18n.tr(key) : key }

    function _isDarkTheme() {
        var theme = Theme.currentTheme
        if (theme && theme.mode) {
            var modeStr = String(theme.mode)
            if (modeStr === "Dark" || modeStr === "dark" || modeStr === "1" || modeStr === "DarkMode") {
                return true
            }
        }
        if (theme && theme.colors && theme.colors.cardColor) {
            var cardColor = String(theme.colors.cardColor)
            if (cardColor.startsWith("#0d") || cardColor.startsWith("#0a") || cardColor.startsWith("#1a")) {
                return true
            }
        }
        return false
    }

    property string syncStatusColor: {
        if (Backend.timeOffset === 0) {
            return "#88cc88"
        } else if (Math.abs(Backend.timeOffset) <= 5) {
            return "#88cc88"
        } else if (Math.abs(Backend.timeOffset) <= 30) {
            return "#ffcc00"
        } else {
            return "#ff6666"
        }
    }

    property string syncStatusTextValue: {
        if (Backend.timeOffset === 0) {
            return settingsPage._t("settings.time_offset.normal")
        } else if (Backend.timeOffset > 0) {
            return settingsPage._t("settings.time_offset.ahead").replace("{offset}", Backend.timeOffset)
        } else {
            return settingsPage._t("settings.time_offset.behind").replace("{offset}", Math.abs(Backend.timeOffset))
        }
    }

    function refreshTexts() {
        var themeIdx = themeCombo.currentIndex
        themeCombo.model = [
            settingsPage._t("settings.theme.system"),
            settingsPage._t("settings.theme.light"),
            settingsPage._t("settings.theme.dark")
        ]
        themeCombo.currentIndex = themeIdx

        var effectIdx = effectCombo.currentIndex
        effectCombo.model = [
            settingsPage._t("settings.effect.acrylic"),
            settingsPage._t("settings.effect.mica"),
            settingsPage._t("settings.effect.none")
        ]
        effectCombo.currentIndex = effectIdx

        var langIdx = languageCombo.currentIndex
        languageCombo.model = languageCombo.langs.map(function(l) { return l.name })
        languageCombo.currentIndex = langIdx
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: settingsColumn.implicitHeight + 40
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: settingsColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 20
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 24

            // ── Appearance ───────────────────────────────────────────
            Text {
                text: settingsPage._t("settings.appearance")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                Text {
                    text: settingsPage._t("settings.theme")
                    typography: Typography.Body
                    color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                }
                ComboBox {
                    id: themeCombo
                    Layout.fillWidth: true
                    model: [
                        settingsPage._t("settings.theme.system"),
                        settingsPage._t("settings.theme.light"),
                        settingsPage._t("settings.theme.dark")
                    ]
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        if (currentIndex === 1) {
                            Theme.setTheme(Theme.mode.Light)
                        } else if (currentIndex === 2) {
                            Theme.setTheme(Theme.mode.Dark)
                        } else {
                            Theme.setTheme(Theme.mode.Auto)
                        }
                    }
                }

                Text {
                    text: settingsPage._t("settings.window_effect")
                    typography: Typography.Body
                    color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                }
                ComboBox {
                    id: effectCombo
                    Layout.fillWidth: true
                    model: [
                        settingsPage._t("settings.effect.acrylic"),
                        settingsPage._t("settings.effect.mica"),
                        settingsPage._t("settings.effect.none")
                    ]
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        if (currentIndex === 0) {
                            Theme.setBackdropEffect(Theme.effect.Acrylic)
                        } else if (currentIndex === 1) {
                            Theme.setBackdropEffect(Theme.effect.Mica)
                        } else {
                            Theme.setBackdropEffect(Theme.effect.None)
                        }
                    }
                }

                // Language picker
                Text {
                    text: settingsPage._t("settings.language")
                    typography: Typography.Body
                    color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                }
                RowLayout {
                    spacing: 8
                    Layout.fillWidth: true
                    ComboBox {
                        id: languageCombo
                        Layout.fillWidth: true
                        property var langs: settingsPage.i18n ? settingsPage.i18n.availableLanguages() : []
                        model: langs.map(function(l) { return l.name })
                        currentIndex: {
                            if (!settingsPage.i18n) return 0
                            var cur = settingsPage.i18n.isAuto() ? "auto" : settingsPage.i18n.currentLanguage()
                            for (var i = 0; i < langs.length; i++) {
                                if (langs[i].code === cur) return i
                            }
                            return 0
                        }
                    }
                    Button {
                        text: settingsPage._t("common.apply")
                        highlighted: true
                        onClicked: {
                            if (settingsPage.i18n && languageCombo.currentIndex >= 0 && languageCombo.currentIndex < languageCombo.langs.length) {
                                settingsPage.i18n.setLanguage(languageCombo.langs[languageCombo.currentIndex].code)
                            }
                        }
                    }
                }
            }

            // ── Security ────────────────────────────────────────────
            Text {
                text: settingsPage._t("settings.security")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Switch {
                        id: autoLockSwitch
                        checked: Backend.autoLock
                        onCheckedChanged: Backend.autoLock = checked
                    }
                    ColumnLayout {
                        Text {
                            text: settingsPage._t("settings.auto_lock")
                            typography: Typography.Body
                            color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                        }
                        Text {
                            text: settingsPage._t("settings.auto_lock.desc")
                            typography: Typography.Caption
                            color: settingsPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                        }
                    }
                }

                Button {
                    text: settingsPage._t("settings.change_password")
                    onClicked: window.showChangePwdDialog()
                }
            }

            // ── Close behavior ─────────────────────────────────────
            Text {
                text: settingsPage._t("settings.behavior")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Switch {
                        id: askOnCloseSwitch
                        checked: Backend.askOnClose
                        onCheckedChanged: Backend.askOnClose = checked
                    }
                    ColumnLayout {
                        Text {
                            text: settingsPage._t("settings.close_ask")
                            typography: Typography.Body
                            color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                        }
                        Text {
                            text: settingsPage._t("settings.close_ask.desc")
                            typography: Typography.Caption
                            color: settingsPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                        }
                    }
                }
            }

            // ── Time calibration ─────────────────────────────────
            Text {
                text: settingsPage._t("settings.time_sync")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Text {
                        text: settingsPage._t("settings.time_offset")
                        typography: Typography.Body
                        color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        spacing: 4

                        Button {
                            text: "-"
                            flat: true
                            onClicked: {
                                var newVal = Backend.timeOffset - 1
                                if (newVal >= -300) Backend.timeOffset = newVal
                            }
                        }
                        Text {
                            text: {
                                var v = Backend.timeOffset
                                if (v > 0) return "+" + v + " s"
                                return v + " s"
                            }
                            typography: Typography.Body
                            color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                            Layout.minimumWidth: 60
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Button {
                            text: "+"
                            flat: true
                            onClicked: {
                                var newVal = Backend.timeOffset + 1
                                if (newVal <= 300) Backend.timeOffset = newVal
                            }
                        }
                    }
                }

                Text {
                    text: settingsPage._t("settings.time_offset.desc")
                    typography: Typography.Caption
                    color: settingsPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                // NTP Server selection
                Text {
                    text: settingsPage._t("settings.ntp_server")
                    typography: Typography.Body
                    color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                }

                RowLayout {
                    spacing: 8
                    Layout.fillWidth: true

                    ComboBox {
                        id: ntpServerCombo
                        Layout.fillWidth: true
                        property var servers: Backend.ntpServers()
                        model: servers.map(function(s) { return s.display })
                        property var currentServerName: Backend.ntpServer
                        currentIndex: {
                            var name = currentServerName
                            for (var i = 0; i < servers.length - 1; i++) {
                                if (servers[i].name === name) return i
                            }
                            return servers.length - 1 // custom
                        }
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < servers.length - 1) {
                                customServerField.visible = false
                                Backend.ntpServer = servers[currentIndex].name
                            } else if (currentIndex === servers.length - 1) {
                                customServerField.visible = true
                            }
                        }
                    }

                    TextField {
                        id: customServerField
                        Layout.fillWidth: true
                        visible: ntpServerCombo.currentIndex === ntpServerCombo.servers.length - 1
                        placeholderText: settingsPage._t("settings.ntp_server.placeholder")
                        text: Backend.ntpServer
                        onAccepted: {
                            if (text.trim().length > 0) {
                                Backend.ntpServer = text.trim()
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: 8
                    Layout.fillWidth: true
                    Button {
                        id: syncButton
                        text: settingsPage._t("settings.sync_ntp")
                        onClicked: Backend.syncTimeNtp()
                        Connections {
                            target: Backend
                            function onSyncingTime(syncing) {
                                syncButton.enabled = !syncing
                                syncButton.text = syncing ? settingsPage._t("settings.syncing") : settingsPage._t("settings.sync_ntp")
                            }
                        }
                    }
                    Button {
                        text: settingsPage._t("settings.reset_time")
                        flat: true
                        onClicked: Backend.timeOffset = 0
                    }
                }

                // Sync status indicator
                RowLayout {
                    spacing: 6
                    Layout.fillWidth: true
                    Layout.topMargin: 4

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: syncStatusColor
                        visible: Backend.timeOffset !== 0
                    }

                    Text {
                        id: syncStatusText
                        text: syncStatusTextValue
                        typography: Typography.Caption
                        color: syncStatusColor
                        visible: Backend.timeOffset !== 0
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Text {
                        text: settingsPage._t("settings.time_offset.normal")
                        typography: Typography.Caption
                        color: settingsPage._isDarkTheme() ? "#88cc88" : "#2d8a2d"
                        visible: Backend.timeOffset === 0
                    }
                }
            }

            // ── Data ───────────────────────────────────────────────
            Text {
                text: settingsPage._t("settings.data")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Button {
                        text: settingsPage._t("settings.export")
                        onClicked: window.showExportPwdDialog()
                    }
                    Button {
                        text: settingsPage._t("settings.import")
                        onClicked: window.showImportFileDialog()
                    }
                }
            }

            // ── About ──────────────────────────────────────────────
            Text {
                text: settingsPage._t("settings.about")
                typography: Typography.Subtitle
                font.bold: true
                color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 8
                Layout.fillWidth: true

                Text {
                    text: settingsPage._t("app.title")
                    typography: Typography.BodyStrong
                    color: settingsPage._isDarkTheme() ? "#ffffff" : "#000000"
                }
                Text {
                    text: settingsPage._t("app.subtitle")
                    typography: Typography.Caption
                    color: settingsPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Button {
                    text: settingsPage._t("settings.about_more")
                    flat: true
                    onClicked: window.showAboutDialog()
                }
            }

            // Spacer
            Item { Layout.fillHeight: true }
        }
    }

    // Refresh UI when language changes
    Connections {
        target: settingsPage.i18n
        function onLanguageChanged() {
            settingsPage.langRev = settingsPage.i18n.revision
            settingsPage.refreshTexts()
        }
    }
}
