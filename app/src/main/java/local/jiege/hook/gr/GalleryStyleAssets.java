package local.jiege.hook.gr;

import java.io.File;

/** Routes only staged GR style JSON assets; all other assets retain their stock loader. */
public final class GalleryStyleAssets {
    private static final String PREFIX = "watermark_master_styles/";

    private GalleryStyleAssets() {}

    public static File resolve(File directory, String asset) {
        if (asset == null || !asset.startsWith(PREFIX)) return null;
        String name = asset.substring(PREFIX.length());
        if (!name.matches("gr_style_[1-9][0-9]*\\.json")) return null;
        return new File(directory, name);
    }
}
