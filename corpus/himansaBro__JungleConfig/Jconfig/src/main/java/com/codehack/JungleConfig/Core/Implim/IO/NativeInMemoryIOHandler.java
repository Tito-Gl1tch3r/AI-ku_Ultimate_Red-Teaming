package com.codehack.JungleConfig.Core.Implim.IO;

import com.codehack.JungleConfig.Core.IOHandlerInterface;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

/**
 *
 * @author Himansa
 */
public class NativeInMemoryIOHandler implements IOHandlerInterface {

    private String save = "";

    @Override
    public String Read() {
        return save;
    }

    @Override
    public void Write(String data) {
        save = data;
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

    private void writeToFile(File f, String data) {
        FileWriter fr;
        try {
            fr = new FileWriter(f, false);
            BufferedWriter br = new BufferedWriter(fr);
            br.write(data);
            br.close();
            fr.close();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
