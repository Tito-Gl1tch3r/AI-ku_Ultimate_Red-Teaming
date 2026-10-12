package com.codehack.JungleConfig.Core.Implim.IO;

import com.codehack.JungleConfig.Core.IOHandlerInterface;

import java.io.*;

public class NativeIOHandler implements IOHandlerInterface {
    private final File file;

    public NativeIOHandler(File file) {
        this.file = file;
        if (!file.exists()) {
            try {
                boolean d = file.createNewFile();
                if (!d)
                    throw new RuntimeException(new IOException("file cannot be created!"));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }
    }

    @Override
    public String Read() {
        try {
            return java.nio.file.Files.readString(file.toPath());
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public void Write(String data) {
        try {
            java.nio.file.Files.writeString(file.toPath(), data);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private void writeToFile(File f, String data) {
        try {
            java.nio.file.Files.writeString(f.toPath(), data);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public boolean Backup(File path, boolean override) {
        try {
            if (path.exists()) {
                if (!override)
                    return false;
                if (!(path.isFile() || path.canWrite()))
                    throw new IllegalArgumentException("Given Path isn't a file or cannot writable");
            } else {
                if (!path.canWrite())
                    throw new IOException("No permission to Write");
                if (!path.createNewFile())
                    throw new IllegalArgumentException("FIle Creation Error, File failed to Create in given path");
            }
            writeToFile(path, Read());
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return true;
    }
}
