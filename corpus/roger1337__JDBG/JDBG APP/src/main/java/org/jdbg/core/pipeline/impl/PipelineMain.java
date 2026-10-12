package org.jdbg.core.pipeline.impl;

import com.sun.jna.platform.win32.Kernel32;
import com.sun.jna.ptr.IntByReference;
import org.jdbg.core.pipeline.Pipeline;
import org.jdbg.logger.Logger;

import java.awt.image.Kernel;

public class PipelineMain extends Pipeline {
    // rn NO_JVM is kinda useless, as if there is no jvm then the dll wont run as the functions wont link properly.
    // AttachManager#hasJVM is the solution
    public enum DllStatus {
        SUCCESS,
        NO_JVM,
        FAIL
    }
    public enum ServerCommand {
        GET_LOADED_CLASS_NAMES,
        GET_CLASS_DATA,
        GET_OBJECT_TAGS,
        GET_REFS,
        GET_FIELDS,

        SET_OBJECT,

        SET_FIELD,
        ADD_BREAKPOINT,
        CLEAR_BREAKPOINT
    }

    public enum ResponseStatus {
        OK,
        ERROR
    }


    public static class ClientResponse {
        public ResponseStatus status;
        public byte[] response;

        public ClientResponse(ResponseStatus status, byte[] response) {
            this.status = status;
            this.response = response;
        }

        public ClientResponse() {};
    }

    static PipelineMain instance;
    public PipelineMain() {
        super("\\\\.\\pipe\\jdbg");
    }

    public DllStatus awaitAndCheckStatus() {
        Logger.log("Awaiting main pipe connection");
        Kernel32.INSTANCE.ConnectNamedPipe(pipeHandle, null);
        Logger.log("Client has connected to main pipe");

        byte[] status = new byte[1];
        IntByReference bytesRead = new IntByReference(0);
        Kernel32.INSTANCE.ReadFile(pipeHandle, status, status.length, bytesRead, null);

        if(bytesRead.getValue()==0){
            return DllStatus.FAIL;
        }

        return DllStatus.values()[status[0]];

    }


    public void createPipe() {
        super.createPipe();
    }

    public static void init() {
        instance = new PipelineMain();
    }


    public ClientResponse sendAndAwait(ServerCommand command) {
        return sendAndAwait(command, new byte[0]);
    }

    public ClientResponse sendAndAwait(ServerCommand command, byte[] data) {
        sendData(command, data);
        byte[] rawResponse = readMessage();

        if(rawResponse.length==0) {
            Logger.log("The thing terminated");
            return new ClientResponse(ResponseStatus.ERROR, new byte[0]);
        }

        ClientResponse response = new ClientResponse();
        byte[] realResponse = new byte[rawResponse.length-1];
        System.arraycopy(rawResponse,1,realResponse,0,realResponse.length);
        response.status = ResponseStatus.values()[rawResponse[0]];
        response.response = realResponse;



        return response;
    }

    private void sendData(ServerCommand command) {
        sendData(command, new byte[0]);
    }
    private void sendData(ServerCommand command, byte[] data) {
        byte[] newBytes = new byte[data.length+1];
        newBytes[0] = (byte)command.ordinal();
        System.arraycopy(data, 0, newBytes, 1, data.length);
        sendData(newBytes);
    }


    public static PipelineMain getInstance() {
        return instance;
    }
}
