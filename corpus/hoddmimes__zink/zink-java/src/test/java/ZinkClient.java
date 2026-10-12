import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import javax.imageio.plugins.tiff.TIFFImageReadParam;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.attribute.UserDefinedFileAttributeView;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.text.SimpleDateFormat;
import java.util.Properties;
import java.util.Random;

public class ZinkClient
{
    private static int RECORD_COUNT = 100;

    private int mHttpsPort = 8282;
    private String mApiKey = "test";
    private String mApplication = "test";
    private String mHost = "127.0.0.1";
    HttpClient mClient;
    private String mURIPath;
    private long mStartSaveTime,mStopSaveTime;
    private Random rnd = new Random(System.nanoTime());
    private String mDeleteApiKey = "delete-key";

    TrustManager[] trustAllCerts = new TrustManager[]{
            new X509TrustManager() {
                public void checkClientTrusted(X509Certificate[] chain, String authType) {}
                public void checkServerTrusted(X509Certificate[] chain, String authType) {}
                public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
            }
    };



    public static void main(String[] args) {
        ZinkClient zk = new ZinkClient();
        zk.parseArguments( args );
        zk.createHttpClient();
        zk.deleteDB();
        zk.saveData();
        zk.findData();
    }

    private void createHttpClient() {
        try {
            SSLContext sslContext = SSLContext.getInstance("TLS");
            sslContext.init(null, trustAllCerts, new SecureRandom());

            Properties props = System.getProperties();
            props.setProperty("jdk.internal.httpclient.disableHostnameVerification", Boolean.TRUE.toString());

            mClient = HttpClient.newBuilder()
                    .sslContext(sslContext)
                    .build();
        }
        catch( Exception e) {
            new RuntimeException(e);
        }



    }

    private void findData() {
        JsonObject rqst;
        SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss,SSS");


        long before,after;
        rqst = new JsonObject();
        rqst.addProperty("application", mApplication);
        long tTimeDiff = mStopSaveTime - mStartSaveTime;
        int choice = rnd.nextInt(4);

        switch( choice ) {
            case 0:
                // Do nothing get all
                break;
            case 1:
                after = mStartSaveTime + 10L + rnd.nextLong(tTimeDiff);
                rqst.addProperty("after", simpleDateFormat.format( after ));
                break;
            case 2:
                before = mStopSaveTime - 10L - rnd.nextLong(tTimeDiff);
                rqst.addProperty("before", simpleDateFormat.format( before ));
                break;
            case 3:
                long x = rnd.nextLong(tTimeDiff);
                after = mStartSaveTime + 10L + x;
                before = after + rnd.nextLong(tTimeDiff - x) + 5L;
                rqst.addProperty("before", simpleDateFormat.format( before ));
                rqst.addProperty("after", simpleDateFormat.format( after ));
                break;
        }

        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(new URI(mURIPath + "find"))
                    .header("Authorization", "apikey " + mApiKey )
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(rqst.toString())).build();

            System.out.println("[Find Request] choice: " + choice + " rqst: " + rqst.toString());
            HttpResponse<String> response = mClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                System.out.println("[Find Error] Status: " + response.statusCode() + " Error: " + response.body());
            }
            JsonArray jFinds = JsonParser.parseString(response.body()).getAsJsonArray();
            for (int i = 0; i < jFinds.size(); i++) {
                System.out.println( jFinds.get(i).getAsJsonObject().toString());
            }
        }
        catch( Exception e ) {
            new RuntimeException(e);
        }
    }

    private void saveData() {
        try {
            JsonObject rqst;
            mStartSaveTime = System.currentTimeMillis();
            for (int i = 0; i < RECORD_COUNT; i++) {
                rqst = new JsonObject();
                rqst.addProperty("application", mApplication );
                if ((i % 2) == 0) {
                    rqst.addProperty("tag", "tag-%03d".formatted(i));
                }
                rqst.addProperty("data", "Data item %d ".formatted(i));
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(new URI(mURIPath + "save"))
                        .header("Authorization", "apikey " + mApiKey )
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(rqst.toString())).build();

                HttpResponse<String> response = mClient.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() != 200) {
                    System.out.println("[Save Error] Status: " + response.statusCode() + " Eroor: " + response.body());
                }

                if ((i % 10) == 0) {
                    try {Thread.sleep(50L);}
                    catch(InterruptedException e) {}
                }
            }

            mStopSaveTime = System.currentTimeMillis();
            System.out.println("[SAVED] %d records".formatted(RECORD_COUNT) + " save-diff: " + (mStopSaveTime - mStartSaveTime) + " ms.");
        }
        catch( Exception e) {
            new RuntimeException(e);
        }
    }

    private void deleteDB() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .header("Authorization", "apikey " + mDeleteApiKey )
                    .uri(new URI(mURIPath+ "delete"))
                    .DELETE()
                    .build();

            HttpResponse<String> response = mClient.send(request, HttpResponse.BodyHandlers.ofString());

            System.out.println("[DELETE] status: " + response.statusCode() + " Response body: " + response.body());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }


    private void parseArguments( String[] args ) {
        int i = 0;
        while( i < args.length ) {
            if (args[i].contentEquals("-host")) {
                mHost = args[++i];
            }
            if (args[i].contentEquals("-application")) {
                mApplication = args[++i];
            }
            if (args[i].contentEquals("-apikey")) {
                mApiKey = args[++i];
            }
            if (args[i].contentEquals("-port")) {
                mHttpsPort = Integer.parseInt(args[++i]);
            }
            i++;
        }
        mURIPath = "https://" + mHost + ":" + String.valueOf(mHttpsPort ) + "/";
    }
}
