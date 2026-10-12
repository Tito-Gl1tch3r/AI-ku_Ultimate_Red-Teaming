package com.six2dez.burp.aiagent.ui.components

import com.six2dez.burp.aiagent.redact.PrivacyMode
import com.six2dez.burp.aiagent.ui.UiTheme
import java.awt.Color
import java.awt.Font
import javax.swing.JLabel
import javax.swing.border.EmptyBorder

class PrivacyPill : JLabel() {
    private val strictColor = Color(0x1B9E5A)
    private val balancedColor = Color(0xF9A825)

    init {
        font = UiTheme.Typography.label.deriveFont(Font.PLAIN, UiTheme.Typography.label.size2D)
        border = EmptyBorder(4, 10, 4, 10)
        isOpaque = true
        updateMode(PrivacyMode.OFF)
    }

    fun updateMode(mode: PrivacyMode) {
        when (mode) {
            PrivacyMode.STRICT -> {
                isVisible = true
                text = "STRICT"
                background = strictColor
                foreground = Color.WHITE
                toolTipText = "STRICT mode strips cookies, redacts tokens, and anonymizes hosts."
            }
            PrivacyMode.BALANCED -> {
                isVisible = true
                text = "BALANCED"
                background = balancedColor
                foreground = UiTheme.Colors.onSurface
                toolTipText = "BALANCED mode strips cookies and redacts tokens but keeps hosts."
            }
            PrivacyMode.OFF -> {
                // The empty text + hidden pill is a value-display decision, not a redaction bypass —
                // D-06's do-not-touch list protects it. Only the tooltip string changes here.
                text = ""
                isVisible = false
                // D-07: OFF skips the built-in rules but custom patterns still run (D-05). updateMode
                // takes only the mode, so conditioning would need a signature change; the "if any are
                // configured" clause keeps this wording true whether or not the user has patterns.
                toolTipText = "OFF mode disables built-in redaction; custom redaction patterns, if any are configured, still apply."
            }
        }
    }
}
