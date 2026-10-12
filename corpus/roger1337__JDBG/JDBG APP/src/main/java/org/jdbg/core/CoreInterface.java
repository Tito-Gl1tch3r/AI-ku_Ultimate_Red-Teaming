package org.jdbg.core;


import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ObjectWriter;
import org.jdbg.core.attach.AttachManager;
import org.jdbg.core.pipeline.impl.PipelineMain;
import org.jdbg.core.pipeline.response.FieldResponseData;
import org.jdbg.core.pipeline.response.SubGraphData;
import org.jdbg.gui.tabs.objectanalysis.objlist.TagItem;
import org.jdbg.logger.Logger;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

// the gui should interact with this only to achieve the goals
public class CoreInterface {
    static CoreInterface instance;


    Map<String, byte[]> classData = new HashMap<>();

    public boolean attach(int pid) {
        return AttachManager.getInstance().attach(pid);
    }


    public List<String> getLoadedClassNames() {
        if(!AttachManager.getInstance().isAttached())
            return new ArrayList<>();

        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.GET_LOADED_CLASS_NAMES);

        List<String> names = new ArrayList<>();

        StringBuilder s = new StringBuilder();
        for(byte b : response.response) {
            if(b=='\0') {
                if(s.length()>1 && !s.toString().startsWith("[") && !s.toString().contains("$$Lambda$"))  {

                    names.add(s.toString());
                }
                s = new StringBuilder();
                continue;
            }
            s.append((char)b);
        }
        return names;
    }

    public List<Integer> getObjectTags(String klass) {
        return getObjectTags(klass, "");
    }


    public List<Integer> getObjectTags(String klass, String filter) {
        if(!AttachManager.getInstance().isAttached())
            return new ArrayList<>();

        klass += '\0';
        filter += '\0';

        byte[] a = klass.getBytes(StandardCharsets.UTF_8);
        byte[] b = filter.getBytes(StandardCharsets.UTF_8);
        byte[] c = new byte[a.length + b.length];
        System.arraycopy(a, 0, c, 0, a.length);
        System.arraycopy(b, 0, c, a.length, b.length);


        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.GET_OBJECT_TAGS,
                c);

        List<Integer> tags = new ArrayList<>();

        // size of long/int
        for(int i = 0; i < Math.min(response.response.length,40000); i+=4) {
            Integer l = Util.toInteger(response.response[i], response.response[i+1], response.response[i+2], response.response[i+3]);
            tags.add(l);
        }

        Logger.log("Got " + tags.size() + " objects.");

        return tags;
    }


    public FieldResponseData getFields(TagItem item) {
        String klass = item.getKlass();
        klass += '\0';


        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        byteBuffer.putInt(item.getTag());
        byte[] bytes = byteBuffer.array();


        byte[] klassBytes = klass.getBytes(StandardCharsets.UTF_8);
        byte[] buffer = new byte[bytes.length + klassBytes.length];

        System.arraycopy(bytes, 0, buffer, 0, bytes.length);
        System.arraycopy(klassBytes, 0, buffer, 4, klassBytes.length);


        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.GET_FIELDS,
                buffer);

        if(response.response.length==0) {
            return null;
        }
        try {
            ObjectMapper mapper = new ObjectMapper();
            return mapper.readValue(new String(response.response), FieldResponseData.class);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    static class ObjectValueRequest {
        public int tag;
        public String klass;
        public Object value;
    }

    public void setObjectValue(TagItem item, String value) {
        ObjectValueRequest req = new ObjectValueRequest();
        req.tag = item.getTag();
        req.value = value;
        req.klass = item.getKlass();


        ObjectWriter writer = new ObjectMapper().writer();

        try {
            String msg = writer.writeValueAsString(req);
            msg += '\0';
            System.out.println("Msg: " + msg);
            PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.SET_OBJECT,
                    msg.getBytes(StandardCharsets.UTF_8));
        } catch (JsonProcessingException e) {
            e.printStackTrace();
        }

    }



    public Map<Integer, SubGraphData> getReferences(TagItem item) {
        String klass = item.getKlass();
        klass += '\0';


        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        byteBuffer.putInt(item.getTag());
        byte[] bytes = byteBuffer.array();


        byte[] klassBytes = klass.getBytes(StandardCharsets.UTF_8);
        byte[] buffer = new byte[bytes.length + klassBytes.length];

        System.arraycopy(bytes, 0, buffer, 0, bytes.length);
        System.arraycopy(klassBytes, 0, buffer, 4, klassBytes.length);

        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.GET_REFS,
                buffer);

        if(response.response.length == 0) {
            return null;
        }

        try {
            ObjectMapper mapper = new ObjectMapper();

            Map<String, SubGraphData> data = mapper.readValue(new String(response.response), new TypeReference<Map<String, SubGraphData>>() {});
            Map<Integer, SubGraphData> map = new HashMap<>();

            for(Map.Entry<String, SubGraphData> entry : data.entrySet()) {
                map.put(Integer.valueOf(entry.getKey()), entry.getValue());
            }
            return map;
        } catch (Exception e) {
            e.printStackTrace();
        }

        return null;
    }


    public byte[] getClassData(String name) {
        if(!AttachManager.getInstance().isAttached())
            return new byte[0];

        name += '\0';

        if(classData.containsKey(name)) {
            Logger.log("Getting cached data");
            return classData.get(name);
        }

        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.GET_CLASS_DATA, name.getBytes(StandardCharsets.UTF_8));

        classData.put(name, response.response);
        return response.response;
    }


    byte[] getBreakpointMessage(String klassName, int methodIdx, int offset) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        byteBuffer.putInt(methodIdx);
        byte[] methodIdxBytes = byteBuffer.array();

        ByteBuffer other = ByteBuffer.allocate(4);
        other.order(ByteOrder.LITTLE_ENDIAN);
        other.putInt(offset);
        byte[] offsetBytes = other.array();


        byte[] klassBytes = klassName.getBytes(StandardCharsets.UTF_8);
        byte[] buffer = new byte[methodIdxBytes.length + offsetBytes.length + klassBytes.length];

        System.arraycopy(methodIdxBytes, 0, buffer, 0, methodIdxBytes.length);
        System.arraycopy(offsetBytes, 0, buffer, 4, offsetBytes.length);
        System.arraycopy(klassBytes, 0, buffer, 8, klassBytes.length);
        return buffer;
    }


    public boolean addBreakpoint(String klassName, int methodIdx, int offset) {
        klassName += '\0';
        Logger.log("Getting breakpoints for " + klassName + " @ " + methodIdx + " at offset " + offset);
        byte[] msg = getBreakpointMessage(klassName, methodIdx, offset);

        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.ADD_BREAKPOINT,
                msg);

        if(response.response.length == 0) {
            return false;
        }

        if(response.status != PipelineMain.ResponseStatus.OK) {
            Logger.log("There was an error adding breakpoint");
            return false;
        }

        return true;
    }

    public boolean clearBreakpoint(String klassName, int methodIdx, int offset) {
        klassName += '\0';
        Logger.log("Clearing breakpoints for " + klassName + " @ " + methodIdx + " at offset " + offset);
        byte[] msg = getBreakpointMessage(klassName, methodIdx, offset);

        PipelineMain.ClientResponse response = PipelineMain.getInstance().sendAndAwait(PipelineMain.ServerCommand.CLEAR_BREAKPOINT,
                msg);

        if(response.response.length == 0) {
            return false;
        }

        if(response.status != PipelineMain.ResponseStatus.OK) {
            Logger.log("There was an error clearing breakpoint");
            return false;
        }

        return true;
    }




    public static CoreInterface getInstance() {
        if(instance == null) instance = new CoreInterface();
        return instance;
    }


}
