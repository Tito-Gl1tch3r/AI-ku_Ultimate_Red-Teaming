package org.jdbg.core.attach;

import com.sun.jna.Function;
import com.sun.jna.Native;
import com.sun.jna.NativeLibrary;
import com.sun.jna.Pointer;
import com.sun.jna.platform.win32.*;
import com.sun.jna.platform.win32.WinNT.HANDLE;
import com.sun.jna.ptr.IntByReference;
import org.jdbg.core.attach.breakpoint.BreakpointManager;
import org.jdbg.core.pipeline.impl.PipelineBreakpoint;
import org.jdbg.core.pipeline.impl.PipelineLogDll;
import org.jdbg.core.pipeline.impl.PipelineMain;
import org.jdbg.gui.MainFrame;
import org.jdbg.logger.Logger;

import java.io.File;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.sun.jna.platform.win32.WinNT.*;

public class AttachManager {

    private static AttachManager instance;
    private boolean attached = false;

    private int currentPid;

    private BreakpointManager breakpointManager;

    private Thread breakpointThread;

    private Thread logThread;

    public AttachManager() {
        instance = this;
    }

    // TODO do cleanups
    public boolean deAttach(int pid) {
        Logger.log("Waiting for threads to cease.");

        PipelineLogDll.getInstance().cease();
        PipelineBreakpoint.getInstance().continueExecution();
        PipelineBreakpoint.getInstance().cease();
        try {
            breakpointThread.join();
            logThread.join();
        } catch (Exception e) {
            e.printStackTrace();
        }



        return false;
    }
    public boolean attach(int pid) {
        if(attached) deAttach(currentPid);

        boolean processAttach = attachProcess(pid);
        if(!processAttach) {
            Logger.log("Failed to attach");
            MainFrame.getInstance().setUnattached();
            return false;
        }

        breakpointThread = new Thread(PipelineBreakpoint.getInstance());
        breakpointThread.start();
        logThread = new Thread(PipelineLogDll.getInstance());
        logThread.start();


        currentPid = pid;
        MainFrame.getInstance().setAttached(String.valueOf(pid));
        attached = true;
        breakpointManager = new BreakpointManager(pid);
        return true;

    }
    public boolean attachProcess(int pid) {
        Logger.log("Attaching");


        if(!hasJVM(pid)) {
            Logger.log("Process has no jvm!");
            return false;
        }

        // This re-creates it.
        PipelineMain.getInstance().createPipe();

        ExecutorService executor = Executors.newSingleThreadExecutor();

        Future<PipelineMain.DllStatus> theStatus = executor.submit(() -> {
            return PipelineMain.getInstance().awaitAndCheckStatus();
        });


        try {
            HANDLE hProcess = Kernel32.INSTANCE.OpenProcess(WinNT.PROCESS_ALL_ACCESS, false, pid);
            IntByReference is64 = new IntByReference();
            Kernel32.INSTANCE.IsWow64Process(hProcess, is64);
            boolean is64Bit = is64.getValue()==0;

            byte[] bytes;
            if(is64Bit) {
                bytes = getClass().getResourceAsStream("/assets/JDBG DLL_64.dll").readAllBytes();
            } else {
                bytes = getClass().getResourceAsStream("/assets/JDBG DLL_32.dll").readAllBytes();

            }
            System.out.println(bytes.length);

            File file = File.createTempFile("jrev", ".dll");
            Files.write(file.getAbsoluteFile().toPath(), bytes);


            if(injectDLL(file.getAbsolutePath(), hProcess, is64Bit)) {
                Logger.log("DLL injected");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        try {
            PipelineMain.DllStatus status = theStatus.get();
            if (status == PipelineMain.DllStatus.SUCCESS) {
                Logger.log("Successfully attached");
                return true;

            } else if (status == PipelineMain.DllStatus.FAIL) {
                Logger.log("Failed to attach");
                return false;
            }
        } catch(ExecutionException|InterruptedException e) {
            e.printStackTrace();
        }
        return false;

    }

    private boolean hasJVM(int pid) {

        HANDLE h = Kernel32.INSTANCE.CreateToolhelp32Snapshot(
                new WinDef.DWORD(Tlhelp32.TH32CS_SNAPMODULE.intValue() | Tlhelp32.TH32CS_SNAPMODULE32.intValue()),
                new WinDef.DWORD(pid));

        Tlhelp32.MODULEENTRY32W module = new Tlhelp32.MODULEENTRY32W();
        while(Kernel32.INSTANCE.Module32NextW(h, module)) {
            String s = Native.toString(module.szModule);
            if(s.equals("jvm.dll"))
                return true;
        }

        return false;
    }


    Function get32BitLoadLibrary() {
        try {

            byte[] bytes = getClass().getResourceAsStream("/assets/JDBG 32bit Helper.exe").readAllBytes();
            File file = File.createTempFile("32bithelper", ".exe");
            Files.write(file.getAbsoluteFile().toPath(), bytes);
            Process process = Runtime.getRuntime().exec(file.getAbsolutePath());


            int nativePtr = process.waitFor();
            Pointer p = new Pointer(nativePtr);

            return Function.getFunction(p);



        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;

    }
    private boolean injectDLL(String dllPath, HANDLE hProcess, boolean is64bit) {
        dllPath += '\0';
        System.out.println(dllPath);

        Pointer pDllPath = Kernel32.INSTANCE.VirtualAllocEx(hProcess, null,
                new BaseTSD.SIZE_T(dllPath.length()),
                MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);


        ByteBuffer bufSrc = ByteBuffer.allocateDirect(dllPath.length());
        bufSrc.put(dllPath.getBytes());


        Pointer ptrSrc = Native.getDirectBufferPointer(bufSrc);

        IntByReference bytesWritten = new IntByReference();
        Kernel32.INSTANCE.WriteProcessMemory(hProcess, pDllPath, ptrSrc, dllPath.length(), bytesWritten);
        if (bytesWritten.getValue() != dllPath.length()) {
            Logger.log("Write process memory failed");
            return false;
        }

        Function LoadLibraryAFunction;

        if(is64bit) {
            NativeLibrary kernel32Library = NativeLibrary.getInstance("kernel32");
            LoadLibraryAFunction = kernel32Library.getFunction("LoadLibraryA");
            Logger.log("JVM Process is 64bit.");
        } else {
            Logger.log("JVM Process is 32bit. Running 32bit helper.");
            LoadLibraryAFunction = get32BitLoadLibrary();
        }

        DWORDByReference threadId = new DWORDByReference();

        HANDLE hThread = Kernel32.INSTANCE.CreateRemoteThread(hProcess, null, 0,
                LoadLibraryAFunction, pDllPath, 0, threadId);


        return true;

    }

    public boolean isAttached() {
        return attached;
    }

    public static AttachManager getInstance() {
        if(instance == null)
            instance = new AttachManager();
        return instance;
    }

    public BreakpointManager getBreakpointManager() {
        return breakpointManager;
    }

}
