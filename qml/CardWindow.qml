import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

// Frameless, always-on-top desktop card for a single TOTP account.
Window {
    id: card

    property string accountId: ""
    property string issuerText: ""
    property string nameText: ""
    property int period: 30
    property int cardX: -1
    property int cardY: -1

    property string codeText: "------"
    property string rawCode: ""
    property int timeRemaining: 0
    property real progressValue: 0

    property var backend: null

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    width: 220
    height: 130
    color: "transparent"
    visible: false

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

    Component.onCompleted: {
        if (cardX >= 0 && cardY >= 0) {
            card.x = cardX
            card.y = cardY
        } else {
            var hash = 0
            for (var i = 0; i < accountId.length; i++) {
                hash = (hash * 31 + accountId.charCodeAt(i)) & 0x7fffffff
            }
            card.x = (hash % 4) * 30 + 80
            card.y = ((hash >> 4) % 4) * 30 + 80
        }
        card.show()
    }

    // Shadow / card body
    Rectangle {
        id: body
        anchors.fill: parent
        radius: 12
        color: card._isDarkTheme() ? "#cc1a1a1a" : "#ffffff"
        border.color: card._isDarkTheme() ? "#333333" : "#dddddd"
        border.width: 1

        // Shadow effect
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: 14
            color: "transparent"
            border.color: card._isDarkTheme() ? Qt.rgba(0, 0, 0, 0.3) : Qt.rgba(0, 0, 0, 0.15)
            border.width: 4
            z: -1
        }

        // Subtle accent on the left edge
        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 3
            color: "#605ed2"
            radius: 2
        }

        MouseArea {
            id: dragArea
            anchors.fill: parent
            cursorShape: Qt.SizeAllCursor
            propagateComposedEvents: false
            onPressed: function(mouse) {
                card.startSystemMove()
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 4

            // Header: issuer + close button
            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: card.issuerText
                    typography: Typography.BodyStrong
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: card._isDarkTheme() ? "#ffffff" : "#000000"
                }

                // Close button
                Rectangle {
                    width: 18
                    height: 18
                    radius: 4
                    color: closeMa.containsMouse
                        ? (card._isDarkTheme() ? "#333333" : "#eeeeee")
                        : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 10
                        color: card._isDarkTheme() ? "#bbbbbb" : "#666666"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        z: 1
                        onClicked: {
                            if (card.backend) {
                                card.backend.hideCard(card.accountId)
                            }
                        }
                    }
                }
            }

            // Account name
            Text {
                text: card.nameText
                typography: Typography.Caption
                color: card._isDarkTheme() ? "#bbbbbb" : "#555555"
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            // The TOTP code
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: codeLabel.font.pixelSize + 8
                z: 1

                Text {
                    id: codeLabel
                    anchors.fill: parent
                    text: card.codeText
                    font.family: "Consolas, Monaco, Courier New, monospace"
                    font.pixelSize: 26
                    font.bold: true
                    color: card.timeRemaining <= 5 ? "#d93025" : "#605ed2"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (card.backend) {
                                card.backend.copyCode(card.accountId)
                                copyFlash.visible = true
                                flashTimer.restart()
                            }
                        }
                    }
                }

                // Copy flash overlay
                Rectangle {
                    id: copyFlash
                    anchors.centerIn: parent
                    width: flashLabel.implicitWidth + 16
                    height: flashLabel.implicitHeight + 6
                    radius: 4
                    color: "#605ed2"
                    visible: false
                    opacity: 0.95

                    Text {
                        id: flashLabel
                        anchors.centerIn: parent
                        text: card._isDarkTheme() ? "Copied!" : "已复制!"
                        color: "#ffffff"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    Timer {
                        id: flashTimer
                        interval: 900
                        repeat: false
                        onTriggered: copyFlash.visible = false
                    }
                }
            }

            // Progress + time remaining
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    value: 1 - card.progressValue
                }

                Text {
                    text: card.timeRemaining + "s"
                    typography: Typography.Caption
                    color: card.timeRemaining <= 5 ? "#d93025" : (card._isDarkTheme() ? "#bbbbbb" : "#666666")
                }
            }
        }
    }
}
