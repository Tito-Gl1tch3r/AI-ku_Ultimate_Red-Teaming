package net.robinfriedli.jxp.logging;

import java.io.PrintStream;

import org.slf4j.helpers.FormattingTuple;
import org.slf4j.helpers.MarkerIgnoringBase;
import org.slf4j.helpers.MessageFormatter;

public class ConsoleLogger extends MarkerIgnoringBase {

    @Override
    public boolean isTraceEnabled() {
        return true;
    }

    @Override
    public void trace(String s) {
        print(Level.TRACE, s);
    }

    @Override
    public void trace(String s, Object o) {
        print(Level.TRACE, s, o);
    }

    @Override
    public void trace(String s, Object o, Object o1) {
        print(Level.TRACE, s, o, o1);
    }

    @Override
    public void trace(String s, Object... objects) {
        print(Level.TRACE, s, objects);
    }

    @Override
    public void trace(String s, Throwable throwable) {
        print(Level.TRACE, s, throwable);
    }

    @Override
    public boolean isDebugEnabled() {
        return true;
    }

    @Override
    public void debug(String s) {
        print(Level.DEBUG, s);
    }

    @Override
    public void debug(String s, Object o) {
        print(Level.DEBUG, s, o);
    }

    @Override
    public void debug(String s, Object o, Object o1) {
        print(Level.DEBUG, s, o, o1);
    }

    @Override
    public void debug(String s, Object... objects) {
        print(Level.DEBUG, s, objects);
    }

    @Override
    public void debug(String s, Throwable throwable) {
        print(Level.DEBUG, s, throwable);
    }

    @Override
    public boolean isInfoEnabled() {
        return true;
    }

    @Override
    public void info(String s) {
        print(Level.INFO, s);
    }

    @Override
    public void info(String s, Object o) {
        print(Level.INFO, s, o);
    }

    @Override
    public void info(String s, Object o, Object o1) {
        print(Level.INFO, s, o, o1);
    }

    @Override
    public void info(String s, Object... objects) {
        print(Level.INFO, s, objects);
    }

    @Override
    public void info(String s, Throwable throwable) {
        print(Level.INFO, s, throwable);
    }

    @Override
    public boolean isWarnEnabled() {
        return true;
    }

    @Override
    public void warn(String s) {
        print(Level.WARN, s);
    }

    @Override
    public void warn(String s, Object o) {
        print(Level.WARN, s, o);
    }

    @Override
    public void warn(String s, Object... objects) {
        print(Level.WARN, s, objects);
    }

    @Override
    public void warn(String s, Object o, Object o1) {
        print(Level.WARN, s, o, o1);
    }

    @Override
    public void warn(String s, Throwable throwable) {
        print(Level.WARN, s, throwable);
    }

    @Override
    public boolean isErrorEnabled() {
        return true;
    }

    @Override
    public void error(String s) {
        print(Level.ERROR, s);
    }

    @Override
    public void error(String s, Object o) {
        print(Level.ERROR, s, o);
    }

    @Override
    public void error(String s, Object o, Object o1) {
        print(Level.ERROR, s, o, o1);
    }

    @Override
    public void error(String s, Object... objects) {
        print(Level.ERROR, s, objects);
    }

    @Override
    public void error(String s, Throwable throwable) {
        print(Level.ERROR, s, throwable);
    }

    private void print(Level level, String message) {
        print(level, message, (Throwable) null);
    }

    private void print(Level level, String message, Throwable e) {
        PrintStream printStream = level.getPrintStream();
        printStream.println("JXP " + level.name() + " - " + message);
        if (e != null) {
            e.printStackTrace();
        }
    }

    private void print(Level level, String s, Object o) {
        print(level, s, new Object[]{o});
    }

    private void print(Level level, String s, Object o1, Object o2) {
        print(level, s, new Object[]{o1, o2});
    }

    private void print(Level level, String s, Object... objects) {
        String message = "JXP " + level.name() + " - " + s;
        FormattingTuple formattingTuple = MessageFormatter.arrayFormat(s, objects);
        level.getPrintStream().println(formattingTuple.getMessage());
        if (formattingTuple.getThrowable() != null) {
            formattingTuple.getThrowable().printStackTrace();
        }
    }

    private enum Level {

        TRACE(System.out),
        DEBUG(System.out),
        INFO(System.out),
        WARN(System.out),
        ERROR(System.err);

        private final PrintStream printStream;

        Level(PrintStream printStream) {
            this.printStream = printStream;
        }

        public PrintStream getPrintStream() {
            return printStream;
        }
    }

}
