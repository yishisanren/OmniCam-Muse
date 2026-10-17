package local.jiege.hook.guard;

import android.os.Build;
import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Iterator;
import java.util.zip.ZipFile;
import org.json.JSONObject;
import local.jiege.hook.common.Log;

/** A newly installed APK remains inactive until its paired boot resources are ready. */
public final class DeviceGuard {
    private static JSONObject profile;
    private static String fingerprint;

    public static void load(String modulePath) {
        try (ZipFile apk = new ZipFile(modulePath);
             InputStream input = apk.getInputStream(apk.getEntry("assets/device_profile.json"))) {
            byte[] bytes = read(input);
            profile = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            fingerprint = digest(bytes);
        } catch (Exception error) {
            profile = null;
            Log.e("Muse", "device profile unavailable", error);
        }
    }

    public static boolean matchesDevice() {
        return profile != null && Build.MODEL.equals(profile.optString("model"))
            && Build.DISPLAY.equals(profile.optString("firmware"));
    }

    public static boolean cameraReady(String apkPath, String dataDir) {
        try {
            if (!profile.getString("apk_sha256").equals(fileDigest(apkPath))) return false;
            try (InputStream input = new FileInputStream(dataDir + "/files/jiege/muse_profile.sha256")) {
                if (!fingerprint.equals(new String(read(input), StandardCharsets.UTF_8).trim())) return false;
            }
            JSONObject files = profile.getJSONObject("mounted_files");
            for (Iterator<String> it = files.keys(); it.hasNext();) {
                String path = it.next();
                if (!files.getString(path).equals(fileDigest(path))) return false;
            }
            return true;
        } catch (Exception error) {
            Log.i("Muse", "paired resources not ready: " + error.getClass().getSimpleName());
            return false;
        }
    }

    public static boolean resourcesReady() {
        if (!matchesDevice()) return false;
        try {
            JSONObject files = profile.getJSONObject("mounted_files");
            for (Iterator<String> it = files.keys(); it.hasNext();) {
                String path = it.next();
                if (!files.getString(path).equals(fileDigest(path))) return false;
            }
            return true;
        } catch (Exception error) {
            return false;
        }
    }

    private static byte[] read(InputStream input) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        for (int n; (n = input.read(buffer)) != -1;) out.write(buffer, 0, n);
        return out.toByteArray();
    }

    private static String fileDigest(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(path)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = input.read(buffer)) != -1;) digest.update(buffer, 0, n);
        }
        return hex(digest.digest());
    }

    private static String digest(byte[] bytes) throws Exception {
        return hex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder();
        for (byte value : bytes) out.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
        return out.toString();
    }
}
