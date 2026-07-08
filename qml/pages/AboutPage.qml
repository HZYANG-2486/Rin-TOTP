import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

Item {
    id: aboutPage
    objectName: "AboutPage"

    property var i18n: I18n
    property string lang: aboutPage.i18n ? aboutPage.i18n.language : "zh_CN"
    property int langRev: aboutPage.i18n ? aboutPage.i18n.revision : 0
    function _t(key) { return aboutPage.i18n ? aboutPage.i18n.tr(key) : key }

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

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: contentColumn.implicitHeight + 40
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: contentColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 20
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 24

            ColumnLayout {
                spacing: 16
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter

                Rectangle {
                    width: 96
                    height: 96
                    radius: 24
                    color: "#605ed2"
                    Layout.alignment: Qt.AlignHCenter

                    Text {
                        anchors.centerIn: parent
                        text: "T"
                        font.pixelSize: 48
                        font.bold: true
                        color: "#ffffff"
                    }
                }

                Text {
                    text: aboutPage._t("app.title")
                    typography: Typography.Title
                    font.bold: true
                    color: aboutPage._isDarkTheme() ? "#ffffff" : "#000000"
                    Layout.alignment: Qt.AlignHCenter
                }

                Text {
                    text: aboutPage._t("app.subtitle")
                    typography: Typography.Body
                    color: aboutPage._isDarkTheme() ? "#bbbbbb" : "#666666"
                    Layout.alignment: Qt.AlignHCenter
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            Text {
                text: aboutPage._t("settings.data")
                typography: Typography.Subtitle
                font.bold: true
                color: aboutPage._isDarkTheme() ? "#ffffff" : "#000000"
                Layout.topMargin: 16
            }

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Button {
                        text: aboutPage._t("settings.export")
                        onClicked: window.showExportPwdDialog()
                    }
                    Button {
                        text: aboutPage._t("settings.import")
                        onClicked: window.showImportFileDialog()
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    Connections {
        target: aboutPage.i18n
        function onLanguageChanged() {
            aboutPage.langRev = aboutPage.i18n.revision
        }
    }
}