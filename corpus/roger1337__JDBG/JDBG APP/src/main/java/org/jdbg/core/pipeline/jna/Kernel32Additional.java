package org.jdbg.core.pipeline.jna;

import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Platform;
import com.sun.jna.Pointer;
import com.sun.jna.platform.win32.Kernel32;
import com.sun.jna.platform.win32.WinBase;
import com.sun.jna.platform.win32.WinNT;
import com.sun.jna.ptr.IntByReference;
import com.sun.jna.win32.StdCallLibrary;

public interface Kernel32Additional extends StdCallLibrary {
    Kernel32Additional INSTANCE = Native.load("kernel32", Kernel32Additional.class);

    boolean CancelIoEx(WinNT.HANDLE hFile, WinBase.OVERLAPPED lpOverlapped);

}
