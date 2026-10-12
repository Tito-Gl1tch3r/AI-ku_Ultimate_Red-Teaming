package org.jdbg.gui.tabs.classanalysis.codepanel.comp;

import org.fife.ui.rsyntaxtextarea.*;
import org.jdbg.Main;

import javax.swing.*;
import java.awt.*;

public class CodeText extends RSyntaxTextArea {

    static Font codeFont;
    static {
        try {
            Font font = Font.createFont(Font.TRUETYPE_FONT,
                    Main.class.getResourceAsStream("/assets/fonts/JetBrainsMonoNL-Regular.ttf"));
            codeFont = font.deriveFont((float)(new JLabel().getFont().getSize()) + 2);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    public CodeText() {
        setSyntaxEditingStyle(SyntaxConstants.SYNTAX_STYLE_JAVA);




        setCodeFoldingEnabled(true);
        setEditable(false);
        setFont(codeFont);

        setBackground(UIManager.getColor("TabbedPane.buttonHoverBackground"));

        setCurrentLineHighlightColor(UIManager.getColor("Panel.background"));
        setCaretColor(UIManager.getColor("Panel.background"));

        Color orange = new Color(200, 96, 49);
        Color blue = new Color(81, 145, 166);
        Color green = new Color(88, 124, 86);
        SyntaxScheme scheme = getSyntaxScheme();
        scheme.getStyle(Token.RESERVED_WORD).foreground = orange;
        scheme.getStyle(Token.DATA_TYPE).foreground = Color.blue;

        scheme.getStyle(Token.FUNCTION).foreground = UIManager.getColor("Label.foreground");
        scheme.getStyle(Token.IDENTIFIER).foreground = UIManager.getColor("Label.foreground");
        scheme.getStyle(Token.SEPARATOR).foreground = UIManager.getColor("Label.foreground");
        scheme.getStyle(Token.OPERATOR).foreground = UIManager.getColor("Label.foreground");

        scheme.getStyle(Token.DATA_TYPE).foreground = orange;
        scheme.getStyle(Token.RESERVED_WORD).foreground = orange;
        scheme.getStyle(Token.RESERVED_WORD_2).foreground = orange;
        scheme.getStyle(Token.LITERAL_BOOLEAN).foreground = orange;

        scheme.getStyle(Token.LITERAL_NUMBER_HEXADECIMAL).foreground = blue;
        scheme.getStyle(Token.LITERAL_NUMBER_FLOAT).foreground = blue;
        scheme.getStyle(Token.LITERAL_NUMBER_DECIMAL_INT).foreground = blue;

        scheme.getStyle(Token.LITERAL_BACKQUOTE).foreground = green;
        scheme.getStyle(Token.LITERAL_STRING_DOUBLE_QUOTE).foreground = green;
        scheme.getStyle(Token.LITERAL_CHAR).foreground = green;





        revalidate();
    }

}
