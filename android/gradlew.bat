@echo off
rem Gradle wrapper for Windows (see gradlew for notes on wrapper jar generation).

if not defined GRADLE_HOME (
  where gradle >nul 2>nul
  if errorlevel 1 (
    echo Gradle not found on PATH. Install Gradle or set GRADLE_HOME.
    exit /b 1
  )
  gradle %*
  exit /b %errorlevel%
)

"%GRADLE_HOME%\bin\gradle" %*
exit /b %errorlevel%