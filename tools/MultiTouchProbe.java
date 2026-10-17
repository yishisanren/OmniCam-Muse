import android.os.SystemClock;
import android.os.Looper;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.MotionEvent;
import java.lang.reflect.Method;

/** A short, bounded two-finger gesture; no app or accessibility settings are changed. */
public final class MultiTouchProbe {
    static Object manager;
    static Method inject;
    static final MotionEvent.PointerProperties[] properties = new MotionEvent.PointerProperties[2];
    static final MotionEvent.PointerCoords[] points = new MotionEvent.PointerCoords[2];
    static long down;

    static void event(int action, int count, float x, float y) throws Exception {
        for (int i = 0; i < count; ++i) { points[i].x = x; points[i].y = y + i * 36; }
        MotionEvent event = MotionEvent.obtain(down, SystemClock.uptimeMillis(), action, count,
            properties, points, 0, 0, 1, 1, 0, 0, InputDevice.SOURCE_TOUCHSCREEN, 0);
        try {
            if (!Boolean.TRUE.equals(inject.invoke(manager, event, 2))) throw new IllegalStateException("Input injection rejected");
        } finally { event.recycle(); }
    }

    public static void main(String[] args) throws Exception {
        Looper.prepareMainLooper();
        if (args.length != 5) throw new IllegalArgumentException("x1 y1 x2 y2 duration_ms");
        float x1 = Float.parseFloat(args[0]), y1 = Float.parseFloat(args[1]);
        float x2 = Float.parseFloat(args[2]), y2 = Float.parseFloat(args[3]);
        int duration = Integer.parseInt(args[4]);
        if (duration < 100 || duration > 1500 || Math.min(x1, x2) < 0 || Math.max(x1, x2) > 1215 ||
            Math.min(y1, y2) < 0 || Math.max(y1, y2) + 36 > 2639) throw new IllegalArgumentException("Gesture outside phone bounds");
        Class<?> type = Class.forName("android.hardware.input.InputManagerGlobal");
        manager = type.getMethod("getInstance").invoke(null);
        inject = type.getMethod("injectInputEvent", InputEvent.class, int.class);
        for (int i = 0; i < 2; ++i) {
            properties[i] = new MotionEvent.PointerProperties();
            properties[i].id = i;
            properties[i].toolType = MotionEvent.TOOL_TYPE_FINGER;
            points[i] = new MotionEvent.PointerCoords();
            points[i].pressure = 1;
            points[i].size = .01f;
        }
        down = SystemClock.uptimeMillis();
        boolean first = false, second = false;
        float x = x1, y = y1;
        try {
            first = true; event(MotionEvent.ACTION_DOWN, 1, x, y);
            second = true; event(MotionEvent.ACTION_POINTER_DOWN | (1 << MotionEvent.ACTION_POINTER_INDEX_SHIFT), 2, x, y);
            int steps = Math.max(6, duration / 20);
            for (int i = 1; i <= steps; ++i) {
                SystemClock.sleep(duration / steps);
                x = x1 + (x2 - x1) * i / steps;
                y = y1 + (y2 - y1) * i / steps;
                event(MotionEvent.ACTION_MOVE, 2, x, y);
            }
        } finally {
            try { if (second) event(MotionEvent.ACTION_POINTER_UP | (1 << MotionEvent.ACTION_POINTER_INDEX_SHIFT), 2, x, y); }
            finally { if (first) event(MotionEvent.ACTION_UP, 1, x, y); }
        }
        System.out.println("Two-finger gesture completed");
        System.exit(0);
    }
}
