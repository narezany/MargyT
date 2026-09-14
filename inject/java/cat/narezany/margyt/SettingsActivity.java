package cat.narezany.margyt;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.List;
import java.util.Locale;

/**
 * MargyT's own screen, drawn in TikTok's settings language.
 *
 * Page, cards, title, grey section labels: the shapes are TikTok's, and so are
 * the colours -- not copied out of a screenshot but the ones the row measured
 * off the real settings screen and kept. Opened from the launcher with TikTok
 * never having been on screen, it falls back to plain black or white.
 *
 * Every view is built here in code. Adding a layout or a style would mean
 * adding resources, and adding resources means rewriting a 25 MB resource
 * table -- the one thing this build refuses to do.
 */
public class SettingsActivity extends Activity {

    private Skin skin;
    private FrameLayout root;
    private LinearLayout column;
    private View restartBar;

    /**
     * Whether a setting was changed in this process.
     *
     * Static, because the bar is about the process and not about the screen:
     * leaving the settings and coming back does not un-change what was changed,
     * and only a restart -- which is a new process, where this is false again --
     * does.
     */
    private static boolean pending;

    /** Where the mod, its people and its money live. */
    private static final String CHANNEL = "https://t.me/margytiktok";
    private static final String FORUM = "https://t.me/margeletforum";
    private static final String OWNER_TELEGRAM = "https://t.me/narezany";
    private static final String OWNER_TIKTOK =
            "https://tiktok.com/@narezany?_r=1&_t=ZT-99hPDJ26hji_";
    private static final String HELPER = "https://www.tiktok.com/@MS4wLjABAAAApBE7v5"
            + "y_tClqKlwqBpZNwzIBn1K7aRJLDxegPPnx8joas1EmS8NZpVFdWATb4zGf";
    private static final String GITHUB = "https://github.com/narezany/MargyT";
    private static final String DOCS =
            "https://github.com/narezany/MargyT/blob/main/docs/plugins.md";
    private static final String YOOMONEY = "https://yoomoney.ru/to/4100118196133693";
    private static final String CARD_NUMBER = "2204120143055305";

    private boolean countriesOpen;
    private boolean accentOpen;
    private boolean textOpen;
    private boolean backgroundOpen;
    private boolean thanksOpen;
    private boolean streakOpen;
    private boolean diaryOpen;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Margy.attach(this);
        skin = Skin.remembered(this);
        dressTheWindow();

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(skin.page);
        scroll.setFillViewport(true);

        column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(0, statusBar(), 0, dp(32));
        scroll.addView(column, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        root = new FrameLayout(this);
        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        setContentView(root);
        rebuild();
    }

    @Override
    protected void onResume() {
        super.onResume();
        rebuild();
    }

    private void dressTheWindow() {
        try {
            getWindow().setStatusBarColor(skin.page);
            getWindow().setNavigationBarColor(skin.page);
            if (!skin.dark()) {
                getWindow().getDecorView().setSystemUiVisibility(
                        View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
            }
        } catch (Throwable ignored) {
        }
    }

    // --------------------------------------------------------- the screen

    private void rebuild() {
        column.removeAllViews();
        column.addView(backArrow());
        column.addView(title("MargyT"));

        column.addView(section(Text.REGION));
        LinearLayout head = card();
        head.addView(switchRow());
        column.addView(wrap(head));

        column.addView(section(Text.COUNTRY));
        LinearLayout countries = card();
        countries.addView(countryHead());
        if (countriesOpen) {
            countries.addView(line());
            for (String[] country : Margy.COUNTRIES) {
                countries.addView(countryRow(country));
            }
        }
        column.addView(wrap(countries));

        column.addView(section(Text.ACCENT));
        LinearLayout accent = card();
        accent.addView(accentHead());
        if (accentOpen) {
            accent.addView(line());
            accent.addView(palette());
        }
        column.addView(wrap(accent));

        column.addView(section(Text.THEME));
        LinearLayout theme = card();
        theme.addView(toggleRow("contrast", Text.THEME_ON, Themes.isEnabled(), on -> {
            Themes.setEnabled(on);
            rebuild();
        }));
        if (Themes.isEnabled()) {
            theme.addView(line());
            theme.addView(toggleRow("wallpaper", Text.THEME_MATERIAL,
                    Themes.isMaterial(), on -> {
                        Themes.setMaterial(on);
                        rebuild();
                    }));
            if (!Themes.isMaterial()) {
                theme.addView(line());
                theme.addView(shadeHead(true));
                if (textOpen) {
                    theme.addView(line());
                    theme.addView(shades(true));
                }
                theme.addView(line());
                theme.addView(shadeHead(false));
                if (backgroundOpen) {
                    theme.addView(line());
                    theme.addView(shades(false));
                }
            }
            theme.addView(line());
            theme.addView(quiet(Text.THEME_NOTE));
        }
        column.addView(wrap(theme));

        column.addView(section(Text.FEED));
        LinearLayout feed = card();
        feed.addView(toggleRow("block", Text.HIDE_ADS, Feed.isEnabled(), Feed::setEnabled));
        column.addView(wrap(feed));

        column.addView(section(Text.COMMENT_FILTER));
        LinearLayout commentFilter = card();
        commentFilter.addView(toggleRow("visibility_off", Text.COMMENT_FILTER_ON,
                CommentFilter.isEnabled(), CommentFilter::setEnabled));
        commentFilter.addView(line());
        commentFilter.addView(commentFilterNamesRow());
        column.addView(wrap(commentFilter));
        column.addView(caption(Text.COMMENT_FILTER_NOTE));

        column.addView(section(Text.VIDEO));
        LinearLayout video = card();
        video.addView(toggleRow("volume_up", Text.SOUND, Sound.isEnabled(), Sound::setEnabled));
        video.addView(line());
        video.addView(toggleRow("timeline", Text.SEEKBAR, Seekbar.isEnabled(), Seekbar::setEnabled));
        column.addView(wrap(video));

        column.addView(section(Text.HIDDEN));
        LinearLayout hidden = card();
        String[][] antiAb = {
                {"play_circle", Text.BACKGROUND, Flags.KEY_BACKGROUND},
                {"swap_vert", Text.AUTOSCROLL, Flags.KEY_AUTOSCROLL},
                {"mic", Text.VOICE, Flags.KEY_VOICE},
        };
        for (int i = 0; i < antiAb.length; i++) {
            if (i > 0) hidden.addView(line());
            final String key = antiAb[i][2];
            hidden.addView(toggleRow(antiAb[i][0], antiAb[i][1], Flags.isOn(key),
                    on -> Flags.set(key, on)));
        }
        column.addView(wrap(hidden));
        column.addView(caption(Text.HIDDEN_NOTE));

        column.addView(section(Text.DOWNLOADS));
        LinearLayout downloads = card();
        downloads.addView(toggleRow("image", Text.NO_WATERMARK, Download.isEnabled(),
                Download::setEnabled));
        downloads.addView(line());
        downloads.addView(toggleRow("download", Text.DOWNLOAD_ALWAYS, Download.isAlways(),
                Download::setAlways));
        downloads.addView(line());
        downloads.addView(toggleRow("place", Text.SAVE_AVATARS_ON, Avatars.isEnabled(),
                Avatars::setEnabled));
        downloads.addView(line());
        downloads.addView(toggleRow("star", Text.SAVE_STICKERS_ON, Stickers.isEnabled(),
                Stickers::setEnabled));
        column.addView(wrap(downloads));

        column.addView(section(Text.PLUGINS));
        LinearLayout plugins = card();
        plugins.addView(installRow());
        plugins.addView(line());
        plugins.addView(linkRow("article", Text.PLUGIN_DOCS, Text.PLUGIN_DOCS_NOTE, DOCS));
        List<Plugins.Info> installed = Plugins.list();
        if (installed.isEmpty()) {
            plugins.addView(line());
            plugins.addView(quiet(Text.PLUGIN_NONE));
        } else {
            for (Plugins.Info info : installed) {
                plugins.addView(line());
                plugins.addView(pluginRow(info));
            }
        }
        column.addView(wrap(plugins));
        column.addView(caption(Text.PLUGIN_WARNING));

        column.addView(section(Text.LINKS));
        LinearLayout links = card();
        links.addView(linkRow("link", Text.CHANNEL, "@margytiktok", CHANNEL));
        links.addView(line());
        links.addView(linkRow("group", Text.FORUM, "@margeletforum", FORUM));
        links.addView(line());
        links.addView(linkRow("extension", Text.SOURCE, "narezany/MargyT", GITHUB));
        links.addView(line());
        links.addView(toggleRow("favorite_border", Text.BADGES_ON, Badges.isEnabled(),
                Badges::setEnabled));
        links.addView(line());
        links.addView(toggleRow("visibility_off", Text.COMMENT_FILTER_ON,
                CommentFilter.isEnabled(), CommentFilter::setEnabled));
        links.addView(line());
        links.addView(thanksHead());
        if (thanksOpen) {
            links.addView(line());
            links.addView(thanks());
        }
        column.addView(wrap(links));

        column.addView(section(Text.ACCOUNT));
        LinearLayout account = card();
        account.addView(idRow(Text.ACCOUNT_ID, Account.id()));
        account.addView(line());
        account.addView(idRow(Text.ACCOUNT_SEC_ID, Account.secId()));
        column.addView(wrap(account));

        column.addView(section(Text.STREAKS));
        LinearLayout streaks = card();
        streaks.addView(betaRow("repeat", Text.STREAK_AUTO, Streaks.isEnabled(),
                Streaks::setEnabled));
        streaks.addView(line());
        streaks.addView(stickerHead());
        if (streakOpen) {
            streaks.addView(line());
            streaks.addView(stickerChoices());
        }
        column.addView(wrap(streaks));
        column.addView(caption(Text.STREAK_NOTE));

        column.addView(section(Text.UPDATE));
        LinearLayout updates = card();
        updates.addView(actionRow("download", Text.UPDATE_CHECK,
                Updater.newer() ? Text.UPDATE_THERE_IS + " " + Updater.latest() : null,
                () -> Updater.check(this, true)));
        updates.addView(line());
        updates.addView(toggleRow("info", Text.UPDATE_REMIND, Updater.remind(this),
                on -> Updater.setRemind(this, on)));
        if (Updater.waiting(this)) {
            updates.addView(line());
            updates.addView(actionRow("extension", Text.UPDATE_INSTALL, null,
                    () -> Updater.install(this)));
        }
        column.addView(wrap(updates));

        column.addView(section(Text.DIARY));
        LinearLayout diary = card();
        diary.addView(diaryHead());
        if (diaryOpen) {
            diary.addView(line());
            diary.addView(diaryLines());
        }
        column.addView(wrap(diary));

        column.addView(versions());

        showRestartBar();
    }

    /**
     * The bar that says a restart is due, pinned to the foot of the screen.
     *
     * It sits in the root frame rather than in the column, so it stays put
     * while the page scrolls under it, and it is built again on every rebuild
     * because the accent it is painted with may be what just changed.
     */
    private void showRestartBar() {
        if (restartBar != null) {
            root.removeView(restartBar);
            restartBar = null;
        }
        if (pending) {
            restartBar = restartBar();
            root.addView(restartBar, new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM));
        }
        // the last card has to be able to clear the bar when it is there
        column.setPadding(0, statusBar(), 0,
                dp(32) + (pending ? dp(64) + navigationBar() : 0));
    }

    /** A setting changed: redraw, and from now on the bar is up. */
    private void markChanged() {
        pending = true;
        rebuild();
    }

    // ----------------------------------------------------------- the rows

    private View switchRow() {
        LinearLayout row = row();
        row.addView(icon("language"));
        row.addView(label(Text.CHANGE_REGION), grow());

        final M3Switch toggle = new M3Switch(this);
        toggle.colours(Accent.colour(), skin.muted(), skin.card);
        toggle.setChecked(Margy.isEnabled());
        toggle.setOnChanged(checked -> {
            Margy.setEnabled(checked);
            markChanged();
        });
        row.addView(toggle);

        row.setOnClickListener(v -> {
            toggle.setChecked(!toggle.isChecked(), true);
            Margy.setEnabled(toggle.isChecked());
            markChanged();
        });
        return sized(row, 56);
    }

    private View countryHead() {
        String[] current = Margy.current();
        LinearLayout row = row();
        row.addView(icon("place"));
        row.setAlpha(Margy.isEnabled() ? 1f : 0.4f);

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(current[Margy.LABEL]));
        text.addView(detail(current[Margy.CARRIER] + "  ·  " + current[Margy.MCCMNC]
                + "  ·  " + current[Margy.ISO].toUpperCase(Locale.US)));
        row.addView(text, grow());

        TextView chevron = new TextView(this);
        chevron.setText(countriesOpen ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        row.addView(chevron);

        if (Margy.isEnabled()) {
            row.setOnClickListener(v -> {
                countriesOpen = !countriesOpen;
                rebuild();
            });
        }
        return sized(row, 64);
    }

    private View countryRow(final String[] country) {
        boolean selected = country[Margy.ISO].equals(Margy.iso());
        LinearLayout row = row();

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(country[Margy.LABEL]));
        text.addView(detail(country[Margy.CARRIER] + "  ·  " + country[Margy.MCCMNC]
                + "  ·  " + country[Margy.ISO].toUpperCase(Locale.US)));
        row.addView(text, grow());

        if (selected) row.addView(new Check(this, Accent.colour()));

        row.setOnClickListener(v -> {
            Margy.setIso(country[Margy.ISO]);
            countriesOpen = false;
            markChanged();
        });
        return sized(row, 60);
    }

    private View accentHead() {
        LinearLayout row = row();
        row.addView(icon("palette"));
        row.addView(label(Text.ACCENT_COLOUR), grow());
        row.addView(new Dot(this, Accent.colour(), false));

        TextView chevron = new TextView(this);
        chevron.setText(accentOpen ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        chevron.setPadding(dp(12), 0, 0, 0);
        row.addView(chevron);

        row.setOnClickListener(v -> {
            accentOpen = !accentOpen;
            rebuild();
        });
        return sized(row, 56);
    }

    /** The row that opens one of the theme's two colours. */
    private View shadeHead(final boolean forText) {
        LinearLayout row = row();
        row.addView(icon(forText ? "text_fields" : "format_color_fill"));
        row.addView(label(forText ? Text.THEME_TEXT : Text.THEME_BACKGROUND), grow());
        row.addView(new Dot(this, forText ? Themes.text() : Themes.background(), false));

        boolean open = forText ? textOpen : backgroundOpen;
        TextView chevron = new TextView(this);
        chevron.setText(open ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        chevron.setPadding(dp(12), 0, 0, 0);
        row.addView(chevron);

        row.setOnClickListener(v -> {
            if (forText) textOpen = !textOpen;
            else backgroundOpen = !backgroundOpen;
            rebuild();
        });
        return sized(row, 56);
    }

    /**
     * What a text colour and a background colour may be.
     *
     * Two ramps rather than one palette: what a background wants is a set of
     * near-blacks and near-whites, and what text wants is the other end. The
     * accent's own dots are bright colours and would be no use for either.
     */
    private static final int[] DARKS = {
            0xFF000000, 0xFF0B0B0F, 0xFF121212, 0xFF161823, 0xFF1B1B1B,
            0xFF0D1B2A, 0xFF12232E, 0xFF1A1423, 0xFF14261C, 0xFF241A1A,
    };

    private static final int[] LIGHTS = {
            0xFFFFFFFF, 0xFFF6F6F6, 0xFFEDEDED, 0xFFE8E4DA, 0xFFDCDCDC,
            0xFFCFD8DC, 0xFFB0B8C4, 0xFF8A8A8A, 0xFF5A5A5A, 0xFF2E2E2E,
    };

    private View shades(final boolean forText) {
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        rows.setPadding(dp(16), dp(12), dp(16), dp(16));

        int[] choices = forText ? LIGHTS : DARKS;
        int now = forText ? Themes.text() : Themes.background();
        LinearLayout line = null;
        for (int i = 0; i < choices.length; i++) {
            if (i % 5 == 0) {
                line = new LinearLayout(this);
                line.setOrientation(LinearLayout.HORIZONTAL);
                line.setPadding(0, dp(6), 0, dp(6));
                rows.addView(line);
            }
            final int colour = choices[i];
            Dot dot = new Dot(this, colour, colour == now);
            dot.setOnClickListener(v -> {
                if (forText) Themes.setText(colour);
                else Themes.setBackground(colour);
                markChanged();
            });
            line.addView(dot, new LinearLayout.LayoutParams(dp(36), dp(36), 1f));
        }
        return rows;
    }

    private View palette() {
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        rows.setPadding(dp(16), dp(12), dp(16), dp(16));

        int[] palette = Accent.palette();
        LinearLayout line = null;
        for (int i = 0; i < palette.length; i++) {
            if (i % 5 == 0) {
                line = new LinearLayout(this);
                line.setOrientation(LinearLayout.HORIZONTAL);
                line.setPadding(0, dp(6), 0, dp(6));
                rows.addView(line);
            }
            final int colour = palette[i];
            Dot dot = new Dot(this, colour, colour == Accent.colour());
            dot.setOnClickListener(v -> {
                Accent.set(colour);
                markChanged();
            });
            LinearLayout.LayoutParams params =
                    new LinearLayout.LayoutParams(dp(36), dp(36), 1f);
            line.addView(dot, params);
        }

        TextView note = new TextView(this);
        note.setText(Text.ACCENT_NOTE);
        note.setTextColor(skin.muted());
        note.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        note.setPadding(0, dp(10), 0, 0);
        rows.addView(note);
        return rows;
    }

    /**
     * A Material icon, tinted to whatever this screen turned out to be.
     *
     * Decoded once per name and kept: the settings screen is rebuilt on every
     * tap, and decoding a dozen pngs each time would be felt.
     */
    private View icon(String name) {
        ImageView view = new ImageView(this);
        Bitmap bitmap = ICONS.get(name);
        if (bitmap == null) {
            try {
                String data = Icons.PNG.get(name);
                if (data != null) {
                    byte[] png = android.util.Base64.decode(data, android.util.Base64.DEFAULT);
                    bitmap = android.graphics.BitmapFactory.decodeByteArray(png, 0, png.length);
                    if (bitmap != null) ICONS.put(name, bitmap);
                }
            } catch (Throwable ignored) {
            }
        }
        if (bitmap != null) {
            view.setImageBitmap(bitmap);
            view.setColorFilter(skin.muted(), android.graphics.PorterDuff.Mode.SRC_IN);
        }
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(dp(22), dp(22));
        params.rightMargin = dp(14);
        view.setLayoutParams(params);
        return view;
    }

    private static final java.util.Map<String, Bitmap> ICONS =
            new java.util.HashMap<String, Bitmap>();

    /** What is set by a setting: one line and a switch, wherever it lives. */
    private interface Setting {
        void set(boolean on);
    }

    private View toggleRow(String picture, String title, boolean on, final Setting setting) {
        LinearLayout row = row();
        row.addView(icon(picture));
        row.addView(label(title), grow());

        final M3Switch toggle = new M3Switch(this);
        toggle.colours(Accent.colour(), skin.muted(), skin.card);
        toggle.setChecked(on);
        toggle.setOnChanged(checked -> {
            setting.set(checked);
            markChanged();
        });
        row.addView(toggle);

        row.setOnClickListener(v -> {
            toggle.setChecked(!toggle.isChecked(), true);
            setting.set(toggle.isChecked());
            markChanged();
        });
        return sized(row, 56);
    }

    /**
     * An identifier, and a tap to copy it.
     *
     * The long one does not fit on a phone, so what is shown is the ends of it
     * and what is copied is all of it.
     */
    /**
     * A switch with a word beside it saying not to trust it yet.
     *
     * The only thing in the mod that acts on its own and the only one that
     * sends anything, so it says so on the row rather than in a note nobody
     * reads.
     */
    private View betaRow(String picture, String title, boolean on, final Setting setting) {
        LinearLayout row = row();
        row.addView(icon(picture));
        row.addView(label(title));

        TextView beta = new TextView(this);
        beta.setText(Text.BETA);
        beta.setTextColor(onAccent());
        beta.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);
        beta.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        beta.setPadding(dp(7), dp(2), dp(7), dp(3));
        GradientDrawable chip = new GradientDrawable();
        chip.setColor(Accent.colour());
        chip.setCornerRadius(dp(9));
        beta.setBackground(chip);
        LinearLayout.LayoutParams place = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        place.leftMargin = dp(8);
        row.addView(beta, place);

        row.addView(new View(this), grow());

        final M3Switch toggle = new M3Switch(this);
        toggle.colours(Accent.colour(), skin.muted(), skin.card);
        toggle.setChecked(on);
        toggle.setOnChanged(checked -> {
            setting.set(checked);
            markChanged();
        });
        row.addView(toggle);
        return sized(row, 56);
    }

    private View stickerHead() {
        LinearLayout row = row();
        row.addView(icon("star"));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(Text.STREAK_STICKER));
        int many = Streaks.offered().size();
        text.addView(detail(many == 0 ? Text.STREAK_NOTHING : String.valueOf(many)));
        row.addView(text, grow());

        TextView chevron = new TextView(this);
        chevron.setText(streakOpen ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        row.addView(chevron);

        row.setOnClickListener(v -> {
            streakOpen = !streakOpen;
            rebuild();
        });
        return sized(row, 64);
    }

    /** The stickers the app has drawn so far, as something to point at. */
    private View stickerChoices() {
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        rows.setPadding(dp(16), dp(10), dp(16), dp(14));

        java.util.List<String> ids = Streaks.offered();
        if (ids.isEmpty()) {
            rows.addView(quiet(Text.STREAK_NOTHING));
            return rows;
        }

        String chosen = Streaks.chosen();
        LinearLayout line = null;
        for (int i = 0; i < ids.size() && i < 24; i++) {
            if (i % 5 == 0) {
                line = new LinearLayout(this);
                line.setOrientation(LinearLayout.HORIZONTAL);
                line.setPadding(0, dp(5), 0, dp(5));
                rows.addView(line);
            }
            final String id = ids.get(i);
            View one = stickerTile(id, id.equals(chosen));
            LinearLayout.LayoutParams size =
                    new LinearLayout.LayoutParams(dp(52), dp(52), 1f);
            line.addView(one, size);
        }
        return rows;
    }

    private View stickerTile(final String id, boolean chosen) {
        ImageView view = new ImageView(this);
        view.setScaleType(ImageView.ScaleType.FIT_CENTER);
        view.setPadding(dp(4), dp(4), dp(4), dp(4));
        if (chosen) {
            GradientDrawable ring = new GradientDrawable();
            ring.setColor(0x00000000);
            ring.setStroke(dp(2), Accent.colour());
            ring.setCornerRadius(dp(10));
            view.setBackground(ring);
        }
        Bitmap picture = Streaks.thumbnail(this, id);
        if (picture != null) view.setImageBitmap(picture);
        view.setOnClickListener(v -> {
            Streaks.choose(id);
            rebuild();
        });
        return view;
    }

    /** A row that does something at once, rather than setting anything. */
    private View actionRow(String picture, String title, String detail, final Runnable action) {
        LinearLayout row = row();
        row.addView(icon(picture));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(title));
        if (detail != null) text.addView(detail(detail));
        row.addView(text, grow());

        row.setOnClickListener(v -> action.run());
        return sized(row, detail == null ? 56 : 64);
    }

    /**
     * What this is and what it was built from, at the very bottom.
     *
     * Small and grey on purpose: nobody needs it until something has gone
     * wrong, and then it is the first thing anybody will ask for.
     */
    private View versions() {
        TextView view = new TextView(this);
        view.setText("MargyT " + Version.MOD + "  ·  TikTok " + Version.TIKTOK);
        view.setTextColor(skin.muted());
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        view.setGravity(Gravity.CENTER);
        view.setPadding(skin.margin, dp(24), skin.margin, dp(8));
        return view;
    }

    private View idRow(String title, final String value) {
        LinearLayout row = row();
        row.addView(icon("fingerprint"));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(title));

        TextView shown = detail(value == null ? Text.ACCOUNT_UNKNOWN : shorten(value));
        if (value != null) shown.setTextColor(skin.text);
        text.addView(shown);
        row.addView(text, grow());

        if (value != null) {
            row.addView(away());
            row.setOnClickListener(v -> copy(title, value));
        }
        return sized(row, 64);
    }

    private static String shorten(String value) {
        if (value.length() <= 26) return value;
        return value.substring(0, 14) + "…" + value.substring(value.length() - 8);
    }

    // ----------------------------------------------------------- the plugins

    private static final int PICK_PLUGIN = 0x4D50;  // "MP"

    private View installRow() {
        LinearLayout row = row();
        row.addView(icon("extension"));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(Text.PLUGIN_INSTALL));
        text.addView(detail(Text.PLUGIN_INSTALL_NOTE));
        row.addView(text, grow());

        TextView plus = new TextView(this);
        plus.setText("+");
        plus.setTextColor(Accent.colour());
        plus.setTextSize(TypedValue.COMPLEX_UNIT_SP, 24);
        plus.setPadding(dp(12), 0, 0, 0);
        row.addView(plus);

        row.setOnClickListener(v -> pickPlugin());
        return sized(row, 64);
    }

    /**
     * One installed plugin: what it says about itself, and a switch.
     *
     * Not `sized()` like the other rows -- a description is as tall as it is,
     * and a plugin whose author wrote two sentences should not have the second
     * one clipped.
     */
    private View pluginRow(final Plugins.Info info) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), dp(12), dp(16), dp(12));

        Bitmap icon = info.icon();
        if (icon != null) {
            ImageView view = new ImageView(this);
            view.setImageBitmap(icon);
            view.setScaleType(ImageView.ScaleType.FIT_CENTER);
            LinearLayout.LayoutParams size =
                    new LinearLayout.LayoutParams(dp(40), dp(40));
            size.rightMargin = dp(14);
            row.addView(view, size);
        } else {
            LinearLayout.LayoutParams size =
                    new LinearLayout.LayoutParams(dp(40), dp(40));
            size.rightMargin = dp(14);
            row.addView(new Dot(this, Accent.colour(), false), size);
        }

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(info.name + "  " + info.version));

        String by = info.author;
        if (!info.description.isEmpty()) by = by + "  ·  " + info.description;
        text.addView(detail(by));
        if (info.trouble != null) text.addView(detail(info.trouble));
        row.addView(text, grow());

        final M3Switch toggle = new M3Switch(this);
        toggle.colours(Accent.colour(), skin.muted(), skin.card);
        toggle.setChecked(Plugins.isEnabled(info.id));
        toggle.setEnabled(info.trouble == null || Plugins.isEnabled(info.id));
        toggle.setOnChanged(checked -> {
            Plugins.setEnabled(info.id, checked);
            markChanged();
        });
        row.addView(toggle);

        row.setOnLongClickListener(v -> {
            askToRemove(info);
            return true;
        });
        return row;
    }

    private void pickPlugin() {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            // .mtp is nobody's registered type, so the picker is shown everything
            intent.setType("*/*");
            startActivityForResult(intent, PICK_PLUGIN);
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error), Toast.LENGTH_LONG).show();
        }
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != PICK_PLUGIN || result != RESULT_OK || data == null) return;
        Uri source = data.getData();
        if (source == null) return;
        try {
            Plugins.install(this, source);
            Toast.makeText(this, Text.PLUGIN_INSTALLED, Toast.LENGTH_SHORT).show();
            markChanged();
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error.getMessage() == null
                    ? error : error.getMessage()), Toast.LENGTH_LONG).show();
        }
    }

    private void askToRemove(final Plugins.Info info) {
        try {
            new android.app.AlertDialog.Builder(this)
                    .setTitle(Text.PLUGIN_REMOVE_ASK)
                    .setMessage(info.name + "  " + info.version)
                    .setNegativeButton(Text.CANCEL, null)
                    .setPositiveButton(Text.PLUGIN_REMOVE, (dialog, which) -> {
                        Plugins.uninstall(this, info.id);
                        markChanged();
                    })
                    .show();
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error), Toast.LENGTH_LONG).show();
        }
    }

    private View commentFilterNamesRow() {
        LinearLayout row = row();
        row.addView(icon("text_fields"));
        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(Text.COMMENT_FILTER_NAMES));
        text.addView(detail(Text.COMMENT_FILTER_NAMES_NOTE));
        row.addView(text, grow());
        row.addView(away());
        row.setOnClickListener(v -> editCommentFilterNames());
        return sized(row, 64);
    }

    private void editCommentFilterNames() {
        final EditText input = new EditText(this);
        input.setSingleLine(false);
        input.setMinLines(6);
        input.setText(CommentFilter.customNamesText());
        int padding = dp(24);
        new android.app.AlertDialog.Builder(this)
                .setTitle(Text.COMMENT_FILTER_NAMES)
                .setMessage(Text.COMMENT_FILTER_EDIT_NOTE)
                .setView(input, padding, 0, padding, 0)
                .setNegativeButton(Text.CANCEL, null)
                .setPositiveButton(Text.SAVED, (dialog, which) ->
                        CommentFilter.setCustomNamesText(String.valueOf(input.getText())))
                .show();
    }

    // ------------------------------------------------------------- the links

    private View linkRow(String picture, String title, String handle, final String url) {
        LinearLayout row = row();
        row.addView(icon(picture));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(title));
        text.addView(detail(handle));
        row.addView(text, grow());
        row.addView(away());

        row.setOnClickListener(v -> open(url));
        return sized(row, 64);
    }

    private View thanksHead() {
        LinearLayout row = row();
        row.addView(icon("favorite_border"));
        row.addView(label(Text.THANKS), grow());

        TextView chevron = new TextView(this);
        chevron.setText(thanksOpen ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        row.addView(chevron);

        row.setOnClickListener(v -> {
            thanksOpen = !thanksOpen;
            rebuild();
        });
        return sized(row, 56);
    }

    /** Who made this, and the two ways to pay for it. */
    private View thanks() {
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        rows.setPadding(0, dp(6), 0, dp(10));

        rows.addView(quiet(Text.THANKS_NOTE));
        rows.addView(owner());
        rows.addView(person("Claude Opus 5", Text.THANKS_CLAUDE, null));
        rows.addView(person("апрель14", Text.THANKS_HELPER, HELPER));

        rows.addView(line());

        TextView heading = new TextView(this);
        heading.setText(Text.DONATE);
        heading.setTextColor(skin.text);
        heading.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        heading.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        heading.setPadding(dp(16), dp(14), dp(16), dp(2));
        rows.addView(heading);

        rows.addView(quiet(Text.DONATE_NOTE));

        LinearLayout card = row();
        LinearLayout cardText = new LinearLayout(this);
        cardText.setOrientation(LinearLayout.VERTICAL);
        cardText.addView(label(spaced(CARD_NUMBER)));
        cardText.addView(detail(Text.CARD + "  ·  " + Text.TAP_TO_COPY));
        card.addView(cardText, grow());
        card.setOnClickListener(v -> copy(Text.CARD, CARD_NUMBER));
        rows.addView(sized(card, 64));

        rows.addView(linkRow("star", Text.YOOMONEY, Text.YOOMONEY_NOTE, YOOMONEY));
        return rows;
    }

    /** The one row with two places to go, so it asks which. */
    private View owner() {
        LinearLayout row = row();

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label("@narezany"));
        text.addView(detail(Text.THANKS_OWNER));
        row.addView(text, grow());
        row.addView(away());

        row.setOnClickListener(v -> {
            try {
                new android.app.AlertDialog.Builder(this)
                        .setTitle("@narezany")
                        .setItems(new CharSequence[]{"Telegram", "TikTok"}, (dialog, which) ->
                                open(which == 0 ? OWNER_TELEGRAM : OWNER_TIKTOK))
                        .setNegativeButton(Text.CANCEL, null)
                        .show();
            } catch (Throwable error) {
                open(OWNER_TELEGRAM);
            }
        });
        return sized(row, 60);
    }

    private View person(String name, String what, final String url) {
        LinearLayout row = row();

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(name));
        text.addView(detail(what));
        row.addView(text, grow());

        if (url != null) {
            row.addView(away());
            row.setOnClickListener(v -> open(url));
        }
        return sized(row, 60);
    }

    /** The mark on a row that leaves the app. */
    private TextView away() {
        TextView arrow = new TextView(this);
        arrow.setText("↗");
        arrow.setTextColor(skin.muted());
        arrow.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        arrow.setPadding(dp(12), 0, 0, 0);
        return arrow;
    }

    /** A paragraph that is there to be read once and then ignored. */
    private TextView quiet(String message) {
        TextView view = new TextView(this);
        view.setText(message);
        view.setTextColor(skin.muted());
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        view.setPadding(dp(16), dp(2), dp(16), dp(8));
        return view;
    }

    /** A card number is read off the screen by a person, so it is grouped. */
    private static String spaced(String digits) {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < digits.length(); i++) {
            if (i > 0 && i % 4 == 0) out.append(' ');
            out.append(digits.charAt(i));
        }
        return out.toString();
    }

    private void open(String url) {
        // a tiktok.com link belongs to the app this is running inside, so it is
        // offered there first: without this the browser opens, recognises the
        // link and hands it straight back, which is two screens for nothing
        url = inApp(url);
        if (url.contains("tiktok.com") && openWith(url, getPackageName())) return;
        if (openWith(url, null)) return;
        Toast.makeText(this, Text.NO_BROWSER, Toast.LENGTH_SHORT).show();
    }

    /**
     * The spelling of a link the app answers to.
     *
     * TikTok claims `www.tiktok.com` and a dozen others in its manifest, and
     * does not claim the bare domain -- so a link written without the `www`
     * resolves to nothing in the app, falls through to the browser, and the
     * browser hands it straight back. One prefix is the whole difference.
     */
    private static String inApp(String url) {
        if (url.startsWith("https://tiktok.com/")) {
            return "https://www.tiktok.com/" + url.substring("https://tiktok.com/".length());
        }
        return url;
    }

    private boolean openWith(String url, String packageName) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            if (packageName != null) intent.setPackage(packageName);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }

    private void copy(String what, String text) {
        try {
            ClipboardManager clipboard =
                    (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText(what, text));
            Toast.makeText(this, Text.COPIED, Toast.LENGTH_SHORT).show();
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error), Toast.LENGTH_LONG).show();
        }
    }

    private View diaryHead() {
        LinearLayout row = row();
        row.addView(icon("article"));
        row.addView(label(Text.DIARY_TITLE), grow());

        TextView copy = new TextView(this);
        copy.setText(Text.COPY);
        copy.setTextColor(Accent.colour());
        copy.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        copy.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        copy.setPadding(dp(12), dp(8), dp(4), dp(8));
        copy.setOnClickListener(v -> copyDiary());
        row.addView(copy);

        TextView clear = new TextView(this);
        clear.setText(Text.CLEAR);
        clear.setTextColor(Accent.colour());
        clear.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        clear.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        clear.setPadding(dp(12), dp(8), dp(4), dp(8));
        clear.setOnClickListener(v -> {
            Diary.clear();
            Toast.makeText(this, Text.CLEARED, Toast.LENGTH_SHORT).show();
            rebuild();
        });
        row.addView(clear);

        TextView chevron = new TextView(this);
        chevron.setText(diaryOpen ? "⌃" : "⌄");
        chevron.setTextColor(skin.muted());
        chevron.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        chevron.setPadding(dp(12), 0, 0, 0);
        row.addView(chevron);

        row.setOnClickListener(v -> {
            diaryOpen = !diaryOpen;
            rebuild();
        });
        return sized(row, 56);
    }

    private View diaryLines() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(16), dp(8), dp(16), dp(12));
        for (String entry : Diary.lines()) {
            TextView view = new TextView(this);
            view.setText(entry);
            view.setTextColor(skin.muted());
            view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
            view.setPadding(0, dp(2), 0, 0);
            box.addView(view);
        }
        return box;
    }

    /**
     * Start TikTok over, so everything is drawn again in the new colour.
     *
     * The launcher's own intent, then out: what comes back is a fresh process
     * with nothing of the old one's colours cached in it.
     */
    private void restartTikTok() {
        try {
            android.content.Intent intent = getPackageManager()
                    .getLaunchIntentForPackage(getPackageName());
            if (intent == null) return;
            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK
                    | android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
            finish();
            Runtime.getRuntime().exit(0);
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error), Toast.LENGTH_LONG).show();
        }
    }

    private void copyDiary() {
        try {
            StringBuilder out = new StringBuilder("MargyT\n");
            List<String> lines = Diary.lines();
            for (String line : lines) out.append(line).append('\n');
            ClipboardManager clipboard =
                    (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("MargyT", out.toString()));
            Toast.makeText(this, Text.COPIED, Toast.LENGTH_SHORT).show();
        } catch (Throwable error) {
            Toast.makeText(this, String.valueOf(error), Toast.LENGTH_LONG).show();
        }
    }

    // ---------------------------------------------------------- the parts

    private View backArrow() {
        TextView arrow = new TextView(this);
        arrow.setText("←");
        arrow.setTextColor(skin.text);
        arrow.setTextSize(TypedValue.COMPLEX_UNIT_SP, 24);
        arrow.setPadding(skin.margin, dp(12), skin.margin, dp(12));
        arrow.setOnClickListener(v -> finish());
        return arrow;
    }

    private View title(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(skin.text);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 30);
        view.setTypeface(Typeface.DEFAULT_BOLD);
        view.setPadding(skin.margin, dp(8), skin.margin, dp(20));
        return view;
    }

    private View section(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(skin.muted());
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        view.setPadding(skin.margin + dp(4), dp(16), skin.margin, dp(8));
        return view;
    }

    private View caption(String message) {
        TextView view = new TextView(this);
        view.setText(message);
        view.setTextColor(skin.muted());
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        view.setPadding(skin.margin + dp(4), dp(16), skin.margin + dp(4), dp(4));
        return view;
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable background = new GradientDrawable();
        background.setColor(skin.card);
        background.setCornerRadius(skin.radius);
        card.setBackground(background);
        card.setPadding(0, dp(4), 0, dp(4));
        return card;
    }

    private View wrap(View card) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(skin.margin, 0, skin.margin, 0);
        box.addView(card, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return box;
    }

    private View line() {
        View line = new View(this);
        line.setBackgroundColor((skin.text & 0x00FFFFFF) | 0x14000000);
        return sized(line, 1);
    }

    private LinearLayout row() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), 0, dp(16), 0);
        return row;
    }

    private TextView label(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(skin.text);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        return view;
    }

    private TextView detail(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(skin.muted());
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        return view;
    }

    private LinearLayout.LayoutParams grow() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }

    private View sized(View view, int height) {
        view.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(height)));
        return view;
    }

    /**
     * The bar itself: one line of why, and the button that does it.
     *
     * Painted in the card colour with a hairline above, so it reads as resting
     * on the page rather than floating over it, and padded underneath by
     * whatever the navigation bar takes -- otherwise the button sits under the
     * gesture pill.
     */
    private View restartBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.VERTICAL);
        bar.setBackgroundColor(skin.card);
        bar.addView(line());

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.HORIZONTAL);
        content.setGravity(Gravity.CENTER_VERTICAL);
        content.setPadding(skin.margin, dp(12), skin.margin, dp(12) + navigationBar());

        TextView why = new TextView(this);
        why.setText(Text.RESTART_PENDING);
        why.setTextColor(skin.text);
        why.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        content.addView(why, grow());

        TextView button = new TextView(this);
        button.setText(Text.RESTART);
        button.setTextColor(onAccent());
        button.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        button.setPadding(dp(18), dp(9), dp(18), dp(9));
        GradientDrawable pill = new GradientDrawable();
        pill.setColor(Accent.colour());
        pill.setCornerRadius(dp(20));
        button.setBackground(pill);
        button.setOnClickListener(v -> restartTikTok());
        content.addView(button);

        bar.addView(content);
        return bar;
    }

    /**
     * What to write on the accent: the palette holds a mint and a near-white
     * as well as the pink, and white letters on either of those are unreadable.
     */
    private int onAccent() {
        int colour = Accent.colour();
        int red = (colour >> 16) & 0xFF, green = (colour >> 8) & 0xFF, blue = colour & 0xFF;
        int brightness = (red * 299 + green * 587 + blue * 114) / 1000;
        return brightness > 150 ? 0xFF1C2C24 : 0xFFFFFFFF;
    }

    private int navigationBar() {
        try {
            android.view.WindowInsets insets = getWindow().getDecorView().getRootWindowInsets();
            if (insets != null) return insets.getSystemWindowInsetBottom();
        } catch (Throwable ignored) {
        }
        return 0;
    }

    private int statusBar() {
        try {
            android.view.WindowInsets insets = getWindow().getDecorView().getRootWindowInsets();
            if (insets != null && insets.getSystemWindowInsetTop() > 0) {
                return insets.getSystemWindowInsetTop();
            }
        } catch (Throwable ignored) {
        }
        int id = getResources().getIdentifier("status_bar_height", "dimen", "android");
        return id > 0 ? getResources().getDimensionPixelSize(id) : dp(24);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    // ----------------------------------------------------- the small shapes

    /** A tick, drawn rather than typed: the glyph fonts have is never the one. */
    private static final class Check extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

        Check(Context context, int colour) {
            super(context);
            paint.setColor(colour);
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeCap(Paint.Cap.ROUND);
            paint.setStrokeJoin(Paint.Join.ROUND);
        }

        @Override
        protected void onMeasure(int widthSpec, int heightSpec) {
            int size = Math.round(22 * getResources().getDisplayMetrics().density);
            setMeasuredDimension(size, size);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float unit = getWidth() / 22f;
            paint.setStrokeWidth(unit * 2.2f);
            float y = getHeight() / 2f;
            canvas.drawLine(unit * 4, y + unit, unit * 9, y + unit * 5.5f, paint);
            canvas.drawLine(unit * 9, y + unit * 5.5f, unit * 18, y - unit * 5f, paint);
        }
    }

    /** One colour of the palette, and a ring around the one in use. */
    private static final class Dot extends View {
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final boolean chosen;

        Dot(Context context, int colour, boolean chosen) {
            super(context);
            this.chosen = chosen;
            fill.setColor(colour);
            ring.setColor(colour);
            ring.setStyle(Paint.Style.STROKE);
            setClickable(chosen ? false : true);
        }

        @Override
        protected void onMeasure(int widthSpec, int heightSpec) {
            int size = Math.round(26 * getResources().getDisplayMetrics().density);
            setMeasuredDimension(resolveSize(size, widthSpec), resolveSize(size, heightSpec));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float density = getResources().getDisplayMetrics().density;
            float centreX = getWidth() / 2f, centreY = getHeight() / 2f;
            float radius = Math.min(centreX, centreY) - (chosen ? 5 * density : 0);
            canvas.drawCircle(centreX, centreY, radius, fill);
            if (chosen) {
                ring.setStrokeWidth(2 * density);
                canvas.drawCircle(centreX, centreY, radius + 3.5f * density, ring);
            }
        }
    }
}
