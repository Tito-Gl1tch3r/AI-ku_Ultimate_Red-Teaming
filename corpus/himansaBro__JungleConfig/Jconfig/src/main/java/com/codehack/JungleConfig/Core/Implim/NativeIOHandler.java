package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.IOHandlerInterface;

import java.io.*;

public class NativeIOHandler implements IOHandlerInterface {
    private final File file;

    public NativeIOHandler(File file) {
        this.file = file;
        if (!file.exists()) {
            try {
                boolean d =file.createNewFile();
                if (!d) throw new RuntimeException(new IOException("file cannot be created!"));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }
    }

    @Override
    public String Read() {
        System.out.println(">>> IO Read");
        StringBuilder builder = new StringBuilder();
        FileReader fs = null;
        try {
            fs = new FileReader(file);
        } catch (FileNotFoundException e) {
            throw new RuntimeException(e);
        }
        BufferedReader bff = new BufferedReader(fs);
        String line;
        while (true){
            try {
                if ((line = bff.readLine()) == null) break;
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            builder.append(line).append("\n");
        }
        try {
            bff.close();
            fs.close();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return builder.toString();
    }
    @Override
    public void Write(String data) {
        System.out.println("<<< IO Write");
        writeToFile(file,data);
    }
    private void writeToFile(File f,String data){
        FileWriter fr = null;
        try {
            fr = new FileWriter(f,false);
            BufferedWriter br = new BufferedWriter(fr);
            br.write(data);
            br.close();
            fr.close();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public boolean Backup(File path, boolean override) {
        try {
            if (path.exists()){
                if(!override) return false;
                if (!(path.isFile()|| path.canWrite())) throw new IllegalArgumentException("Given Path isn't a file or cannot writable");
            }else {
                if (!path.canWrite()) throw new IOException("No permission to Write");
                if (!path.createNewFile()) throw new IllegalArgumentException("FIle Creation Error, File failed to Create in given path");
            }
            writeToFile(path,Read());
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return true;
    }
}
