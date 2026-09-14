package cat.narezany.margyt;

import android.content.Context;

import com.ss.android.ugc.aweme.comment.model.Comment;
import com.ss.android.ugc.aweme.profile.model.User;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.text.Normalizer;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Hides comments only when their author is verified and their display name
 * matches a deliberately narrow rule from comment-filter.json.  Rules are
 * full-name matches: neither a word in an otherwise unrelated name nor an
 * unverified account is enough.
 */
public final class CommentFilter {
    public static final String KEY = "comment_filter_on";
    private static final String CUSTOM_KEY = "comment_filter_names";
    private static final String SOURCE =
            "https://raw.githubusercontent.com/narezany/MargyT/main/comment-filter.json";
    private static final long EVERY = 5 * 60 * 1000L;

    private static volatile Boolean enabled;
    private static volatile Rules rules = Rules.EMPTY;
    private static volatile boolean started;

    private CommentFilter() {}

    /** Hook target: a null author makes TikTok omit this comment's author row. */
    public static User getUser(Comment comment) {
        if (comment == null) return null;
        User author = comment.getUser();
        return shouldHide(author) ? null : author;
    }

    public static boolean shouldHide(User author) {
        if (!isEnabled() || author == null || !author.isVerified()) return false;
        String uid = author.getUid();
        if (rules.allowUids.contains(uid)) return false;
        String name = normalise(author.getNickname());
        if (name.length() == 0 || rules.allowNames.contains(name)) return false;
        return rules.names.contains(name) || matches(rules.patterns, name)
                || customNames().contains(name);
    }

    /** NFKC, trim, Locale.ROOT case-fold and one ASCII space between words. */
    static String normalise(String value) {
        if (value == null) return "";
        return Normalizer.normalize(value, Normalizer.Form.NFKC)
                .trim().toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
    }

    public static boolean isEnabled() {
        Boolean remembered = enabled;
        if (remembered != null) return remembered;
        Context context = Margy.context();
        if (context == null) return true;
        boolean value = context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                .getBoolean(KEY, true);
        enabled = value;
        return value;
    }

    public static void setEnabled(boolean value) {
        enabled = value;
        Context context = Margy.context();
        if (context != null) context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(KEY, value).apply();
    }

    /** Newline-separated exact display names set locally by the user. */
    public static String customNamesText() {
        Context context = Margy.context();
        return context == null ? "" : context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                .getString(CUSTOM_KEY, "");
    }

    public static void setCustomNamesText(String value) {
        Context context = Margy.context();
        if (context != null) context.getSharedPreferences(Margy.PREFS, Context.MODE_PRIVATE)
                .edit().putString(CUSTOM_KEY, value == null ? "" : value).apply();
    }

    private static Set<String> customNames() {
        String text = customNamesText();
        if (text.length() == 0) return Collections.emptySet();
        Set<String> names = new HashSet<String>();
        for (String line : text.split("\\r?\\n")) {
            String name = normalise(line);
            if (name.length() > 0) names.add(name);
        }
        return names;
    }

    public static synchronized void start(final Context context) {
        if (started) return;
        started = true;
        byte[] cached = Net.read(file(context));
        if (cached != null) apply(cached);
        final android.os.Handler handler = new android.os.Handler(android.os.Looper.getMainLooper());
        handler.post(new Runnable() { @Override public void run() {
            refresh(context.getApplicationContext());
            handler.postDelayed(this, EVERY);
        }});
    }

    private static void refresh(final Context context) {
        Net.away("comment filter", new Runnable() { @Override public void run() {
            byte[] fresh = Net.bytes(SOURCE);
            if (fresh == null) return;
            byte[] old = Net.read(file(context));
            if (old != null && Arrays.equals(old, fresh)) return;
            if (apply(fresh)) Net.save(file(context), fresh);
        }});
    }

    private static boolean apply(byte[] raw) {
        try {
            JSONObject root = new JSONObject(new String(raw, "UTF-8"));
            if (root.optInt("version", 0) != 1) return false;
            Set<String> names = names(root.optJSONArray("names"));
            Set<String> allowNames = names(root.optJSONArray("allowlist_names"));
            Set<String> allowUids = strings(root.optJSONArray("allowlist_uids"));
            JSONArray sourcePatterns = root.optJSONArray("patterns");
            Pattern[] patterns = new Pattern[sourcePatterns == null ? 0 : sourcePatterns.length()];
            for (int i = 0; i < patterns.length; i++) {
                String expression = sourcePatterns.optString(i, "");
                // Config patterns are documented as anchored full-name regexes.
                if (!expression.startsWith("^") || !expression.endsWith("$")) return false;
                patterns[i] = Pattern.compile(expression);
            }
            rules = new Rules(names, allowNames, allowUids, patterns);
            return true;
        } catch (Throwable error) {
            Diary.note("comment filter: unreadable, keeping last rules -- " + error);
            return false;
        }
    }

    private static boolean matches(Pattern[] patterns, String name) {
        for (Pattern pattern : patterns) if (pattern.matcher(name).matches()) return true;
        return false;
    }
    private static Set<String> names(JSONArray source) {
        Set<String> result = new HashSet<String>();
        if (source != null) for (int i = 0; i < source.length(); i++) {
            String value = normalise(source.optString(i, ""));
            if (value.length() > 0) result.add(value);
        }
        return result;
    }
    private static Set<String> strings(JSONArray source) {
        Set<String> result = new HashSet<String>();
        if (source != null) for (int i = 0; i < source.length(); i++) {
            String value = source.optString(i, ""); if (value.length() > 0) result.add(value);
        }
        return result;
    }
    private static File file(Context context) {
        return new File(context.getFilesDir(), "margyt/comment-filter.json");
    }
    private static final class Rules {
        static final Rules EMPTY = new Rules(Collections.<String>emptySet(), Collections.<String>emptySet(), Collections.<String>emptySet(), new Pattern[0]);
        final Set<String> names, allowNames, allowUids; final Pattern[] patterns;
        Rules(Set<String> names, Set<String> allowNames, Set<String> allowUids, Pattern[] patterns) {
            this.names = names; this.allowNames = allowNames; this.allowUids = allowUids; this.patterns = patterns;
        }
    }
}
