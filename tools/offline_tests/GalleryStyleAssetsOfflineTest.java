import java.io.File;
import local.jiege.hook.gr.GalleryStyleAssets;

public final class GalleryStyleAssetsOfflineTest {
    public static void main(String[] args) {
        File staged = new File("/private/gallery/ricoh_gr_styles");
        for (int i = 1; i <= 5; i++) {
            String name = "gr_style_" + i + ".json";
            if (!new File(staged, name).equals(GalleryStyleAssets.resolve(staged, "watermark_master_styles/" + name)))
                throw new AssertionError("GR asset lost: " + name);
        }
        String[] stock = {null, "gr_style_1.json", "other/gr_style_1.json", "watermark_master_styles/lumo_style_1.json",
            "watermark_master_styles/gr_style_1.json/secret", "watermark_master_styles/../gr_style_1.json",
            "watermark_master_styles/gr_style_../secret.json", "watermark_master_styles/gr_style_1\\secret.json",
            "watermark_master_styles/gr_style_1.png", "watermark_master_styles/gr_style_0.json"};
        for (String path : stock) {
            if (GalleryStyleAssets.resolve(staged, path) != null)
                throw new AssertionError("Unrelated or unsafe asset intercepted: " + path);
        }
        System.out.println("GR assets 1..5, stock fallthrough, traversal rejection: PASS");
    }
}
