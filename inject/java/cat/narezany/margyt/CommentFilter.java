package cat.narezany.margyt;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.lang.reflect.Method;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/** Removes comments by accounts published in the remote badges list.
 *
 * The endpoint is intentionally treated as an untrusted list of ids: malformed
 * replies never replace a working cached list, and a comment whose model is not
 * recognised is always left visible.  TikTok changes the class carrying a
 * comment page frequently, hence dexpatch redirects its stable getComments()
 * accessors here rather than tying the feature to an obfuscated response name.
 */
public final class CommentFilter {
    private CommentFilter() {}

    static final String KEY = "comment_filter_on";
    static final String SOURCE = "https://tiktokyou.yzewe.ru/api/v1/badges";
    private static final long EVERY = 5 * 60 * 1000L;
    private static final Set<String> EMPTY = Collections.emptySet();
    private static volatile Set<String> blocked = EMPTY;
    private static volatile Boolean enabled;
    private static volatile boolean started;

    public static boolean isEnabled() {
        Boolean known = enabled;
        if (known != null) return known.booleanValue();
        try {
            Context context = Margy.context();
            if (context == null) return true;
            boolean value = context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                    .getBoolean(KEY, true);
            enabled = Boolean.valueOf(value);
            return value;
        } catch (Throwable ignored) {
            return true;
        }
    }

    public static void setEnabled(boolean value) {
        enabled = Boolean.valueOf(value);
        try {
            Context context = Margy.context();
            if (context != null) context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                    .edit().putBoolean(KEY, value).apply();
        } catch (Throwable ignored) {
        }
    }

    public static synchronized void start(Context context) {
        if (started || context == null) return;
        started = true;
        final Context app = context.getApplicationContext();
        byte[] cached = Net.read(file(app));
        if (cached != null) apply(cached);
        Handler handler = new Handler(Looper.getMainLooper());
        handler.post(new Runnable() {
            @Override public void run() {
                refresh(app);
                new Handler(Looper.getMainLooper()).postDelayed(this, EVERY);
            }
        });
    }

    /** The rewrite target: return a fresh list so TikTok's shared response is untouched. */
    public static List getComments(Object response) {
        List original = originalComments(response);
        if (original == null || original.isEmpty() || !isEnabled()) return original;
        ArrayList kept = new ArrayList(original.size());
        boolean changed = false;
        for (Object comment : original) {
            if (shouldHide(comment)) changed = true;
            else kept.add(comment);
        }
        return changed ? kept : original;
    }

    private static List originalComments(Object response) {
        if (response == null) return null;
        try {
            Method method = response.getClass().getMethod("getComments");
            Object value = method.invoke(response);
            return value instanceof List ? (List) value : null;
        } catch (Throwable ignored) {
            return null;
        }
    }

    private static boolean shouldHide(Object comment) {
        Object user = call(comment, "getUser");
        if (user == null) user = call(comment, "getAuthor");
        if (user == null) return false;
        Object uid = call(user, "getUid");
        if (uid != null && blocked.contains(String.valueOf(uid))) return true;
        return verified(user) && suspiciousName(String.valueOf(call(user, "getNickname")));
    }

    private static Object call(Object target, String name) {
        if (target == null) return null;
        try { return target.getClass().getMethod(name).invoke(target); }
        catch (Throwable ignored) { return null; }
    }

    private static boolean verified(Object user) {
        Object type = call(user, "getVerificationType");
        if (type instanceof Number && ((Number) type).intValue() > 0) return true;
        Object flag = call(user, "isVerified");
        return flag instanceof Boolean && ((Boolean) flag).booleanValue();
    }

    // Exact normalised display names only.  Do not hide ordinary accounts
    // merely because their name contains a game title or a country.
    static boolean suspiciousName(String name) {
        if (name == null) return false;
        String plain = Normalizer.normalize(name, Normalizer.Form.NFKC)
                .trim().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
        return "roblox russia".equals(plain) || "brawl stars russia".equals(plain);
    }

    private static void refresh(final Context context) {
        Net.away("comment-filter", new Runnable() {
            @Override public void run() {
                byte[] fresh = Net.bytes(SOURCE);
                if (fresh == null) return;
                if (apply(fresh)) Net.save(file(context), fresh);
            }
        });
    }

    static boolean apply(byte[] json) {
        try {
            JSONArray entries = new JSONArray(new String(json, "UTF-8"));
            Set<String> next = new HashSet<String>();
            for (int i = 0; i < entries.length(); i++) {
                JSONObject entry = entries.optJSONObject(i);
                if (entry == null) continue;
                String uid = entry.optString("uid", "").trim();
                if (uid.matches("[0-9]{1,32}")) next.add(uid);
            }
            blocked = Collections.unmodifiableSet(next);
            Diary.note("comment filter: " + next.size() + " accounts from badges API");
            return true;
        } catch (Throwable error) {
            Diary.note("comment filter: unreadable, keeping the last list -- " + error);
            return false;
        }
    }

    private static File file(Context context) {
        return new File(new File(context.getFilesDir(), "margyt"), "comment-filter.json");
    }
}
