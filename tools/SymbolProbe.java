import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Map;
import java.util.List;
import org.json.JSONObject;
import org.json.JSONArray;
import org.luckypray.dexkit.DexKitBridge;
import local.jiege.hook.common.SymbolSearch;

/** Runs the production fingerprint search without loading or changing camera classes. */
public final class SymbolProbe {
    public static void main(String[] args) throws Exception {
        System.load(args[0]);
        JSONObject spec = new JSONObject(new String(Files.readAllBytes(Paths.get(args[2])), java.nio.charset.StandardCharsets.UTF_8));
        try (DexKitBridge bridge = DexKitBridge.create(args[1])) {
            SymbolSearch search = SymbolSearch.run(bridge, spec.getJSONObject(args[3]));
            JSONObject resolved = new JSONObject();
            for (Map.Entry<String, List<String>> entry : search.resolved.entrySet())
                resolved.put(entry.getKey(), new JSONArray(entry.getValue()));
            System.out.println(new JSONObject().put("resolved", resolved).put("failures", new JSONObject(search.failures)));
        }
    }
}
