@rem
@rem Gradle startup script for Windows
@rem

@if "%DEBUG%"=="" @echo off
@rem ##########################################################################
@rem  Gradle startup script for Windows
@rem ##########################################################################

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

set DEFAULT_JVM_OPTS="-Xmx64m" "-Xms64m"

if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=C:\Program Files\Android\Android Studio\jbr\bin\java.exe
if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is not set and no Java executable was found.
echo.
echo Please set JAVA_HOME or install Android Studio/JDK.
exit /b 1

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%\bin\java.exe
if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is not set to a valid Java installation: %JAVA_HOME%
echo.
exit /b 1

:execute
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %GRADLE_OPTS% -classpath "%APP_HOME%\gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*

:end
@rem End local scope for rem variables
exit /b %ERRORLEVEL%
