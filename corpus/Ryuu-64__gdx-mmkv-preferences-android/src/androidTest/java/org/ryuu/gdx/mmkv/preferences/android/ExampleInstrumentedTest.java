package org.ryuu.gdx.mmkv.preferences.android;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.badlogic.gdx.*;
import com.badlogic.gdx.utils.Clipboard;
import com.tencent.mmkv.MMKV;
import org.junit.Test;
import org.junit.runner.RunWith;

import static org.junit.Assert.*;

/**
 * Instrumented test, which will execute on an Android device.
 *
 * @see <a href="http://d.android.com/tools/testing">Testing documentation</a>
 */
@RunWith(AndroidJUnit4.class)
public class ExampleInstrumentedTest {
    private final Application application = new Application() {
        @Override
        public ApplicationListener getApplicationListener() {
            return null;
        }

        @Override
        public Graphics getGraphics() {
            return null;
        }

        @Override
        public Audio getAudio() {
            return null;
        }

        @Override
        public Input getInput() {
            return null;
        }

        @Override
        public Files getFiles() {
            return null;
        }

        @Override
        public Net getNet() {
            return null;
        }

        @Override
        public void log(String tag, String message) {

        }

        @Override
        public void log(String tag, String message, Throwable exception) {

        }

        @Override
        public void error(String tag, String message) {

        }

        @Override
        public void error(String tag, String message, Throwable exception) {

        }

        @Override
        public void debug(String tag, String message) {

        }

        @Override
        public void debug(String tag, String message, Throwable exception) {

        }

        @Override
        public void setLogLevel(int logLevel) {

        }

        @Override
        public int getLogLevel() {
            return 0;
        }

        @Override
        public void setApplicationLogger(ApplicationLogger applicationLogger) {

        }

        @Override
        public ApplicationLogger getApplicationLogger() {
            return null;
        }

        @Override
        public ApplicationType getType() {
            return null;
        }

        @Override
        public int getVersion() {
            return 0;
        }

        @Override
        public long getJavaHeap() {
            return 0;
        }

        @Override
        public long getNativeHeap() {
            return 0;
        }

        @Override
        public Preferences getPreferences(String name) {
            return new MMKVPreferences(name);
        }

        @Override
        public Clipboard getClipboard() {
            return null;
        }

        @Override
        public void postRunnable(Runnable runnable) {

        }

        @Override
        public void exit() {

        }

        @Override
        public void addLifecycleListener(LifecycleListener listener) {

        }

        @Override
        public void removeLifecycleListener(LifecycleListener listener) {

        }
    };

    @Test
    public void getPreferences() {
        Context appContext = InstrumentationRegistry.getInstrumentation().getTargetContext();
        MMKV.initialize(appContext);
        Preferences preferences = application.getPreferences("");
        assertTrue(preferences instanceof MMKVPreferences);
    }
}