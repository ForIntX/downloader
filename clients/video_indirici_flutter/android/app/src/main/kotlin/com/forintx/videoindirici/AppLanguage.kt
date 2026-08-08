package com.forintx.videoindirici

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

internal object AppLanguage {
    private const val PREFERENCES = "downloader_language"
    private const val KEY_LOCALE = "locale"

    fun set(context: Context, languageCode: String) {
        val normalized = if (languageCode == "en") "en" else "tr"
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_LOCALE, normalized)
            .apply()
    }

    fun text(context: Context, resourceId: Int, vararg arguments: Any): String {
        val language = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .getString(KEY_LOCALE, "tr") ?: "tr"
        val configuration = Configuration(context.resources.configuration)
        configuration.setLocale(Locale.forLanguageTag(language))
        val localized = context.createConfigurationContext(configuration)
        return localized.resources.getString(resourceId, *arguments)
    }
}
