package cat.narezany.margyt;

import java.util.Locale;

/**
 * The words the mod puts on screen, in the phone's language where it has them.
 *
 * Three languages and a handful of lines: enough that the mod does not look
 * bolted onto a Russian phone in English, and small enough to keep in one file
 * rather than in string resources -- which this build cannot add.
 */
final class Text {

    private Text() {}

    private static final boolean RU = "ru".equals(language()) || "be".equals(language());
    private static final boolean UK = "uk".equals(language());

    static final String ROW = pick("Настройки MargyT", "Налаштування MargyT", "MargyT settings");

    static final String REGION = pick("Регион", "Регіон", "Region");

    static final String CHANGE_REGION = pick(
            "Менять регион", "Змінювати регіон", "Change the region");

    static final String COUNTRY = pick("Страна", "Країна", "Country");

    static final String ACCENT = pick("Цвет TikTok", "Колір TikTok", "TikTok's colour");

    static final String ACCENT_COLOUR = pick("Акцент", "Акцент", "Accent");

    static final String ACCENT_NOTE = pick(
            "Меняет розовый, которым TikTok рисует лайки, кнопки и вкладки. "
                    + "Часть значков нарисована картинками — их цвет задаётся при сборке "
                    + "и здесь не меняется.",
            "Змінює рожевий, яким TikTok малює лайки, кнопки та вкладки. "
                    + "Частина значків намальована картинками — їхній колір задається "
                    + "під час збірки і тут не змінюється.",
            "Changes the pink TikTok draws likes, buttons and tabs with. Some icons "
                    + "are pictures rather than code; their colour is settled at build "
                    + "time and does not follow.");

    /** The bar at the foot of the screen: one line, not a paragraph. */
    static final String RESTART_PENDING = pick(
            "Изменения применятся после перезапуска",
            "Зміни застосуються після перезапуску",
            "Changes apply after a restart");

    static final String RESTART = pick("Перезапустить", "Перезапустити", "Restart");

    // ------------------------------------------------ what TikTok ships off

    static final String HIDDEN = pick("Анти A/B", "Анти A/B", "Anti A/B");

    static final String HIDDEN_NOTE = pick(
            "Функции у TikTok уже написаны, но выдаются случайной части людей. "
                    + "Здесь они включаются всем.",
            "Функції в TikTok уже написані, але видаються випадковій частині людей. "
                    + "Тут вони вмикаються всім.",
            "TikTok has written these already and hands them to a random share of "
                    + "people. Here they are switched on for everyone.");

    static final String CLOSE = pick("Понятно", "Зрозуміло", "Got it");

    static final String SAVE_STICKER = pick(
            "Сохранить стикер", "Зберегти стікер", "Save the sticker");

    static final String STICKER_FAILED = pick(
            "Не получилось сохранить стикер", "Не вдалося зберегти стікер",
            "Could not save the sticker");

    static final String SAVE_AVATARS_ON = pick(
            "Кнопка на аватарках", "Кнопка на аватарках", "The button on avatars");

    static final String SAVE_STICKERS_ON = pick(
            "Кнопка на стикерах", "Кнопка на стікерах", "The button on stickers");

    static final String BADGES_ON = pick("Значки", "Значки", "Badges");

    static final String SAVE_AVATAR = pick(
            "Сохранить аватарку", "Зберегти аватарку", "Save the avatar");

    static final String SAVED = pick("Сохранено", "Збережено", "Saved");

    static final String AVATAR_NOTHING = pick(
            "Нечего сохранять — откройте аватарку сначала",
            "Нема чого зберігати — відкрийте аватарку спершу",
            "Nothing to save yet -- open an avatar first");

    static final String AVATAR_FAILED = pick(
            "Не получилось сохранить", "Не вдалося зберегти", "Could not save it");

    static final String BADGE_OWNER = pick(
            "Владелец Margy и MargyT", "Власник Margy і MargyT",
            "The owner of Margy and MargyT");

    static final String VIDEO = pick("Видео", "Відео", "Video");

    static final String THEME = pick("Тема", "Тема", "Theme");

    static final String THEME_ON = pick(
            "Своя тема", "Своя тема", "A theme of your own");

    static final String THEME_MATERIAL = pick(
            "Цвета с обоев", "Кольори зі шпалер", "Colours from the wallpaper");

    static final String THEME_TEXT = pick("Текст", "Текст", "Text");

    static final String THEME_BACKGROUND = pick("Фон", "Тло", "Background");

    static final String THEME_NOTE = pick(
            "Перекрашивается только то, что тикток и сам перекрашивает при "
                    + "смене светлой темы на тёмную. Акцент живёт отдельно.",
            "Перефарбовується лише те, що тікток і сам перефарбовує при зміні "
                    + "світлої теми на темну. Акцент живе окремо.",
            "Only what TikTok itself repaints when you switch between light and "
                    + "dark. The accent is its own thing.");

    static final String BACKGROUND = pick(
            "Играть в фоне", "Грати у фоні", "Play in the background");

    static final String AUTOSCROLL = pick(
            "Автопрокрутка ленты", "Автопрокрутка стрічки", "Scroll the feed by itself");

    static final String SOUND = pick(
            "Звук, снятый по копирайту", "Звук, знятий за копірайтом",
            "Sound pulled for copyright");

    static final String SEEKBAR = pick(
            "Перемотка на всех видео", "Перемотка на всіх відео",
            "The scrubbing bar everywhere");

    static final String VOICE = pick(
            "Голосовые комментарии", "Голосові коментарі", "Voice comments");

    // -------------------------------------------------------- the downloads

    static final String DOWNLOADS = pick("Скачивание", "Завантаження", "Downloads");

    static final String NO_WATERMARK = pick(
            "Без водяного знака", "Без водяного знака", "Without the watermark");

    static final String DOWNLOAD_ALWAYS = pick(
            "Сохранять можно всё", "Зберігати можна все", "Save anything");

    static final String COMMENT_FILTER = pick("Комментарии", "Коментарі", "Comments");
    static final String COMMENT_FILTER_ON = pick("Скрывать по имени", "Ховати за ім’ям", "Hide by name");
    static final String COMMENT_FILTER_NAMES = pick("Имена для скрытия", "Імена для приховування", "Names to hide");
    static final String COMMENT_FILTER_NAMES_NOTE = pick("По одному имени в строке", "Одне ім’я в рядку", "One name per line");
    static final String COMMENT_FILTER_EDIT_NOTE = pick("Точные имена; фильтр применяется только к верифицированным аккаунтам.", "Точні імена; фільтр діє лише для верифікованих акаунтів.", "Exact names; the filter applies only to verified accounts.");
    static final String COMMENT_FILTER_NOTE = pick("Правила загружаются и кэшируются; официальные аккаунты из allowlist не скрываются.", "Правила завантажуються й кешуються; офіційні акаунти з allowlist не приховуються.", "Rules are downloaded and cached; official allowlisted accounts are never hidden.");

    static final String FEED = pick("Лента", "Стрічка", "Feed");

    static final String HIDE_ADS = pick(
            "Убирать рекламу", "Прибирати рекламу", "Drop the advertisements");

    // --------------------------------------------------------- the plugins

    static final String PLUGINS = pick("Плагины", "Плагіни", "Plugins");

    static final String PLUGIN_INSTALL = pick(
            "Установить плагин", "Встановити плагін", "Install a plugin");

    static final String PLUGIN_INSTALL_NOTE = pick(
            "Файл .mtp", "Файл .mtp", "An .mtp file");

    static final String PLUGIN_NONE = pick(
            "Пока ничего не установлено.",
            "Поки нічого не встановлено.",
            "Nothing installed yet.");

    static final String PLUGIN_WARNING = pick(
            "Песочницы нет. Ставьте только то, чему доверяете.",
            "Пісочниці немає. Встановлюйте лише те, чому довіряєте.",
            "No sandbox. Install only what you trust.");

    static final String PLUGIN_DOCS = pick(
            "Как писать плагины", "Як писати плагіни", "Writing plugins");

    static final String PLUGIN_DOCS_NOTE = pick(
            "Документация на GitHub", "Документація на GitHub", "The documentation on GitHub");

    static final String PLUGIN_INSTALLED = pick(
            "Плагин установлен", "Плагін встановлено", "Plugin installed");

    static final String PLUGIN_REMOVE = pick("Удалить", "Видалити", "Remove");

    static final String PLUGIN_REMOVE_ASK = pick(
            "Удалить плагин?", "Видалити плагін?", "Remove the plugin?");

    static final String CANCEL = pick("Отмена", "Скасувати", "Cancel");

    static final String PLUGIN_HOLD = pick(
            "Долгое нажатие — удалить",
            "Довге натискання — видалити",
            "Hold to remove");

    // ----------------------------------------------------------- the links

    static final String LINKS = pick("Ссылки", "Посилання", "Links");

    static final String CHANNEL = pick("Канал", "Канал", "Channel");

    static final String FORUM = pick("Форум", "Форум", "Forum");

    // ----------------------------------------------------------- the streaks

    static final String STREAKS = pick("Серии", "Серії", "Streaks");

    static final String STREAK_AUTO = pick(
            "Продлевать серии сами", "Продовжувати серії самі", "Keep streaks alive");

    static final String BETA = pick("бета", "бета", "beta");

    static final String STREAK_NOTE = pick(
            "Отправляет выбранный стикер тем, с кем серия вот-вот погаснет. "
                    + "Не чаще раза в сутки на человека.",
            "Надсилає вибраний стікер тим, з ким серія ось-ось згасне. "
                    + "Не частіше разу на добу на людину.",
            "Sends the sticker you picked to whoever the streak is about to lapse "
                    + "with, at most once a day each.");

    static final String STREAK_STICKER = pick(
            "Чем продлевать", "Чим продовжувати", "What to send");

    static final String STREAK_NOTHING = pick(
            "Откройте стикеры в переписке, и они появятся здесь",
            "Відкрийте стікери в листуванні, і вони з'являться тут",
            "Open the stickers in a chat and they will show up here");

    // ------------------------------------------------------- the updates

    static final String UPDATE = pick("Обновление", "Оновлення", "An update");

    static final String UPDATE_THERE_IS = pick(
            "Вышла версия", "Вийшла версія", "There is a version");

    static final String UPDATE_GET = pick("Скачать", "Завантажити", "Get it");

    static final String UPDATE_LATER = pick("Не сейчас", "Не зараз", "Not now");

    static final String UPDATE_NEVER = pick(
            "Больше не напоминать", "Більше не нагадувати", "Stop reminding me");

    static final String UPDATE_GETTING = pick("Скачиваю", "Завантажую", "Getting it");

    static final String UPDATE_FAILED = pick(
            "Не получилось скачать", "Не вдалося завантажити", "Could not get it");

    static final String UPDATE_NONE = pick(
            "Уже последняя версия", "Вже остання версія", "This is the latest");

    static final String UPDATE_NO_ANSWER = pick(
            "GitHub не ответил", "GitHub не відповів", "GitHub did not answer");

    static final String UPDATE_ALLOW = pick(
            "Разрешите установку из этого источника, и я поставлю",
            "Дозвольте встановлення з цього джерела, і я поставлю",
            "Allow installing from this source and it will go on");

    static final String UPDATE_CHECK = pick(
            "Проверить обновления", "Перевірити оновлення", "Check for updates");

    static final String UPDATE_REMIND = pick(
            "Напоминать об обновлениях", "Нагадувати про оновлення",
            "Remind me about updates");

    static final String UPDATE_INSTALL = pick(
            "Установить скачанное", "Встановити завантажене", "Install what was downloaded");

    static final String VERSIONS = pick("Версии", "Версії", "Versions");

    static final String SOURCE = pick("Исходники", "Вихідники", "The source");

    static final String THANKS = pick("Благодарности", "Подяки", "Thanks");

    static final String THANKS_NOTE = pick(
            "Люди, без которых мода бы не было.",
            "Люди, без яких мода б не було.",
            "The people the mod would not exist without.");

    static final String THANKS_OWNER = pick(
            "Владелец мода", "Власник мода", "The mod's owner");

    static final String THANKS_CLAUDE = pick(
            "Написал большую часть того, что в моде есть",
            "Написав більшу частину того, що в моді є",
            "Wrote most of what is in the mod");

    static final String THANKS_HELPER = pick(
            "Помог с несколькими фичами",
            "Допоміг з кількома фічами",
            "Helped with several of the features");

    static final String DONATE = pick("Поддержать", "Підтримати", "Support the project");

    static final String DONATE_NOTE = pick(
            "Каждый ваш рубль помогает держать проект на плаву и развивать открытое "
                    + "сообщество моддинга. Спасибо.",
            "Кожен ваш рубль допомагає тримати проєкт на плаву та розвивати відкриту "
                    + "спільноту модингу. Дякуємо.",
            "Every rouble keeps the project afloat and goes back into the open source "
                    + "modding community. Thank you.");

    static final String CARD = pick("Карта", "Картка", "Card");

    static final String TAP_TO_COPY = pick(
            "Нажми, чтобы скопировать", "Натисни, щоб скопіювати", "Tap to copy");

    static final String YOOMONEY = pick("ЮMoney", "ЮMoney", "YooMoney");

    static final String YOOMONEY_NOTE = pick(
            "Перевод напрямую", "Переказ напряму", "Straight to the transfer page");

    static final String NO_BROWSER = pick(
            "Нечем открыть ссылку", "Нема чим відкрити посилання", "Nothing here opens links");

    static final String DIARY_TITLE = pick("Журнал мода", "Журнал мода", "The mod's diary");

    static final String COPY = pick("Скопировать", "Скопіювати", "Copy");

    static final String COPIED = pick("Скопировано", "Скопійовано", "Copied");

    static final String CLEAR = pick("Очистить", "Очистити", "Clear");

    static final String DIARY = pick(
            "Что мод видел", "Що мод бачив", "What the mod saw");

    static final String CLEARED = pick("Журнал очищен", "Журнал очищено", "The diary is empty");

    static final String ACCOUNT = pick("Аккаунт", "Акаунт", "Account");

    static final String ACCOUNT_ID = pick("ID", "ID", "ID");

    static final String ACCOUNT_SEC_ID = pick(
            "ID для ссылки", "ID для посилання", "The id a link is built from");

    static final String ACCOUNT_UNKNOWN = pick(
            "Пока неизвестен", "Поки невідомий", "Not seen yet");

    private static String language() {
        try {
            return Locale.getDefault().getLanguage();
        } catch (Throwable ignored) {
            return "en";
        }
    }

    private static String pick(String russian, String ukrainian, String english) {
        if (RU) return russian;
        if (UK) return ukrainian;
        return english;
    }
}
