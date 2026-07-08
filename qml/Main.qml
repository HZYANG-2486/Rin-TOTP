import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import QtQuick.Window 2.15
import QtQuick.Dialogs
import RinUI
import "./pages/"

FluentWindow {
    id: window
    visible: true
    width: 720
    height: 560
    minimumWidth: 600
    minimumHeight: 480
    title: "PyTOTP Authenticator"

    property bool isUnlocked: !Backend.isLocked
    property string pendingDeleteId: ""
    property bool askOnClose: true

    property var i18n: I18n
    property string lang: window.i18n ? window.i18n.language : "zh_CN"
    property int langRev: window.i18n ? window.i18n.revision : 0
    function _t(key) { return window.i18n ? window.i18n.tr(key) : key }

    // Manually refresh all translatable texts
    function refreshTexts() {
        // Refresh navigation items
        var items = window.navigationItems
        if (items && items.length >= 3) {
            items[0].title = window._t("nav.codes")
            items[1].title = window._t("nav.settings")
            items[2].title = window._t("nav.about")
            window.navigationItems = items
        }
        // Refresh password dialog
        passwordDialog.title = passwordDialog.isNew ? window._t("dialog.password.title.new") : window._t("dialog.password.title.existing")
        pwdField.placeholderText = window._t("dialog.password.placeholder")
        pwdConfirm.placeholderText = window._t("dialog.password.confirm")
        // Refresh add/edit dialog
        addEditDialog.title = addEditDialog.editId.length > 0 ? window._t("dialog.addedit.title.edit") : window._t("dialog.addedit.title.new")
        // Refresh lock overlay
        lockOverlayTitle.text = window._t("lock.title")
        lockOverlaySubtitle.text = window._t("lock.subtitle")
        lockOverlayBtn.text = window._t("button.unlock")
    }

    // ── Navigation items ────────────────────────────────────────────
    navigationItems: [
        {
            title: window._t("nav.codes"),
            page: Qt.resolvedUrl("pages/MainPage.qml"),
            icon: "ic_fluent_key_20_regular",
            position: Position.Top
        },
        {
            title: window._t("nav.settings"),
            page: Qt.resolvedUrl("pages/SettingsPage.qml"),
            icon: "ic_fluent_settings_20_regular",
            position: Position.Bottom
        },
        {
            title: window._t("nav.about"),
            page: Qt.resolvedUrl("pages/AboutPage.qml"),
            icon: "ic_fluent_info_20_regular",
            position: Position.Bottom
        }
    ]

    // ── Theme initialization ──────────────────────────────────────
    Component.onCompleted: {
        Theme.setTheme(Theme.mode.Auto)
        Theme.setBackdropEffect(Theme.effect.Acrylic)

        if (Backend.hasPassword()) {
            passwordDialog.isNew = false
            passwordDialog.open()
        } else {
            passwordDialog.isNew = true
            passwordDialog.open()
        }
    }

    // ── Helper functions to show dialogs from pages ───────────────
    function showAddEditDialog(accountId) {
        if (accountId && accountId.length > 0) {
            addEditDialog.openEdit(accountId)
        } else {
            addEditDialog.openNew()
        }
    }
    function showDeleteConfirmDialog() { deleteConfirmDialog.open() }
    function showChangePwdDialog() { changePwdDialog.open() }
    function showExportPwdDialog() { exportPwdDialog.open() }
    function showImportFileDialog() { importFileDialog.open() }
    function showAboutDialog() { aboutDialog.open() }
    function showCloseDialog() { closeConfirmDialog.open() }

    // ── Password dialog ────────────────────────────────────────────
    Dialog {
        id: passwordDialog
        property bool isNew: false
        title: passwordDialog.isNew ? window._t("dialog.password.title.new") : window._t("dialog.password.title.existing")
        modal: true
        closePolicy: Popup.NoAutoClose
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text {
                text: passwordDialog.isNew ? window._t("dialog.password.desc.new") : window._t("dialog.password.desc.existing")
                typography: Typography.Caption
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            TextField {
                id: pwdField
                Layout.fillWidth: true
                placeholderText: window._t("dialog.password.placeholder")
                echoMode: TextInput.Password
                focus: true
                onAccepted: passwordDialog.accept()
            }

            TextField {
                id: pwdConfirm
                Layout.fillWidth: true
                visible: passwordDialog.isNew
                placeholderText: window._t("dialog.password.confirm")
                echoMode: TextInput.Password
                onAccepted: passwordDialog.accept()
            }
        }

        onOpened: {
            pwdField.text = ""
            pwdConfirm.text = ""
            pwdField.forceActiveFocus()
        }

        onAccepted: {
            if (isNew) {
                if (pwdField.text === pwdConfirm.text && pwdField.text.length > 0) {
                    if (Backend.setupPassword(pwdField.text, pwdConfirm.text)) {
                        passwordDialog.close()
                    } else {
                        pwdField.text = ""
                        pwdConfirm.text = ""
                    }
                }
            } else {
                if (Backend.verifyPassword(pwdField.text)) {
                    passwordDialog.close()
                } else {
                    pwdField.text = ""
                    pwdField.forceActiveFocus()
                }
            }
        }
    }

    // ── Add/Edit account dialog ────────────────────────────────────
    Dialog {
        id: addEditDialog
        property string editId: ""
        title: editId.length > 0 ? window._t("dialog.addedit.title.edit") : window._t("dialog.addedit.title.new")
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        function openNew() {
            editId = ""
            aeName.text = ""
            aeIssuer.text = ""
            aeSecret.text = ""
            aeDigits.value = 6
            aePeriod.value = 30
            aeAlgo.currentIndex = 0
            open()
        }
        function openEdit(accountId) {
            editId = accountId
            var acc = Backend.getAccount(accountId)
            aeName.text = acc.name || ""
            aeIssuer.text = acc.issuer || ""
            aeSecret.text = acc.secret || ""
            aeDigits.value = acc.digits || 6
            aePeriod.value = acc.period || 30
            var algoIdx = aeAlgo.find(function(item) { return item === acc.algorithm })
            aeAlgo.currentIndex = algoIdx >= 0 ? algoIdx : 0
            open()
        }

        ColumnLayout {
            spacing: 12
            Layout.fillWidth: true

            Text { text: window._t("dialog.addedit.name"); typography: Typography.Caption }
            TextField {
                id: aeName
                Layout.fillWidth: true
                placeholderText: window._t("dialog.addedit.name.placeholder")
            }

            Text { text: window._t("dialog.addedit.issuer"); typography: Typography.Caption }
            TextField {
                id: aeIssuer
                Layout.fillWidth: true
                placeholderText: window._t("dialog.addedit.issuer.placeholder")
            }

            Text { text: window._t("dialog.addedit.secret") + " (Base32)"; typography: Typography.Caption }
            TextField {
                id: aeSecret
                Layout.fillWidth: true
                placeholderText: window._t("dialog.addedit.secret.placeholder")
            }
            Row {
                spacing: 6
                Button {
                    text: "生成随机密钥"
                    flat: true
                    onClicked: aeSecret.text = Backend.generateSecret()
                }
                Button {
                    text: window._t("dialog.addedit.otpauth")
                    flat: true
                    onClicked: otpAuthDialog.open()
                }
            }

            RowLayout {
                spacing: 16
                Layout.fillWidth: true

                ColumnLayout {
                    spacing: 4
                    Text { text: window._t("dialog.addedit.algorithm"); typography: Typography.Caption }
                    ComboBox {
                        id: aeAlgo
                        model: ["SHA1", "SHA256", "SHA512"]
                    }
                }

                ColumnLayout {
                    spacing: 4
                    Text { text: window._t("dialog.addedit.digits"); typography: Typography.Caption }
                    SpinBox {
                        id: aeDigits
                        from: 6
                        to: 8
                        value: 6
                    }
                }

                ColumnLayout {
                    spacing: 4
                    Text { text: window._t("dialog.addedit.period"); typography: Typography.Caption }
                    RowLayout {
                        SpinBox {
                            id: aePeriod
                            from: 15
                            to: 120
                            value: 30
                        }
                        Text {
                            text: "秒"
                            typography: Typography.Caption
                            color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
                        }
                    }
                }
            }
        }

        onAccepted: {
            var data = {
                name: aeName.text,
                issuer: aeIssuer.text,
                secret: aeSecret.text,
                digits: aeDigits.value,
                period: aePeriod.value,
                algorithm: aeAlgo.currentText
            }
            if (editId.length > 0) {
                Backend.updateAccount(editId, data)
            } else {
                Backend.addAccount(data)
            }
        }
    }

    // ── OTP Auth URL import dialog ─────────────────────────────────
    Dialog {
        id: otpAuthDialog
        title: window._t("dialog.addedit.otpauth")
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text {
                text: window._t("dialog.addedit.otpauth")
                typography: Typography.Caption
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
            }
            TextArea {
                id: otpAuthUrl
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                placeholderText: window._t("dialog.addedit.otpauth.placeholder")
                wrapMode: TextArea.Wrap
            }
            Text {
                id: otpAuthStatus
                text: ""
                typography: Typography.Caption
                color: "#d93025"
                visible: text.length > 0
            }
        }

        onOpened: {
            otpAuthUrl.text = ""
            otpAuthStatus.text = ""
        }

        onAccepted: {
            var url = otpAuthUrl.text.trim()
            if (url.length === 0) {
                otpAuthStatus.text = window._t("dialog.addedit.otpauth.placeholder")
                otpAuthDialog.open()
                return
            }
            var result = Backend.parseOTPAuthUrl(url)
            if (!result || Object.keys(result).length === 0) {
                otpAuthStatus.text = "无法解析该链接，请检查格式"
                otpAuthDialog.open()
                return
            }
            if (result.name) aeName.text = result.name
            if (result.issuer !== undefined) aeIssuer.text = result.issuer
            if (result.secret) aeSecret.text = result.secret
            if (result.digits !== undefined) aeDigits.value = result.digits
            if (result.period !== undefined) aePeriod.value = result.period
            if (result.algorithm) {
                var idx = aeAlgo.find(function(item) { return item === result.algorithm })
                if (idx >= 0) aeAlgo.currentIndex = idx
            }
        }
    }

    // ── Delete confirm dialog ──────────────────────────────────────
    Dialog {
        id: deleteConfirmDialog
        title: window._t("dialog.delete.title")
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text {
                text: window._t("dialog.delete.message")
                typography: Typography.Body
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            if (window.pendingDeleteId.length > 0) {
                Backend.deleteAccount(window.pendingDeleteId)
                window.pendingDeleteId = ""
            }
        }
    }

    // ── Change password dialog ─────────────────────────────────────
    Dialog {
        id: changePwdDialog
        title: window._t("settings.change_password")
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text { text: "旧密码"; typography: Typography.Caption }
            TextField {
                id: cpOldPwd
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "旧密码"
            }
            Text { text: "新密码"; typography: Typography.Caption }
            TextField {
                id: cpNewPwd
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "新密码"
            }
            Text { text: "确认新密码"; typography: Typography.Caption }
            TextField {
                id: cpConfirmPwd
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "确认新密码"
            }
        }

        onOpened: {
            cpOldPwd.text = ""
            cpNewPwd.text = ""
            cpConfirmPwd.text = ""
        }

        onAccepted: {
            if (cpNewPwd.text !== cpConfirmPwd.text) {
                Backend.notification.emit("错误", "新密码不匹配")
                return
            }
            Backend.changePassword(cpOldPwd.text, cpNewPwd.text)
        }
    }

    // ── Export password verification dialog ────────────────────────
    Dialog {
        id: exportPwdDialog
        title: "导出验证"
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text {
                text: "请输入主密码以导出数据"
                typography: Typography.Caption
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
            }
            TextField {
                id: exportPwd
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "主密码"
            }
        }

        onOpened: {
            exportPwd.text = ""
        }

        onAccepted: {
            exportFileDialog.password = exportPwd.text
            exportFileDialog.open()
        }
    }

    // ── Import file dialog ─────────────────────────────────────────
    FileDialog {
        id: importFileDialog
        title: window._t("settings.import")
        fileMode: FileDialog.OpenFile
        nameFilters: ["JSON Files (*.json)", "All Files (*)"]
        onAccepted: {
            Backend.importFromFile(selectedFile.toString())
        }
    }

    // ── Export file dialog ─────────────────────────────────────────
    FileDialog {
        id: exportFileDialog
        title: window._t("settings.export")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON Files (*.json)"]
        property string password: ""
        onAccepted: {
            Backend.exportToFile(password, selectedFile.toString())
            password = ""
        }
    }

    // ── About dialog ───────────────────────────────────────────────
    Dialog {
        id: aboutDialog
        title: window._t("settings.about")
        modal: true
        closePolicy: Popup.CloseOnPressOutside
        standardButtons: DialogButtonBox.Ok
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 8
            Layout.fillWidth: true

            Text {
                text: window._t("app.title")
                typography: Typography.Subtitle
                font.bold: true
            }
            Text {
                text: window._t("app.subtitle")
                typography: Typography.Body
            }
            Text {
                typography: Typography.Caption
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
                text: "基于 RinUI Fluent Design 界面\n支持桌面卡片模式\nAES 加密存储 · 实时验证码"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }

    // ── Close confirmation dialog ──────────────────────────────────
    Dialog {
        id: closeConfirmDialog
        title: window.langRev ? window._t("dialog.close.title") : window._t("dialog.close.title")
        modal: true
        closePolicy: Popup.NoAutoClose
        standardButtons: DialogButtonBox.NoButton
        anchors.centerIn: Overlay.overlay

        ColumnLayout {
            spacing: 16
            Layout.fillWidth: true

            Text {
                text: window.langRev ? window._t("dialog.close.question") : window._t("dialog.close.question")
                typography: Typography.Body
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textPrimaryColor : "#000000"
                Layout.fillWidth: true
            }
            Text {
                text: window.langRev ? window._t("dialog.close.desc") : window._t("dialog.close.desc")
                typography: Typography.Caption
                color: Theme.currentTheme && Theme.currentTheme.colors ? Theme.currentTheme.colors.textSecondaryColor : "#888888"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Button {
                    text: window.langRev ? window._t("dialog.close.hide_to_tray") : window._t("dialog.close.hide_to_tray")
                    flat: true
                    Layout.fillWidth: true
                    onClicked: {
                        closeConfirmDialog.close()
                        CloseFilter.action_hide_to_tray()
                    }
                }
                Button {
                    text: window.langRev ? window._t("dialog.close.quit") : window._t("dialog.close.quit")
                    highlighted: true
                    Layout.fillWidth: true
                    onClicked: {
                        closeConfirmDialog.close()
                        CloseFilter.action_quit()
                    }
                }
                Button {
                    text: window.langRev ? window._t("dialog.close.cancel") : window._t("dialog.close.cancel")
                    flat: true
                    Layout.fillWidth: true
                    onClicked: {
                        closeConfirmDialog.close()
                        CloseFilter.action_cancel()
                    }
                }
            }
        }
    }

    // ── Backend connections ──────────────────────────────────────
    Connections {
        target: Backend

        function onAuthenticated() {
            window.isUnlocked = true
            passwordDialog.close()
        }

        function onRequestPasswordDialog(isNew) {
            window.isUnlocked = false
            passwordDialog.isNew = isNew
            passwordDialog.open()
        }
    }

    // Refresh UI when language changes
    Connections {
        target: window.i18n
        function onLanguageChanged() {
            window.langRev = window.i18n.revision
            window.refreshTexts()
        }
    }

    // ── Lock overlay: blocks interaction when not authenticated ─
    Rectangle {
        id: lockOverlay
        anchors.fill: parent
        color: (function() {
            var theme = Theme.currentTheme
            if (theme && theme.mode) {
                var modeStr = String(theme.mode)
                if (modeStr === "Dark" || modeStr === "dark" || modeStr === "1" || modeStr === "DarkMode") {
                    return "#1a1a1a"
                }
            }
            if (theme && theme.colors && theme.colors.cardColor) {
                var cardColor = String(theme.colors.cardColor)
                if (cardColor.startsWith("#0d") || cardColor.startsWith("#0a") || cardColor.startsWith("#1a")) {
                    return "#1a1a1a"
                }
            }
            return "#f3f3f3"
        })()
        visible: !window.isUnlocked
        z: 100

        Column {
            anchors.centerIn: parent
            spacing: 12
            width: parent.width - 80

            Text {
                id: lockOverlayTitle
                width: parent.width
                text: window._t("lock.title")
                font.pixelSize: 24
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                color: (function() {
                    var theme = Theme.currentTheme
                    if (theme && theme.mode) {
                        var modeStr = String(theme.mode)
                        if (modeStr === "Dark" || modeStr === "dark" || modeStr === "1" || modeStr === "DarkMode") {
                            return "#ffffff"
                        }
                    }
                    if (theme && theme.colors && theme.colors.cardColor) {
                        var cardColor = String(theme.colors.cardColor)
                        if (cardColor.startsWith("#0d") || cardColor.startsWith("#0a") || cardColor.startsWith("#1a")) {
                            return "#ffffff"
                        }
                    }
                    return "#000000"
                })()
            }

            Text {
                id: lockOverlaySubtitle
                width: parent.width
                text: window._t("lock.subtitle")
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                color: (function() {
                    var theme = Theme.currentTheme
                    if (theme && theme.mode) {
                        var modeStr = String(theme.mode)
                        if (modeStr === "Dark" || modeStr === "dark" || modeStr === "1" || modeStr === "DarkMode") {
                            return "#bbbbbb"
                        }
                    }
                    if (theme && theme.colors && theme.colors.cardColor) {
                        var cardColor = String(theme.colors.cardColor)
                        if (cardColor.startsWith("#0d") || cardColor.startsWith("#0a") || cardColor.startsWith("#1a")) {
                            return "#bbbbbb"
                        }
                    }
                    return "#666666"
                })()
                wrapMode: Text.WordWrap
            }

            Button {
                id: lockOverlayBtn
                anchors.horizontalCenter: parent.horizontalCenter
                text: window._t("button.unlock")
                highlighted: true
                onClicked: {
                    passwordDialog.isNew = false
                    passwordDialog.open()
                }
            }
        }
    }
}