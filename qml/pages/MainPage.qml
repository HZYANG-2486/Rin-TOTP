import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

Item {
    id: mainPage
    objectName: "MainPage"

    property var i18n: I18n
    property string lang: mainPage.i18n ? mainPage.i18n.language : "zh_CN"
    property int langRev: mainPage.i18n ? mainPage.i18n.revision : 0
    function _t(key) { return mainPage.i18n ? mainPage.i18n.tr(key) : key }

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

    function refreshTexts() {
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: contentColumn.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: 0

            // ── Header ─────────────────────────────────────
            Rectangle {
                width: parent.width
                height: 56
                color: "transparent"

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    text: mainPage._t("header.codes")
                    typography: Typography.Title
                    font.bold: true
                    color: mainPage._isDarkTheme() ? "#ffffff" : "#000000"
                }

                Button {
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    text: mainPage._t("header.add")
                    highlighted: true
                    enabled: window.isUnlocked
                    onClicked: window.showAddEditDialog("")
                }
            }

            // ── Account cards ──────────────────────────────
            Repeater {
                model: totpModel ? totpModel : null

                Rectangle {
                    id: cardItem
                    width: contentColumn.width
                    height: 92
                    color: mainPage._isDarkTheme() ? "#1a1a1a" : "#ffffff"

                    MouseArea {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: parent.width - 110
                        onDoubleClicked: {
                            Backend.toggleCardMode(model.accountId)
                            if (cardItem && cardItem.parent) {
                                var page = cardItem.parent.parent
                                if (page && page.parent && page.parent.notifBar) {
                                    page = page.parent
                                    page.notifBar.show(page._t("menu.detach"),
                                        model.cardMode ? page._t("notif.card_off") : page._t("notif.card_on"))
                                }
                            }
                        }
                    }

                    // Bottom divider
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 1
                        color: mainPage._isDarkTheme() ? "#333333" : "#eeeeee"
                    }

                    // Card mode indicator
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 3
                        color: model.cardMode ? "#605ed2" : "transparent"
                    }

                    // ── Left: issuer, name, code ──────────
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        width: parent.width - 130
                        spacing: 2

                        Text {
                            text: model.issuer || "Unknown"
                            font.bold: true
                            font.pixelSize: 14
                            color: mainPage._isDarkTheme() ? "#ffffff" : "#000000"
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        Text {
                            text: model.name
                            font.pixelSize: 12
                            color: mainPage._isDarkTheme() ? "#bbbbbb" : "#555555"
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        Text {
                            text: model.code
                            font.family: "Consolas, Monaco, Courier New, monospace"
                            font.pixelSize: 26
                            font.bold: true
                            color: model.timeRemaining <= 5 ? "#d93025" : "#605ed2"
                            width: parent.width
                        }
                    }

                    // ── Right: progress, time, buttons ────
                    Column {
                        anchors.right: parent.right
                        anchors.rightMargin: 15
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        width: 92
                        spacing: 4

                        ProgressBar {
                            width: parent.width
                            from: 0
                            to: 1
                            value: 1 - model.progress
                        }

                        Text {
                            text: model.timeRemaining + "s"
                            font.pixelSize: 12
                            color: model.timeRemaining <= 5 ? "#d93025" : (mainPage._isDarkTheme() ? "#bbbbbb" : "#666666")
                            anchors.right: parent.right
                        }

                        Row {
                            anchors.right: parent.right
                            spacing: 4

                            Button {
                                id: copyBtn
                                text: mainPage._t("button.copy")
                                width: 58
                                height: 26
                                onClicked: {
                                    Backend.copyCode(model.accountId)
                                    copyBtn.text = mainPage._t("button.copied")
                                    copyResetTimer.restart()
                                }
                                Timer {
                                    id: copyResetTimer
                                    interval: 1500
                                    repeat: false
                                    onTriggered: copyBtn.text = mainPage._t("button.copy")
                                }
                            }

                            Button {
                                flat: true
                                text: "⋯"
                                width: 28
                                height: 26
                                onClicked: itemMenu.popup()
                            }
                        }
                    }

                    // ── Context menu ──────────────────────
                    Menu {
                        id: itemMenu
                        MenuItem {
                            text: mainPage._t("menu.edit")
                            onTriggered: window.showAddEditDialog(model.accountId)
                        }
                        MenuItem {
                            text: model.cardMode ? mainPage._t("menu.reattach") : mainPage._t("menu.detach")
                            onTriggered: Backend.toggleCardMode(model.accountId)
                        }
                        MenuSeparator {}
                        MenuItem {
                            text: mainPage._t("menu.delete")
                            onTriggered: {
                                window.pendingDeleteId = model.accountId
                                window.showDeleteConfirmDialog()
                            }
                        }
                    }
                }
            }

            // ── Empty state ────────────────────────────────
            Text {
                width: parent.width
                height: 100
                text: (totpModel && totpModel.count === 0 && window.isUnlocked)
                    ? mainPage._t("empty.title") + "\n" + mainPage._t("empty.subtitle")
                    : ""
                color: mainPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 14
            }
        }
    }

    // ── Notification bar ─────────────────────────────────
    Rectangle {
        id: notifBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 36
        color: "#605ed2"
        visible: false
        z: 100

        property string notifTitle: ""
        property string notifMessage: ""

        Text {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            verticalAlignment: Text.AlignVCenter
            color: "#ffffff"
            text: notifBar.notifTitle.length > 0
                ? notifBar.notifTitle + ": " + notifBar.notifMessage
                : notifBar.notifMessage
            elide: Text.ElideRight
        }

        Timer {
            id: notifTimer
            interval: 2500
            repeat: false
            onTriggered: notifBar.visible = false
        }

        function show(title, message) {
            notifTitle = title
            notifMessage = message
            visible = true
            notifTimer.restart()
        }
    }

    Connections {
        target: Backend
        function onNotification(title, message) {
            notifBar.show(title, message)
        }
    }

    // Refresh UI when language changes
    Connections {
        target: mainPage.i18n
        function onLanguageChanged() {
            mainPage.langRev = mainPage.i18n.revision
            mainPage.refreshTexts()
        }
    }
}
