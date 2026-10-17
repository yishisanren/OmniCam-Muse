import android.content.Context;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.os.Looper;
import android.util.SizeF;
import java.util.LinkedHashSet;
import org.json.JSONArray;
import org.json.JSONObject;

/** Reads public calibration metadata without opening a camera or changing settings. */
public final class CameraProfileProbe {
    static boolean zoomKey(String name) {
        String lower = name.toLowerCase(java.util.Locale.ROOT);
        return lower.contains("sensor") || lower.contains("crop") || lower.contains("zoom");
    }
    static JSONArray matrix(ColorSpaceTransform matrix) throws Exception {
        if (matrix == null) return null;
        JSONArray values = new JSONArray();
        for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++)
            values.put(matrix.getElement(c, r).doubleValue());
        return values;
    }

    public static void main(String[] args) throws Exception {
        Looper.prepareMainLooper();
        Class<?> type = Class.forName("android.app.ActivityThread");
        Object thread = type.getMethod("systemMain").invoke(null);
        Context context = (Context) type.getMethod("getSystemContext").invoke(thread);
        CameraManager manager = context.getSystemService(CameraManager.class);
        LinkedHashSet<String> ids = new LinkedHashSet<>();
        for (String id : manager.getCameraIdList()) {
            ids.add(id);
            ids.addAll(manager.getCameraCharacteristics(id).getPhysicalCameraIds());
        }
        JSONObject result = new JSONObject();
        for (String id : ids) {
            JSONObject row = new JSONObject();
            try {
                CameraCharacteristics c = manager.getCameraCharacteristics(id);
                SizeF size = c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE);
                float[] focal = c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS);
                row.put("facing", c.get(CameraCharacteristics.LENS_FACING));
                row.put("physical_ids", new JSONArray(c.getPhysicalCameraIds()));
                if (size != null && focal != null && focal.length > 0)
                    row.put("equivalent_focal", focal[0] * 43.2666 / Math.hypot(size.getWidth(), size.getHeight()));
                row.put("illuminant1", c.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1));
                row.put("illuminant2", c.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2));
                row.put("forward1", matrix(c.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1)));
                row.put("forward2", matrix(c.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2)));
                row.put("calibration1", matrix(c.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1)));
                row.put("calibration2", matrix(c.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2)));
                JSONArray requestKeys = new JSONArray(), resultKeys = new JSONArray();
                for (CaptureRequest.Key<?> key : c.getAvailableCaptureRequestKeys())
                    if (zoomKey(key.getName())) requestKeys.put(key.getName());
                for (CaptureResult.Key<?> key : c.getAvailableCaptureResultKeys())
                    if (zoomKey(key.getName())) resultKeys.put(key.getName());
                row.put("zoom_request_keys", requestKeys);
                row.put("zoom_result_keys", resultKeys);
            } catch (Exception error) {
                row.put("error", error.toString());
            }
            result.put(id, row);
        }
        System.out.println(result.toString());
        System.exit(0);
    }
}
