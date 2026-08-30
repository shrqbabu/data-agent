package com.analyticsagent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import com.analyticsagent.data.local.AppConfig
import com.analyticsagent.navigation.AppNavHost
import com.analyticsagent.ui.login.LoginScreen
import com.analyticsagent.ui.setup.UnconfiguredScreen
import com.analyticsagent.ui.theme.AnalyticsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AnalyticsTheme {
                val container = rememberContainer()
                when {
                    container == null -> UnconfiguredScreen("App failed to initialize.")
                    !AppConfig.isConfigured() -> UnconfiguredScreen()
                    else -> AuthGate(container)
                }
            }
        }
    }
}

@Composable
internal fun rememberContainer(): AppContainer? {
    val context = LocalContext.current
    return (context.applicationContext as? AnalyticsApplication)?.container
}

/** Gate: show the single-page login until an admin session is present. */
@Composable
private fun AuthGate(container: AppContainer) {
    val session by container.authRepository.session.collectAsState(initial = null)
    val loggedIn = session?.isLoggedIn == true
    if (loggedIn) {
        AppNavHost(container)
    } else {
        LoginScreen(container)
    }
}